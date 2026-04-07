from agent.tools import get_finally_response, render_prompt


def _invoke_with_langchain(
    msg: str, user_id: str = "", chat_window_id: str = "", course: str = ""
) -> str:
    # 延迟导入，避免在未安装 LangChain 依赖时导致应用启动失败
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    from project_config import API_KEY, BASE_URL, Pro_Model

    llm = ChatOpenAI(
        model=Pro_Model,
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.2,
    )
    response = llm.invoke(
        [
            SystemMessage(
                content=render_prompt(
                    "system_prompt.txt",
                    {
                        "msg": msg or "",
                        "user_id": user_id or "",
                        "chat_window_id": chat_window_id or "",
                        "course": course or "",
                    },
                )
            ),
            HumanMessage(content=msg),
        ]
    )
    return getattr(response, "content", "") or ""


def run_agent_stream(
    msg: str, user_id: str = "", chat_window_id: str = "", course: str = ""
):
    """LangChain Agent 流式入口：按步骤输出提示与最终回复内容。"""
    clean_msg = (msg or "").strip()
    if not clean_msg:
        return

    yield {"type": "tip", "data": "正在思考"}
    embedded_msg = render_prompt(
        "system_prompt.txt",
        {
            "msg": clean_msg,
            "user_id": user_id or "",
            "chat_window_id": chat_window_id or "",
            "course": course or "",
        },
    )

    try:
        # 主路径：先让 LangChain 完成中间推理，再进入最终回答工具
        processed_msg = _invoke_with_langchain(
            embedded_msg, user_id, chat_window_id, course
        ) or embedded_msg
    except Exception:
        # 兜底路径：LangChain 异常时继续使用原始嵌入文本
        processed_msg = embedded_msg

    yield {"type": "tip", "data": "正在生成最终回答"}
    for piece in get_finally_response(
        processed_msg,
        user_id=user_id,
        chat_window_id=chat_window_id,
        course=course,
    ):
        yield {"type": "content", "data": piece}
    yield {"type": "done", "data": ""}


def run_agent(msg: str, user_id: str = "", chat_window_id: str = "", course: str = "") -> str:
    all_parts = []
    for event in run_agent_stream(msg, user_id, chat_window_id, course):
        if event.get("type") == "content":
            all_parts.append(event.get("data", ""))
    return "".join(all_parts)
