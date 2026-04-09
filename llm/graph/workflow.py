import json

from agent.tools import get_knowledge_graph, get_page_navigation
from llm.adapters.stream_adapter import generate_json_packet, generate_text_stream
from llm.memory import build_history_prompt
from llm.providers.doubao import auth_gate, create_langchain_chat_model

PLANNER_SYSTEM_PROMPT = """
你是学习平台的任务规划器。
你只能在以下模式中选择一个：
1. chat：用户只是想让你解释、分析、讲解、答疑。
2. example_card：用户想要例题、练习题、选择题、出一道题。
3. knowledge_graph：用户想看知识图谱、关系图、Neo4j 图数据。
4. page_navigation：用户想跳转到考试、做题、练习、聊天、设置等页面。

你必须输出严格 JSON，不要输出 Markdown，不要输出解释。
JSON 字段如下：
{{
  "mode": "chat|example_card|knowledge_graph|page_navigation",
  "course_name": "",
  "topic": "",
  "query_text": "",
  "target_page": "exam_list|practice|chat",
  "target_id": ""
}}
"""

CHAT_SYSTEM_PROMPT = """
你是教育平台中的智能学习助手。
请根据用户当前问题、最近几轮历史对话和图谱检索补充信息，给出准确、简洁、便于学生理解的中文回答。
如果图谱补充信息为空，就只根据历史和问题回答。
不要输出 JSON。
"""

EXAMPLE_CARD_SYSTEM_PROMPT = """
你是教育平台中的命题助手。
请根据用户问题、课程和最近几轮历史对话，输出严格 JSON，不要输出 Markdown，不要输出额外解释。
JSON 结构如下：
{{
  "brief_text": "一句简短引导语，例如：下面是我为你准备的一道例题。",
  "card": {{
    "title": "",
    "stem": "",
    "options": [
      {{"key": "A", "text": ""}},
      {{"key": "B", "text": ""}},
      {{"key": "C", "text": ""}},
      {{"key": "D", "text": ""}}
    ],
    "answer": "",
    "explanation": ""
  }}
}}
题目必须是选择题。
"""

_WORKFLOW_COMPONENTS = None


def _get_workflow_components():
    global _WORKFLOW_COMPONENTS
    if _WORKFLOW_COMPONENTS is not None:
        return _WORKFLOW_COMPONENTS

    try:
        from langchain_core.prompts import ChatPromptTemplate
    except Exception as exc:
        raise RuntimeError("缺少 LangChain Core 依赖。") from exc

    planner_llm = create_langchain_chat_model(
        model_level="lite",
        streaming=False,
        temperature=0,
    )
    chat_llm = create_langchain_chat_model(
        model_level="pro",
        streaming=True,
        temperature=0,
    )
    example_llm = create_langchain_chat_model(
        model_level="pro",
        streaming=False,
        temperature=0,
    )

    planner_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PLANNER_SYSTEM_PROMPT),
            ("system", "当前课程：{course}"),
            ("human", "{input}"),
        ]
    )
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CHAT_SYSTEM_PROMPT),
            ("system", "当前课程：{course}"),
            ("system", "最近几轮历史对话：\n{history_context}"),
            ("system", "图谱检索补充信息：\n{graph_context}"),
            ("human", "{input}"),
        ]
    )
    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", EXAMPLE_CARD_SYSTEM_PROMPT),
            ("system", "当前课程：{course}"),
            ("system", "最近几轮历史对话：\n{history_context}"),
            ("human", "{input}"),
        ]
    )
    _WORKFLOW_COMPONENTS = {
        "planner_chain": planner_prompt | planner_llm,
        "chat_chain": chat_prompt | chat_llm,
        "example_chain": example_prompt | example_llm,
    }
    return _WORKFLOW_COMPONENTS


def _extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "".join(parts).strip()
    return str(content or "").strip()


def _extract_json_block(raw_text: str) -> dict:
    content = (raw_text or "").strip()
    if not content:
        return {}
    try:
        return json.loads(content)
    except Exception:
        pass

    start_index = content.find("{")
    end_index = content.rfind("}")
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return {}
    try:
        return json.loads(content[start_index : end_index + 1])
    except Exception:
        return {}


def _fallback_plan(message: str, course: str) -> dict:
    content = (message or "").strip().lower()
    if any(keyword in content for keyword in ("例题", "练习题", "选择题", "出一道题", "来一道题")):
        return {
            "mode": "example_card",
            "course_name": course or "",
            "topic": message,
            "query_text": message,
            "target_page": "",
            "target_id": "",
        }
    if any(keyword in content for keyword in ("图谱", "关系图", "neo4j", "graph")):
        return {
            "mode": "knowledge_graph",
            "course_name": course or "",
            "topic": "",
            "query_text": message,
            "target_page": "",
            "target_id": "",
        }
    if any(keyword in content for keyword in ("考试", "做题", "练习页面", "跳转", "进入考试")):
        target_page = "exam_list" if "考试" in content else "practice"
        return {
            "mode": "page_navigation",
            "course_name": course or "",
            "topic": "",
            "query_text": message,
            "target_page": target_page,
            "target_id": "",
        }
    return {
        "mode": "chat",
        "course_name": course or "",
        "topic": "",
        "query_text": message,
        "target_page": "",
        "target_id": "",
    }


