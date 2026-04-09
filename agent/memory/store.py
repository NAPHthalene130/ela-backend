from pathlib import Path

from repositories.chat_repository import get_chat_history

DATABASE_URL = f"sqlite:///{(Path(__file__).resolve().parents[2] / 'instance' / 'project.db').as_posix()}"


def get_session_history(session_id: str):
    try:
        from langchain_community.chat_message_histories import SQLChatMessageHistory
    except Exception as exc:
        raise RuntimeError("缺少 SQLChatMessageHistory 依赖") from exc
    return SQLChatMessageHistory(
        session_id=str(session_id or "").strip(),
        connection_string=DATABASE_URL,
    )


def get_recent_messages(chat_window_id: str, limit: int = 6) -> list[dict]:
    if not chat_window_id:
        return []
    history = get_chat_history(chat_window_id)
    if not history:
        return []
    safe_limit = max(1, min(int(limit or 6), 12))
    return history[-safe_limit:]


def build_history_prompt(chat_window_id: str, limit: int = 6) -> str:
    messages = get_recent_messages(chat_window_id, limit=limit)
    lines = []
    for item in messages:
        role = "用户" if item.get("isUserSend") else "助手"
        content = str(item.get("content", "") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines).strip()
