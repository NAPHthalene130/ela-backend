try:
    from langchain_core.tools import tool
except Exception:
    def tool(func):
        return func

from agent.memory import get_recent_messages
from agent.providers import call_chat_once
from database.models import ChoiceQuestionNode
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
    """知识图谱卡片占位工具。"""
    normalized_course = _normalize_text(course_name) or "通用课程"
    normalized_query = _normalize_text(query_text) or "核心知识点"
    return {
        "ui_type": "knowledge_graph_card",
        "payload": {
            "brief_text": "已为你生成知识图谱卡片。",
            "course": normalized_course,
            "query_text": normalized_query,
            "card_title": "知识图谱",
            "todo": "TODO: 接入知识图谱检索服务，并返回节点与关系数据。",
        },
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
