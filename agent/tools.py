import difflib
import json

try:
    from langchain_core.tools import tool
except Exception:
    def tool(func):
        return func

from agent.memory import get_recent_messages
from agent.providers import call_chat_once
from core.extensions import db
from database.models import ChoiceQuestionNode, graphCourseNode
from repositories.answer_repository import get_answer_history
from repositories.graph_repository import get_course_node_names, get_relation, resolve_course_name
from repositories.vectorDB_repository import search_question_topK


def _normalize_text(value) -> str:
    if value is None:
        return ""
    try:
        return str(value).strip()
    except Exception:
        return ""


def _build_user_brief(topic: str, chat_window_id: str, course_name: str) -> str:
    current_topic = _normalize_text(topic)
    recent_messages = get_recent_messages(chat_window_id, limit=6)
    history_lines = []
    for item in recent_messages:
        role = "用户" if item.get("isUserSend") else "助手"
        content = _normalize_text(item.get("content", ""))
        if content:
            history_lines.append(f"{role}: {content}")
    history_text = "\n".join(history_lines).strip()
    prompt = (
        "你是学习需求提炼助手。请基于最近最多3轮对话和当前提问，"
        "输出用户希望考察的知识点概述。"
        "输出必须是单行中文，格式严格为“考察A、B、C”。"
        "不要解释，不要换行，不要包含其他字段。"
    )
    user_message = (
        f"课程：{_normalize_text(course_name)}\n"
        f"最近对话：\n{history_text or '无'}\n"
        f"当前提问：{current_topic or '无'}"
    )
    brief = call_chat_once(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        model_level="lite",
        temperature=0,
        max_tokens=128,
    )
    clean_brief = _normalize_text(brief)
    if clean_brief.startswith("考察"):
        return clean_brief
    if clean_brief:
        return f"考察{clean_brief}"
    fallback = current_topic or "课程核心知识点"
    return f"考察{fallback}"


def _serialize_choice_question(question: ChoiceQuestionNode) -> dict:
    return {
        "id": question.id,
        "course": question.course or "",
        "content": question.content or "",
        "optionA": question.optionA or "",
        "optionB": question.optionB or "",
        "optionC": question.optionC or "",
        "optionD": question.optionD or "",
        "answer": question.answer or "",
        "brief": question.brief or "",
        "explanation": question.explanation or "",
        "difficulty": int(question.difficulty or 0),
    }


def _load_choice_questions_by_ids(question_ids: list[int]) -> list[dict]:
    if not question_ids:
        return []
    unique_ids = []
    seen = set()
    for item in question_ids:
        try:
            current = int(item)
        except Exception:
            continue
        if current in seen:
            continue
        seen.add(current)
        unique_ids.append(current)
    if not unique_ids:
        return []
    query_rows = ChoiceQuestionNode.query.filter(ChoiceQuestionNode.id.in_(unique_ids)).all()
    row_mapping = {int(row.id): row for row in query_rows if getattr(row, "id", None) is not None}
    output = []
    for question_id in unique_ids:
        row = row_mapping.get(question_id)
        if row is None:
            continue
        output.append(_serialize_choice_question(row))
    return output


def _select_relevant_node(course_name: str, query_text: str, candidate_nodes: list[str]) -> str:
    clean_course = _normalize_text(course_name)
    clean_query = _normalize_text(query_text)
    clean_candidates = [item for item in (_normalize_text(name) for name in candidate_nodes) if item]
    if not clean_candidates:
        return ""
    prompt = (
        "你是知识图谱节点选择器。"
        "请根据课程、用户问题和候选节点列表，挑选最相关的一个节点。"
        "输出必须只包含节点名本身，不要解释，不要换行，不要输出额外符号。"
        "若无法判断，返回候选列表中的第一个节点。"
    )
    user_message = (
        f"课程：{clean_course}\n"
        f"用户问题：{clean_query or '无'}\n"
        f"候选节点：{json.dumps(clean_candidates, ensure_ascii=False)}"
    )
    selected = _normalize_text(
        call_chat_once(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            model_level="lite",
            temperature=0,
            max_tokens=64,
        )
    )
    if selected in clean_candidates:
        return selected
    for item in clean_candidates:
        if item and item in selected:
            return item
    closest = difflib.get_close_matches(selected, clean_candidates, n=1, cutoff=0.0)
    if closest:
        return closest[0]
    return clean_candidates[0]


