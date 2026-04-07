from agent.tools import auth_gate, get_finally_response


def run_agent_stream(
    msg: str, user_id: str = "", chat_window_id: str = "", course: str = ""
):
    """LangChain Agent 流式入口：按步骤输出提示与最终回复内容。"""
    clean_msg = (msg or "").strip()
    if not clean_msg:
        return

    yield {"type": "tip", "data": "正在思考"}
    if not auth_gate(clean_msg):
        yield {"type": "content", "data": "当前内容不适合讨论，请换一个试试吧"}
        yield {"type": "done", "data": ""}
        return

    yield {"type": "tip", "data": "正在生成最终回答"}
    for chunk in get_finally_response(
        clean_msg,
        user_id=user_id,
        chat_window_id=chat_window_id,
        course=course,
    ):
        if isinstance(chunk, dict):
            event_type = chunk.get("type", "content")
            event_data = chunk.get("data", "")
        else:
            event_type = "content"
            event_data = chunk
        if event_data:
            yield {"type": event_type, "data": event_data}
    yield {"type": "done", "data": ""}


def run_agent(msg: str, user_id: str = "", chat_window_id: str = "", course: str = "") -> str:
    all_parts = []
    for event in run_agent_stream(msg, user_id, chat_window_id, course):
        if event.get("type") == "content":
            all_parts.append(event.get("data", ""))
    return "".join(all_parts)
