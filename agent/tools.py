try:
    from langchain_core.tools import tool
except Exception:
    def tool(func):
        return func


def _normalize_course_name(course_name: str) -> str:
    return (course_name or "").strip()


@tool
def get_example_card(course_name: str, topic: str = "") -> dict:
    """
    当用户明确想要做练习题、来一道例题、生成题目卡片、挂载习题组件时调用。

    需要提取的参数：
    1. course_name：用户当前讨论的课程或学科名称，例如数据结构、操作系统、高等数学。
    2. topic：用户想练习的具体知识点，例如二分查找、动态规划、极限。

    当用户只是要求纯文字讲解时不要调用本工具。
    当用户希望在聊天区域旁边出现可做题的组件时优先调用本工具。
    返回值必须是 Generative UI 可以直接消费的 example_card 字典结构。
    """
    normalized_course = _normalize_course_name(course_name) or "通用"
    normalized_topic = (topic or "").strip() or "基础练习"
    return {
        "ui_type": "example_card",
        "payload": {
            "course": normalized_course,
            "topic": normalized_topic,
            "cards": [
                {
                    "id": f"{normalized_course}-{normalized_topic}-example-1",
                    "title": f"{normalized_course} · {normalized_topic}",
                    "stem": f"请完成一题与“{normalized_topic}”相关的练习。",
                    "answer_type": "text",
                    "difficulty": "medium",
                }
            ],
        },
    }


@tool
def get_knowledge_graph(course_name: str, query_text: str = "") -> dict:
    """
    当用户明确要求查看知识图谱、关系图、概念网络，或希望从 Neo4j 中查询知识点之间的关系时调用。

    需要提取的参数：
    1. course_name：课程或学科名称，例如数据结构、离散数学、计算机网络。
    2. query_text：用户真正想查询的知识点、主题或原始问题，例如二分查找、红黑树与AVL树的关系。

    当用户仅需要文字解释时不要调用本工具。
    当用户希望前端渲染可拖拽图谱组件时调用本工具。
    返回值必须是 Generative UI 可以直接消费的 graph 字典结构。
    """
    from llm.retrievers import query_knowledge_graph

    normalized_course = _normalize_course_name(course_name) or "通用"
    graph_data = query_knowledge_graph(
        query_text=(query_text or "").strip(),
        course=normalized_course,
        limit=20,
    )
    if graph_data.get("ok"):
        return {
            "ui_type": "graph",
            "payload": {
                "course": normalized_course,
                "nodes": graph_data.get("nodes", []),
                "edges": graph_data.get("edges", []),
                "source": graph_data.get("source", "neo4j"),
            },
        }

    fallback_keyword = (query_text or "").strip() or "核心知识点"
    return {
        "ui_type": "graph",
        "payload": {
            "course": normalized_course,
            "nodes": [
                {
                    "id": "fallback-root",
                    "label": fallback_keyword,
                    "type": "concept",
                }
            ],
            "edges": [],
            "source": "mock",
            "fallback_reason": graph_data.get("reason", "unknown"),
        },
    }


@tool
def get_page_navigation(target_page: str, course_name: str = "", target_id: str = "") -> dict:
    """
    当用户明确要求跳转到某个页面时调用，例如考试列表、考试详情、练习大厅、聊天页、设置页。

    需要提取的参数：
    1. target_page：目标页面语义，建议取值 exam_list、exam_detail、practice、chat、settings。
    2. course_name：可选，若用户提到课程名称则提取出来，供前端后续做上下文展示。
    3. target_id：可选，若用户明确指定考试或任务 ID 则提取出来。

    当用户只是询问如何学习、如何解释知识点时不要调用本工具。
    当用户的核心需求是页面跳转而不是知识问答时调用本工具。
    返回值必须是 Generative UI 可以直接消费的 route_intent 字典结构。
    """
    normalized_page = (target_page or "").strip().lower()
    normalized_course = _normalize_course_name(course_name)
    normalized_target_id = (target_id or "").strip()
    route_map = {
        "exam_list": "/student/exam-list",
        "exam_detail": "/student/exam-detail",
        "practice": "/student/practice",
        "chat": "/student/chat",
        "settings": "/student/settings",
    }
    route = route_map.get(normalized_page, "/student/chat")
    if normalized_page == "exam_detail" and normalized_target_id:
        route = f"{route}?assignmentId={normalized_target_id}"

    return {
        "ui_type": "route_intent",
        "payload": {
            "route": route,
            "target_page": normalized_page or "chat",
            "course": normalized_course,
            "target_id": normalized_target_id,
        },
    }


TOOLS = [
    get_example_card,
    get_knowledge_graph,
    get_page_navigation,
]