def _serialize_graph_edges(edges) -> list[dict]:
    output = []
    for edge in edges or []:
        node1 = _normalize_text(getattr(edge, "node1", ""))
        node2 = _normalize_text(getattr(edge, "node2", ""))
        relation = _normalize_text(getattr(edge, "relation", ""))
        course = _normalize_text(getattr(edge, "course", ""))
        if not node1 or not node2 or not relation:
            continue
        output.append(
            {
                "course": course,
                "node1": node1,
                "node2": node2,
                "relation": relation,
            }
        )
    return output


def _upsert_graph_course_nodes(course_name: str, node_names: list[str]) -> None:
    clean_course = _normalize_text(course_name)
    clean_nodes = [item for item in (_normalize_text(node) for node in node_names) if item]
    if not clean_course or not clean_nodes:
        return
    existing_rows = (
        graphCourseNode.query.filter_by(course=clean_course)
        .with_entities(graphCourseNode.nodeName)
        .all()
    )
    existing = {
        _normalize_text(getattr(row, "nodeName", row[0] if isinstance(row, tuple) else ""))
        for row in existing_rows
    }
    pending = [name for name in clean_nodes if name not in existing]
    if not pending:
        return
    for node_name in pending:
        db.session.add(graphCourseNode(course=clean_course, nodeName=node_name))
    db.session.commit()


def _load_candidate_nodes(course_name: str) -> tuple[str, list[str]]:
    preferred_course = _normalize_text(course_name)
    rows = (
        graphCourseNode.query.filter_by(course=preferred_course)
        .order_by(graphCourseNode.id.asc())
        .all()
    )
    candidate_nodes = [
        _normalize_text(getattr(item, "nodeName", ""))
        for item in rows
        if _normalize_text(getattr(item, "nodeName", ""))
    ]
    if candidate_nodes:
        return preferred_course, list(dict.fromkeys(candidate_nodes))
    resolved_course = _normalize_text(resolve_course_name(preferred_course)) or preferred_course
    graph_nodes = get_course_node_names(resolved_course)
    if graph_nodes:
        _upsert_graph_course_nodes(resolved_course, graph_nodes)
        rows = (
            graphCourseNode.query.filter_by(course=resolved_course)
            .order_by(graphCourseNode.id.asc())
            .all()
        )
        candidate_nodes = [
            _normalize_text(getattr(item, "nodeName", ""))
            for item in rows
            if _normalize_text(getattr(item, "nodeName", ""))
        ]
    return resolved_course, list(dict.fromkeys(candidate_nodes))


def _rank_candidate_nodes(query_text: str, focused_node: str, candidate_nodes: list[str]) -> list[str]:
    clean_query = _normalize_text(query_text)
    clean_focus = _normalize_text(focused_node)
    candidates = [item for item in (_normalize_text(name) for name in candidate_nodes) if item]
    if not candidates:
        return []
    base = []
    if clean_focus:
        base.append(clean_focus)
    if clean_query:
        scored = sorted(
            candidates,
            key=lambda node: difflib.SequenceMatcher(None, clean_query, node).ratio(),
            reverse=True,
        )
        base.extend(scored[:8])
    base.extend(candidates[:8])
    ordered = []
    seen = set()
    for item in base:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _to_date_text(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())
        except Exception:
            return str(value)
    return str(value)


def _safe_ratio(value: float) -> float:
    try:
        return round(float(value), 4)
    except Exception:
        return 0.0


def _serialize_answer_records(rows) -> list[dict]:
    output = []
    for item in rows or []:
        brief = _normalize_text(getattr(item, "questionBrief", "") or "未命名题目")
        date_text = _to_date_text(getattr(item, "date", ""))
        output.append(
            {
                "brief": brief or "未命名题目",
                "isCorrect": bool(getattr(item, "isCorrect", False)),
                "date": date_text,
            }
        )
    return output


