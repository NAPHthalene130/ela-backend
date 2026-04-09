try:
    from langchain_core.tools import tool
except Exception:
    def tool(func):
        return func


def _normalize_text(value: str) -> str:
    return (value or "").strip()


@tool
def get_exercise_recommendation_card(course_name: str, topic: str = "") -> dict:
    """习题推荐卡片占位工具。"""
    normalized_course = _normalize_text(course_name) or "通用课程"
    normalized_topic = _normalize_text(topic) or "综合练习"
    return {
        "ui_type": "exercise_recommendation_card",
        "payload": {
            "brief_text": "已为你生成习题推荐卡片。",
            "course": normalized_course,
            "topic": normalized_topic,
            "card_title": "习题推荐",
            "todo": "TODO: 接入真实习题推荐服务，并返回可渲染的习题卡片列表。",
        },
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
