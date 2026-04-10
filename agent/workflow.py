import json

from agent.tools import (
    get_exercise_recommendation_card,
    get_knowledge_graph_card,
    get_learning_review_card,
)
from agent.adapters.stream_adapter import generate_json_packet, generate_text_stream
from agent.memory import build_history_prompt
from agent.providers.doubao import auth_gate, create_langchain_chat_model
from repositories.card_repository import add_card

INTENT_SYSTEM_PROMPT = """
你是学习平台的意图识别器。
请根据用户输入判断是否需要调用工具，并输出严格 JSON，不要输出其他内容。

JSON 结构如下：
{{
  "intent": "chat|exercise_recommendation|knowledge_graph|learning_review",
  "course_name": "",
  "topic": "",
  "query_text": "",
  "need_tool": true,
  "tool_name": "exercise_recommendation|knowledge_graph|learning_review|none"
}}

规则：
1. 用户要题目推荐、练习建议时，intent=exercise_recommendation。
2. 用户要知识点关系、图谱结构时，intent=knowledge_graph。
3. 用户要学习记录、学习总结、掌握情况分析时，intent=learning_review。
4. 其余场景为 chat。
"""

ANSWER_SYSTEM_PROMPT = """
你是 ELA 学习平台的教学助手。
请先判断用户输入是否包含“知识问答内容”和“功能卡片请求”两部分。
1. 若同时包含两部分：先回答知识问答内容，再单独追加一句“已为您生成了XXXX功能卡片”。
2. 若只包含功能卡片请求：不要展开知识讲解，只输出“已为您生成了XXXX功能卡片”。
3. 若不需要功能卡片：正常回答用户问题。
其中 XXXX 需根据意图填写为：习题推荐、知识图谱、学情回顾。
输出要简洁、准确、便于学生理解。
不要输出 JSON。
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
    intent_llm = create_langchain_chat_model(
        model_level="lite",
        streaming=False,
        temperature=0,
    )
    answer_llm = create_langchain_chat_model(
        model_level="pro",
        streaming=True,
        temperature=0,
        enable_reasoning=True,
    )
    intent_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", INTENT_SYSTEM_PROMPT),
            ("system", "当前课程：{course}"),
            ("human", "{input}"),
        ]
    )
    answer_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ANSWER_SYSTEM_PROMPT),
            ("system", "当前课程：{course}"),
            ("system", "识别到的意图：{intent}"),
            ("system", "最近几轮历史对话：\n{history_context}"),
            ("human", "{input}"),
        ]
    )
    _WORKFLOW_COMPONENTS = {
        "intent_chain": intent_prompt | intent_llm,
        "answer_chain": answer_prompt | answer_llm,
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


def _fallback_intent(message: str, course: str) -> dict:
    content = (message or "").strip().lower()
    if any(keyword in content for keyword in ("例题", "练习题", "推荐题", "出一道题", "来一道题")):
        return {
            "intent": "exercise_recommendation",
            "course_name": course or "",
            "topic": message,
            "query_text": message,
            "need_tool": True,
            "tool_name": "exercise_recommendation",
        }
    if any(keyword in content for keyword in ("图谱", "关系图", "neo4j", "知识网络", "graph")):
        return {
            "intent": "knowledge_graph",
            "course_name": course or "",
            "topic": "",
            "query_text": message,
            "need_tool": True,
            "tool_name": "knowledge_graph",
        }
    if any(keyword in content for keyword in ("学情", "学习情况", "掌握度", "回顾", "复盘", "总结")):
        return {
            "intent": "learning_review",
            "course_name": course or "",
            "topic": "",
            "query_text": message,
            "need_tool": True,
            "tool_name": "learning_review",
        }
    return {
        "intent": "chat",
        "course_name": course or "",
        "topic": "",
        "query_text": message,
        "need_tool": False,
        "tool_name": "none",
    }


def _plan_intent(message: str, course: str) -> dict:
    intent_chain = _get_workflow_components()["intent_chain"]
    response = intent_chain.invoke(
        {
            "input": message,
            "course": course or "",
        }
    )
    parsed = _extract_json_block(_extract_text_content(getattr(response, "content", "")))
    if not parsed or not parsed.get("intent"):
        return _fallback_intent(message, course)
    parsed.setdefault("course_name", course or "")
    parsed.setdefault("topic", "")
    parsed.setdefault("query_text", message)
    parsed.setdefault("need_tool", parsed.get("intent") != "chat")
    parsed.setdefault("tool_name", "none")
    return parsed


def _invoke_tool(tool_obj, payload: dict) -> dict:
    if hasattr(tool_obj, "invoke"):
        return tool_obj.invoke(payload)
    return tool_obj(**payload)


def _resolve_tool_result(
    intent: dict,
    user_id: str,
    chat_window_id: str,
) -> tuple[str, dict] | tuple[None, None]:
    tool_name = str(intent.get("tool_name", "") or "").strip().lower()
    course_name = str(intent.get("course_name", "") or "").strip()
    topic = str(intent.get("topic", "") or "").strip()
    query_text = str(intent.get("query_text", "") or "").strip()
    if tool_name == "exercise_recommendation":
        result = _invoke_tool(
            get_exercise_recommendation_card,
            {
                "course_name": course_name,
                "topic": topic or query_text,
                "chat_window_id": chat_window_id or "",
            },
        )
        return "exercise_recommendation", result
    if tool_name == "knowledge_graph":
        result = _invoke_tool(
            get_knowledge_graph_card,
            {
                "course_name": course_name,
                "query_text": query_text,
            },
        )
        return "knowledge_graph", result
    if tool_name == "learning_review":
        result = _invoke_tool(
            get_learning_review_card,
            {
                "course_name": course_name,
                "user_id": user_id or "",
            },
        )
        return "learning_review", result
    return None, None


def run_agentic_stream(msg: str, user_id: str = "", chat_window_id: str = "", course: str = ""):
    clean_msg = (msg or "").strip()
    if not clean_msg:
        return
    try:
        if not auth_gate(clean_msg):
            yield "data: " + json.dumps(
                {"type": "text", "content": "当前内容不适合讨论，请换一个试试吧"},
                ensure_ascii=False,
            ) + "\n\n"
            yield "data: [DONE]\n\n"
            return
        intent = _plan_intent(clean_msg, course or "")
        intent_name = str(intent.get("intent", "chat") or "chat").strip().lower()
        course_name = str(intent.get("course_name", "") or course or "").strip()
        need_tool = bool(intent.get("need_tool"))
        answer_chain = _get_workflow_components()["answer_chain"]
        yield from generate_text_stream(
            chain=answer_chain,
            payload={
                "input": clean_msg,
                "course": course_name,
                "intent": intent_name,
                "history_context": build_history_prompt(chat_window_id, limit=6),
            },
            emit_done=not need_tool,
        )
        if not need_tool:
            return
        mode, result = _resolve_tool_result(intent, user_id, chat_window_id)
        if (
            mode == "exercise_recommendation"
            and isinstance(result, dict)
            and result.get("type") == "questions"
        ):
            card_content = result.get("content")
            if isinstance(card_content, list):
                add_card(chat_window_id, json.dumps(card_content, ensure_ascii=False))
        if mode and isinstance(result, dict):
            yield from generate_json_packet(mode, result)
            return
        yield "data: [DONE]\n\n"
    except Exception as exc:
        yield "data: " + json.dumps(
            {"type": "error", "content": f"Agent 运行失败: {exc}"},
            ensure_ascii=False,
        ) + "\n\n"
        yield "data: [DONE]\n\n"