def _build_daily_trend(entries: list[dict], limit: int = 14) -> list[dict]:
    grouped = {}
    for item in entries:
        day = _normalize_text(item.get("date", ""))
        if not day:
            continue
        current = grouped.setdefault(day, {"date": day, "total": 0, "correct": 0})
        current["total"] += 1
        if item.get("isCorrect"):
            current["correct"] += 1
    trend = []
    for day in sorted(grouped.keys()):
        row = grouped[day]
        total = int(row["total"])
        correct = int(row["correct"])
        trend.append(
            {
                "date": day,
                "total": total,
                "correct": correct,
                "accuracy": _safe_ratio(correct / total) if total else 0.0,
            }
        )
    if len(trend) <= limit:
        return trend
    return trend[-limit:]


def _build_brief_stats(entries: list[dict], limit: int = 6) -> tuple[list[dict], list[dict]]:
    grouped = {}
    for item in entries:
        brief = _normalize_text(item.get("brief", "")) or "未命名题目"
        row = grouped.setdefault(brief, {"brief": brief, "attempts": 0, "correct": 0})
        row["attempts"] += 1
        if item.get("isCorrect"):
            row["correct"] += 1
    stats = []
    for row in grouped.values():
        attempts = int(row["attempts"])
        correct = int(row["correct"])
        stats.append(
            {
                "brief": row["brief"],
                "attempts": attempts,
                "correct": correct,
                "accuracy": _safe_ratio(correct / attempts) if attempts else 0.0,
            }
        )
    if not stats:
        return [], []
    weak_pool = [item for item in stats if item["attempts"] >= 2] or stats
    strong_pool = [item for item in stats if item["attempts"] >= 2] or stats
    weak_items = sorted(
        weak_pool,
        key=lambda item: (item["accuracy"], -item["attempts"], item["brief"]),
    )[:limit]
    strong_items = sorted(
        strong_pool,
        key=lambda item: (-item["accuracy"], -item["attempts"], item["brief"]),
    )[:limit]
    return weak_items, strong_items


def _parse_json_block(raw_text: str) -> dict:
    content = _normalize_text(raw_text)
    if not content:
        return {}
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    start_index = content.find("{")
    end_index = content.rfind("}")
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return {}
    try:
        parsed = json.loads(content[start_index : end_index + 1])
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _build_fallback_insights(
    weak_items: list[dict],
    strong_items: list[dict],
    overall_accuracy: float,
) -> dict:
    weak_names = [item.get("brief", "") for item in weak_items[:3] if item.get("brief")]
    strong_names = [item.get("brief", "") for item in strong_items[:3] if item.get("brief")]
    weak_text = "、".join(weak_names) if weak_names else "暂无明显弱势项"
    strong_text = "、".join(strong_names) if strong_names else "暂无明显强势项"
    return {
        "weak_items": [
            f"{weak_text}的正确率相对偏低，建议先回归课本定义与典型例题。",
        ],
        "strong_items": [
            f"{strong_text}保持稳定，建议继续通过变式题巩固。",
        ],
        "learning_suggestions": [
            "每次练习后优先复盘错题，定位是概念遗漏还是审题失误。",
            "将同类题集中练习并记录纠错要点，隔天进行二次回测。",
            "先保正确率再提速度，单次训练建议控制在20分钟内。",
        ],
        "overall_summary": f"最近作答整体正确率约为{round(overall_accuracy * 100, 1)}%，建议按“弱项优先、强项保持”的节奏推进。",
    }


def _build_empty_insights() -> dict:
    return {
        "weak_items": ["暂无可分析的弱势项，先完成若干道练习题。"],
        "strong_items": ["暂无可分析的强势项，完成更多作答后会自动识别。"],
        "learning_suggestions": [
            "建议先完成同一课程下的基础题与中档题，形成可分析样本。",
            "每次练习后查看错因并记录，连续两天复测同类题。",
            "先稳定正确率，再逐步压缩作答时间。",
        ],
        "overall_summary": "当前未检索到有效作答记录，暂无法形成可靠学情画像。",
    }


