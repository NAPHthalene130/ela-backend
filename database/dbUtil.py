from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import inspect, text

from database.extensions import db
from database.models import UserChatWindowTable, WindowChatNode, CrourseNode


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


def deleteUserChatWindow(windowId):
    try:
        WindowChatNode.query.filter_by(windowID=windowId).delete()
        UserChatWindowTable.query.filter_by(windowsId=windowId).delete()
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def getCourseList():
    try:
        courses = CrourseNode.query.all()
        course_list = []
        for course in courses:
            course_name = getattr(course, 'courseName', None) or getattr(course, 'course', None)
            if course_name:
                course_list.append(course_name)
        return course_list
    except Exception:
        try:
            columns = {column["name"] for column in inspect(db.engine).get_columns('courseTable')}
            target_column = 'course' if 'course' in columns else 'courseName' if 'courseName' in columns else None
            if not target_column:
                return []
            rows = db.session.execute(text(f'SELECT "{target_column}" FROM "courseTable"')).all()
            return [row[0] for row in rows if row and row[0]]
        except Exception:
            return []

