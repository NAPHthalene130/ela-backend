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
from repositories.graph_repository import get_course_node_names, get_relation, resolve_course_name
from repositories.vectorDB_repository import search_question_topK


def _normalize_text(value: str) -> str:
    return (value or "").strip()


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
    """学情回顾卡片占位工具。"""
    normalized_course = _normalize_text(course_name) or "通用课程"
    normalized_user_id = _normalize_text(user_id)
    return {
        "ui_type": "learning_review_card",
        "payload": {
            "brief_text": "已为你生成学情回顾卡片。",
            "course": normalized_course,
            "user_id": normalized_user_id,
            "card_title": "学情回顾",
            "todo": "TODO: 接入学情分析服务，返回知识掌握度、薄弱点与学习建议。",
        },
    }


TOOLS = [
    get_exercise_recommendation_card,
    get_knowledge_graph_card,
    get_learning_review_card,
]