def _filter_rows_by_course(rows, course_name: str, limit: int = 100):
    target = _normalize_text(course_name)
    if not target:
        return list(rows or [])[:limit], ""
    lower_target = target.lower()
    output = []
    for row in rows or []:
        row_course = _normalize_text(getattr(row, "course", ""))
        lower_row = row_course.lower()
        if lower_row == lower_target or lower_target in lower_row or lower_row in lower_target:
            output.append(row)
            if len(output) >= limit:
                break
    return output, target


def _fetch_learning_review_rows(user_id: str, course_name: str, limit: int = 100):
    normalized_user_id = _normalize_text(user_id)
    normalized_course = _normalize_text(course_name)
    if not normalized_user_id:
        return [], normalized_course
    if not normalized_course or normalized_course == "$ALL$":
        return [], normalized_course
    direct_rows = get_answer_history(normalized_user_id, normalized_course, limit)
    if direct_rows:
        return direct_rows, normalized_course
    all_rows = get_answer_history(normalized_user_id, "$ALL$", max(limit * 4, 400))
    if not all_rows:
        return [], normalized_course
    filtered_rows, _ = _filter_rows_by_course(all_rows, normalized_course, limit=limit)
    if filtered_rows:
        return filtered_rows, normalized_course
    course_names = list(
        dict.fromkeys(
            _normalize_text(getattr(item, "course", ""))
            for item in all_rows
            if _normalize_text(getattr(item, "course", ""))
        )
    )
    if not course_names:
        return [], normalized_course
    matched = difflib.get_close_matches(normalized_course, course_names, n=1, cutoff=0.45)
    if matched:
        fuzzy_rows, _ = _filter_rows_by_course(all_rows, matched[0], limit=limit)
        if fuzzy_rows:
            return fuzzy_rows, matched[0]
    return [], normalized_course


def _build_llm_learning_insights(course_name: str, entries: list[dict], fallback: dict) -> dict:
    if not entries:
        return fallback
    compact_lines = [
        f"[{item.get('brief', '')}][{'true' if item.get('isCorrect') else 'false'}][{item.get('date', '')}]"
        for item in entries
    ]
    prompt = (
        "你是资深学习分析师。"
        "请只基于给定作答记录，输出严格JSON，不要输出任何额外文本。"
        "JSON结构："
        '{"weak_items":[""],"strong_items":[""],"learning_suggestions":[""],"overall_summary":""}。'
        "要求："
        "1) weak_items、strong_items、learning_suggestions 各返回3-5条中文短句；"
        "2) 结论要具体、可执行，不要空泛；"
        "3) 不要编造不存在的数据。"
    )
    user_message = (
        f"课程：{course_name}\n"
        "作答记录如下，每条格式为[brief][isCorrect][Date]：\n"
        + "\n".join(compact_lines)
    )
    raw = call_chat_once(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        model_level="pro",
        temperature=0,
        max_tokens=900,
    )
    parsed = _parse_json_block(raw)
    weak_items = parsed.get("weak_items")
    strong_items = parsed.get("strong_items")
    suggestions = parsed.get("learning_suggestions")
    summary = _normalize_text(parsed.get("overall_summary", ""))
    if not isinstance(weak_items, list) or not isinstance(strong_items, list) or not isinstance(suggestions, list):
        return fallback
    clean_weak = [_normalize_text(item) for item in weak_items if _normalize_text(str(item))]
    clean_strong = [_normalize_text(item) for item in strong_items if _normalize_text(str(item))]
    clean_suggestions = [_normalize_text(item) for item in suggestions if _normalize_text(str(item))]
    if not clean_weak or not clean_strong or not clean_suggestions:
        return fallback
    if not summary:
        summary = fallback.get("overall_summary", "")
    return {
        "weak_items": clean_weak[:5],
        "strong_items": clean_strong[:5],
        "learning_suggestions": clean_suggestions[:5],
        "overall_summary": summary,
    }


