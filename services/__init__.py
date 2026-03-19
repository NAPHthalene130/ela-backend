def normalize_user_type(user_type):
    from services.auth_service import normalize_user_type as _normalize_user_type

    return _normalize_user_type(user_type)


def login_user(user_id: str, password: str):
    from services.auth_service import login_user as _login_user

    return _login_user(user_id, password)


def register_user(user_id: str, password: str, email: str, email_code: str, user_type: str):
    from services.auth_service import register_user as _register_user

    return _register_user(user_id, password, email, email_code, user_type)


def require_email_code(email: str):
    from services.auth_service import require_email_code as _require_email_code

    return _require_email_code(email)


def check_user_id_exists(user_id: str) -> bool:
    from services.auth_service import check_user_id_exists as _check_user_id_exists

    return _check_user_id_exists(user_id)


def get_course_list():
    from services.chat_service import get_course_list as _get_course_list

    return _get_course_list()


def get_windows_by_user(user_id: str):
    from services.chat_service import get_windows_by_user as _get_windows_by_user

    return _get_windows_by_user(user_id)


def get_history_by_window(window_id: str):
    from services.chat_service import get_history_by_window as _get_history_by_window

    return _get_history_by_window(window_id)


def create_window_for_user(user_id: str):
    from services.chat_service import create_window_for_user as _create_window_for_user

    return _create_window_for_user(user_id)


def save_message(window_id: str, content: str, is_user_send: bool):
    from services.chat_service import save_message as _save_message

    return _save_message(window_id, content, is_user_send)


def stream_chat_response(user_id: str, chat_window_id: str, message: str, course: str = ""):
    from services.chat_service import stream_chat_response as _stream_chat_response

    return _stream_chat_response(user_id, chat_window_id, message, course)


def delete_window_for_user(user_id: str, window_id: str):
    from services.chat_service import delete_window_for_user as _delete_window_for_user

    return _delete_window_for_user(user_id, window_id)


__all__ = [
    "normalize_user_type",
    "login_user",
    "register_user",
    "require_email_code",
    "check_user_id_exists",
    "get_course_list",
    "get_windows_by_user",
    "get_history_by_window",
    "create_window_for_user",
    "save_message",
    "stream_chat_response",
    "delete_window_for_user",
]
