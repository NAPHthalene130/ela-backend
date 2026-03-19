from database.models import CQNode
from repositories.cq_repository import add_cq_node, update_cq_node
from services.chat_service import (
    create_window_for_user,
    get_course_list,
    get_history_by_window,
    get_windows_by_user,
    save_message,
)
from repositories.chat_repository import delete_user_chat_window


def creatChatWindow(userID):
    return create_window_for_user(userID)


def addChatMessage(windowID, content, isUserSend):
    return save_message(windowID, content, isUserSend)


def getChatHistory(windowID):
    return get_history_by_window(windowID)


def getWindowHistory(userID):
    return get_windows_by_user(userID)


def deleteUserChatWindow(windowId):
    return delete_user_chat_window(windowId)


def getCourseList():
    return get_course_list()


def addCQ(cqNode: CQNode):
    return add_cq_node(cqNode)


def updateCQ(cqNode: CQNode):
    return update_cq_node(cqNode)