@tool
def get_exercise_recommendation_card(
    course_name: str,
    topic: str = "",
    chat_window_id: str = "",
) -> dict:
    """习题推荐卡片工具。"""
    normalized_course = _normalize_text(course_name) or "通用课程"
    user_brief = _build_user_brief(
        topic=topic,
        chat_window_id=_normalize_text(chat_window_id),
        course_name=normalized_course,
    )
    top_ids = search_question_topK(
        myBrief=user_brief,
        course=normalized_course,
        type="choice",
        k=5,
    )
    questions = _load_choice_questions_by_ids(top_ids)
    return {
        "type": "questions",
        "content": questions,
        "userBrief": user_brief,
        "card_title": "习题推荐",
        "course": normalized_course,
    }


@tool
def get_knowledge_graph_card(course_name: str, query_text: str = "") -> dict:
    """知识图谱卡片工具。"""
    normalized_course = _normalize_text(course_name) or "通用课程"
    normalized_query = _normalize_text(query_text) or "核心知识点"
    resolved_course, candidate_nodes = _load_candidate_nodes(normalized_course)
    focused_node = _select_relevant_node(resolved_course, normalized_query, candidate_nodes)
    if not focused_node:
        fallback = normalized_query.replace("知识图谱", "").replace("图谱", "").strip()
        focused_node = fallback or (candidate_nodes[0] if candidate_nodes else "")
    relations = get_relation(focused_node, resolved_course, 3) if focused_node else []
    if not relations and candidate_nodes:
        for candidate in _rank_candidate_nodes(normalized_query, focused_node, candidate_nodes):
            current = get_relation(candidate, resolved_course, 3)
            if current:
                focused_node = candidate
                relations = current
                break
    content = _serialize_graph_edges(relations)
    summary = f"已定位节点「{focused_node}」，共检索到{len(content)}条3跳内关系。"
    return {
        "type": "graph",
        "content": content,
        "course": resolved_course,
        "query_text": normalized_query,
        "focus_node": focused_node,
        "card_title": "知识图谱",
        "summary": summary,
        "brief_text": summary,
    }


@tool
def get_learning_review_card(course_name: str, user_id: str = "") -> dict:
    """学情回顾卡片工具。"""
    normalized_course = _normalize_text(course_name) or "$ALL$"
    normalized_user_id = _normalize_text(user_id)
    answer_rows, matched_course = _fetch_learning_review_rows(
        user_id=normalized_user_id,
        course_name=normalized_course,
        limit=100,
    )
    entries = _serialize_answer_records(answer_rows)
    total_count = len(entries)
    correct_count = sum(1 for item in entries if item.get("isCorrect"))
    accuracy = _safe_ratio(correct_count / total_count) if total_count else 0.0
    trend = _build_daily_trend(entries, limit=14)
    weak_stats, strong_stats = _build_brief_stats(entries, limit=6)
    fallback_insights = (
        _build_fallback_insights(weak_stats, strong_stats, accuracy)
        if total_count
        else _build_empty_insights()
    )
    analysis_course = matched_course or (normalized_course if normalized_course != "$ALL$" else "")
    insights = _build_llm_learning_insights(analysis_course, entries, fallback_insights)
    if not normalized_course or normalized_course == "$ALL$":
        summary = "请先指定学科后再进行学情回顾分析。"
    elif total_count:
        summary = f"近{total_count}题正确率{round(accuracy * 100, 1)}%，已提炼弱势项{len(weak_stats)}个、强势项{len(strong_stats)}个。"
    else:
        summary = f"未检索到「{analysis_course or normalized_course}」相关作答记录，可先完成该学科练习后再生成学情回顾。"
    overview = {
        "total": total_count,
        "correct": correct_count,
        "wrong": max(total_count - correct_count, 0),
        "accuracy": accuracy,
    }
    content = {
        "overview": overview,
        "trend": trend,
        "weak_stats": weak_stats,
        "strong_stats": strong_stats,
        "insights": insights,
        "samples": entries[-24:],
    }
    return {
        "type": "analysis",
        "content": content,
        "summary": summary,
        "brief_text": summary,
        "course": matched_course or (normalized_course if normalized_course != "$ALL$" else ""),
        "card_title": "学情回顾",
    }


TOOLS = [
    get_exercise_recommendation_card,
    get_knowledge_graph_card,
    get_learning_review_card,
]