def _plan_request(message: str, course: str) -> dict:
    planner_chain = _get_workflow_components()["planner_chain"]
    response = planner_chain.invoke(
        {
            "input": message,
            "course": course or "",
        }
    )
    parsed = _extract_json_block(_extract_text_content(getattr(response, "content", "")))
    if not parsed or not parsed.get("mode"):
        return _fallback_plan(message, course)
    parsed.setdefault("course_name", course or "")
    parsed.setdefault("topic", "")
    parsed.setdefault("query_text", message)
    parsed.setdefault("target_page", "")
    parsed.setdefault("target_id", "")
    return parsed


def _format_graph_context(query_text: str, course_name: str) -> str:
    try:
        from llm.retrievers import query_knowledge_graph
    except Exception:
        return ""
    graph_data = query_knowledge_graph(
        query_text=query_text,
        course=course_name or "",
        limit=8,
    )
    if not graph_data.get("ok"):
        return ""
    nodes = graph_data.get("nodes", [])[:8]
    edges = graph_data.get("edges", [])[:12]
    lines = []
    if nodes:
        lines.append(
            "节点: " + "；".join(f"{item.get('label', '')}({item.get('type', '')})" for item in nodes)
        )
    if edges:
        lines.append(
            "关系: " + "；".join(
                f"{item.get('source', '')}-{item.get('label', '')}-{item.get('target', '')}"
                for item in edges
            )
        )
    return "\n".join(lines).strip()


def _build_example_card_result(message: str, course_name: str, chat_window_id: str) -> dict:
    example_chain = _get_workflow_components()["example_chain"]
    response = example_chain.invoke(
        {
            "input": message,
            "course": course_name or "",
            "history_context": build_history_prompt(chat_window_id, limit=6),
        }
    )
    parsed = _extract_json_block(_extract_text_content(getattr(response, "content", "")))
    brief_text = str(parsed.get("brief_text", "") or "下面是我为你准备的一道例题。").strip()
    card = parsed.get("card") or {}
    title = str(card.get("title", "") or f"{course_name or '通用'}例题").strip()
    stem = str(card.get("stem", "") or "请完成下面这道选择题。").strip()
    options = card.get("options")
    if not isinstance(options, list) or len(options) < 4:
        options = [
            {"key": "A", "text": "选项 A"},
            {"key": "B", "text": "选项 B"},
            {"key": "C", "text": "选项 C"},
            {"key": "D", "text": "选项 D"},
        ]
    return {
        "ui_type": "example_card",
        "payload": {
            "brief_text": brief_text,
            "course": course_name or "",
            "topic": stem,
            "cards": [
                {
                    "id": f"{course_name or 'common'}-example-1",
                    "title": title,
                    "stem": stem,
                    "options": options,
                    "answer": str(card.get("answer", "") or "").strip(),
                    "explanation": str(card.get("explanation", "") or "").strip(),
                    "answer_type": "single_choice",
                }
            ],
        },
    }


def _build_graph_result(query_text: str, course_name: str) -> dict:
    return get_knowledge_graph.invoke(
        {
            "course_name": course_name or "",
            "query_text": query_text or "",
        }
    )


def _build_navigation_result(message: str, plan: dict, course_name: str) -> dict:
    target_page = str(plan.get("target_page", "") or "").strip().lower()
    if not target_page:
        target_page = "exam_list" if "考试" in (message or "") else "practice"
    return get_page_navigation.invoke(
        {
            "target_page": target_page,
            "course_name": course_name or "",
            "target_id": str(plan.get("target_id", "") or ""),
        }
    )


def run_agentic_stream(msg: str, user_id: str = "", chat_window_id: str = "", course: str = ""):
    clean_msg = (msg or "").strip()
    if not clean_msg:
        return
    if not auth_gate(clean_msg):
        yield "data: " + json.dumps(
            {"type": "text", "content": "当前内容不适合讨论，请换一个试试吧"},
            ensure_ascii=False,
        ) + "\n\n"
        yield "data: [DONE]\n\n"
        return

    try:
        plan = _plan_request(clean_msg, course or "")
        mode = str(plan.get("mode", "chat") or "chat").strip().lower()
        course_name = str(plan.get("course_name", "") or course or "").strip()
        if mode == "chat":
            chat_chain = _get_workflow_components()["chat_chain"]
            yield from generate_text_stream(
                chain=chat_chain,
                payload={
                    "input": clean_msg,
                    "course": course_name,
                    "history_context": build_history_prompt(chat_window_id, limit=6),
                    "graph_context": _format_graph_context(clean_msg, course_name),
                },
            )
            return
        if mode == "example_card":
            result = _build_example_card_result(clean_msg, course_name, chat_window_id)
            yield from generate_json_packet("example_card", result)
            return
        if mode == "knowledge_graph":
            result = _build_graph_result(
                query_text=str(plan.get("query_text", "") or clean_msg),
                course_name=course_name,
            )
            yield from generate_json_packet("knowledge_graph", result)
            return
        result = _build_navigation_result(clean_msg, plan, course_name)
        yield from generate_json_packet("page_navigation", result)
    except Exception as exc:
        yield "data: " + json.dumps(
            {"type": "error", "content": f"LangChain Agent 运行失败: {exc}"},
            ensure_ascii=False,
        ) + "\n\n"
        yield "data: [DONE]\n\n"
