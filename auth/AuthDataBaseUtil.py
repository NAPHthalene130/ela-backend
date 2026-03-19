from services.auth_service import (
    login_user,
    normalize_user_type,
    register_user,
    require_email_code,
)


def login(user_id, password):
    return login_user(user_id, password)


def register(user_id, password, email, emailCode, user_type):
    return register_user(user_id, password, email, emailCode, user_type)


def requireEmailCode(email):
    return require_email_code(email)
