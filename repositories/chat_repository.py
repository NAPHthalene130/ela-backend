from datetime import datetime, timezone
from uuid import uuid4

from database.models import UserChatWindowTable, WindowChatNode


def create_chat_window(user_id: str) -> str | None:
    window_id = str(uuid4())
    while UserChatWindowTable.query.filter_by(windowsId=window_id).first():
        window_id = str(uuid4())

    chat_window = UserChatWindowTable(
        id=user_id,
        windowsId=window_id,
        title="新对话",
        createTime=datetime.now(timezone.utc).isoformat(),
    )
    return _save_chat_window(chat_window)


def _save_chat_window(window: UserChatWindowTable) -> str | None:
    from core.extensions import db

    try:
        db.session.add(window)
        db.session.commit()
        return window.windowsId
    except Exception:
        db.session.rollback()
        return None


def save_chat_message(window_id: str, content: str, is_user_send: bool) -> bool:
    from core.extensions import db

    chat_node = WindowChatNode(
        windowID=window_id,
        content=content,
        isUserSend=is_user_send,
        sendTime=datetime.now(timezone.utc).isoformat(),
    )
    try:
        db.session.add(chat_node)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def get_chat_history(window_id: str) -> list[dict]:
    try:
        history = (
            WindowChatNode.query.filter_by(windowID=window_id)
            .order_by(WindowChatNode.id.asc())
            .all()
        )
        return [
            {
                "id": node.id,
                "windowID": node.windowID,
                "content": node.content,
                "isUserSend": node.isUserSend,
                "sendTime": node.sendTime,
            }
            for node in history
        ]
    except Exception:
        return []


def get_window_history(user_id: str) -> list[dict]:
    try:
        windows = (
            UserChatWindowTable.query.filter_by(id=user_id)
            .order_by(UserChatWindowTable.createTime.asc())
            .all()
        )
        return [
            {
                "windowsId": win.windowsId,
                "title": win.title,
                "createTime": win.createTime,
                "id": win.id,
            }
            for win in windows
        ]
    except Exception:
        return []


def delete_user_chat_window(window_id: str) -> bool:
    from core.extensions import db

    try:
        WindowChatNode.query.filter_by(windowID=window_id).delete()
        UserChatWindowTable.query.filter_by(windowsId=window_id).delete()
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def is_window_owned_by_user(user_id: str, window_id: str) -> bool:
    target = UserChatWindowTable.query.filter_by(id=user_id, windowsId=window_id).first()
    return target is not None
