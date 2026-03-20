from werkzeug.security import check_password_hash, generate_password_hash

from core.extensions import db
from database.models import USER_TYPES, User
from repositories.auth_repository import get_user_by_email, get_user_by_id
from services.redis_service import get_redis_client

DEFAULT_REGISTER_CODE = "000000"


def normalize_user_type(user_type):
    """统一用户类型取值，避免脏数据写入数据库。"""
    if not isinstance(user_type, str):
        return None
    normalized = user_type.strip().lower()
    if normalized in USER_TYPES:
        return normalized
    return None


def login_user(user_id: str, password: str) -> User | None:
    user = get_user_by_id(user_id)
    if user and check_password_hash(user.passwordHash, password):
        return user
    return None


def get_user_profile(user_id: str) -> User | None:
    return get_user_by_id(user_id)


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "type": normalize_user_type(user.type),
    }


def check_user_id_exists(user_id: str) -> bool:
    return get_user_by_id(user_id) is not None


def register_user(user_id: str, password: str, email: str, email_code: str, user_type: str):
    """注册用户并校验邮箱验证码。"""
    normalized_type = normalize_user_type(user_type)
    if not normalized_type:
        return False, "Invalid user type"

    redis_client = None
    redis_key = f"email_code:{email}"
    if email_code != DEFAULT_REGISTER_CODE:
        redis_client = get_redis_client()
        if not redis_client:
            return False, "Redis service unavailable"
        stored_code = redis_client.get(redis_key)
        if not stored_code:
            return False, "Verification code expired or invalid"
        if stored_code.decode("utf-8") != email_code:
            return False, "Incorrect verification code"

    if get_user_by_id(user_id):
        return False, "User ID already exists"
    if get_user_by_email(email):
        return False, "Email already registered"

    new_user = User(
        id=user_id,
        email=email,
        passwordHash=generate_password_hash(password),
        type=normalized_type,
    )
    try:
        db.session.add(new_user)
        db.session.commit()
        if redis_client:
            redis_client.delete(redis_key)
        return True, "Registration successful"
    except Exception as exc:
        db.session.rollback()
        return False, f"Database error: {exc}"


def require_email_code(email: str):
    """生成并缓存邮箱验证码。"""
    if not email:
        return False, "Email is required"

    code = DEFAULT_REGISTER_CODE
    redis_client = get_redis_client()
    if redis_client:
        redis_key = f"email_code:{email}"
        try:
            redis_client.setex(redis_key, 120, code)
        except Exception:
            pass
    return True, f"Verification code sent: {code}"
