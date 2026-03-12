from datetime import datetime, timezone
from uuid import uuid4

from database.extensions import db
from database.models import UserChatWindowTable, WindowChatNode


def creatChatWindow(userID):
    windows_id = str(uuid4())
    while UserChatWindowTable.query.filter_by(windowsId=windows_id).first():
        windows_id = str(uuid4())

    chat_window = UserChatWindowTable(
        id=userID,
        windowsId=windows_id,
        title='新对话',
        createTime=datetime.now(timezone.utc).isoformat()
    )

    try:
        db.session.add(chat_window)
        db.session.commit()
        return chat_window.windowsId
    except Exception:
        db.session.rollback()
        return None


def addChatMessage(windowID, content, isUserSend):
    chat_node = WindowChatNode(
        windowID=windowID,
        content=content,
        isUserSend=isUserSend,
        sendTime=datetime.now(timezone.utc).isoformat()
    )

    try:
        db.session.add(chat_node)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def getChatHistory(windowID):
    try:
        # 按 id 升序排列，保证时间顺序（因为 id 是自增的）
        history = WindowChatNode.query.filter_by(windowID=windowID).order_by(WindowChatNode.id.asc()).all()
        return [{
            'id': node.id,
            'windowID': node.windowID,
            'content': node.content,
            'isUserSend': node.isUserSend,
            'sendTime': node.sendTime
        } for node in history]
    except Exception:
        return []


def getWindowHistory(userID):
    try:
        # 按 createTime 升序排列（早的在上面）
        windows = UserChatWindowTable.query.filter_by(id=userID).order_by(UserChatWindowTable.createTime.asc()).all()
        return [{
            'windowsId': win.windowsId,
            'title': win.title,
            'createTime': win.createTime,
            'id': win.id
        } for win in windows]
    except Exception:
        return []

