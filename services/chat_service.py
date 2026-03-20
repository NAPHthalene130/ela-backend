from repositories.chat_repository import (
    create_chat_window,
    delete_user_chat_window,
    get_chat_history,
    get_window_history,
    is_window_owned_by_user,
    save_chat_message,
)
from repositories.course_repository import get_course_list as fetch_course_list
from util.getLlmResponse import getLlmRes


def get_course_list() -> list[str]:
    return fetch_course_list()


def get_windows_by_user(user_id: str) -> list[dict]:
    return get_window_history(user_id)


def get_history_by_window(window_id: str) -> list[dict]:
    return get_chat_history(window_id)


def create_window_for_user(user_id: str) -> str | None:
    return create_chat_window(user_id)


def save_message(window_id: str, content: str, is_user_send: bool) -> bool:
    return save_chat_message(window_id, content, is_user_send)


def delete_window_for_user(user_id: str, window_id: str):
    """删除用户会话前先校验归属关系。"""
    if not is_window_owned_by_user(user_id, window_id):
        return False, 404, "Window not found"
    success = delete_user_chat_window(window_id)
    if not success:
        return False, 500, "Failed to delete window"
    return True, 200, "Window deleted"


def stream_chat_response(user_id: str, chat_window_id: str, message: str, course: str = ""):
    """执行流式聊天并在流结束后落库完整回复。"""
    save_chat_message(chat_window_id, message, True)
    prompt = f"请返回以下内容:userId={user_id}\nchatWindowID={chat_window_id}\ncourse={course or ''}"

    def generate():
        try:
            full_content = getLlmRes(message, prompt)
            yield full_content
            save_chat_message(chat_window_id, full_content, False)
        except Exception as exc:
            yield f"\n[System Error: {exc}]"

    return generate()
