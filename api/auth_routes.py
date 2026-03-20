from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from services.auth_service import (
    check_user_id_exists,
    get_user_profile,
    login_user,
    normalize_user_type,
    register_user,
    require_email_code,
    serialize_user,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/login")
def login_route():
    """登录接口：校验账号密码并签发 JWT。"""
    data = request.get_json(silent=True) or {}
    user_id = data.get("id")
    password = data.get("password")
    if not user_id or not password:
        return fail_response("Missing id or password", 400)

    user = login_user(user_id, password)
    if not user:
        return fail_response("Invalid id or password", 401)

    token = create_access_token(identity=user.id)
    return jsonify(
        {
            "status": "success",
            "msg": "Login successful",
            "user": serialize_user(user),
            "token": token,
        }
    )


@auth_bp.get("/me")
@jwt_required()
def me_route():
    """返回当前 JWT 对应的用户信息，供前端恢复会话。"""
    current_user_id = get_jwt_identity()
    user = get_user_profile(current_user_id)
    if not user:
        return fail_response("User not found", 404)

    return jsonify(
        {
            "status": "success",
            "msg": "Session valid",
            "user": serialize_user(user),
        }
    )


@auth_bp.post("/register")
def register_route():
    """注册接口：完成邮箱验证码校验并创建用户。"""
    data = request.get_json(silent=True) or {}
    user_id = data.get("id")
    password = data.get("password")
    email = data.get("email")
    email_code = data.get("emailCode")
    user_type = normalize_user_type(data.get("type"))
    if not all([user_id, password, email, email_code, user_type]):
        return fail_response("Missing required fields", 400)

    success, message = register_user(user_id, password, email, email_code, user_type)
    if not success:
        return fail_response(message, 400)
    return success_response(msg=message)


@auth_bp.post("/send-code")
def send_code_route():
    """验证码接口：生成并写入 Redis。"""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email:
        return fail_response("Missing email", 400)

    success, message = require_email_code(email)
    if not success:
        return fail_response(message, 500)
    return success_response(msg=message)


@auth_bp.get("/check-id")
def check_id_route():
    """检测用户 ID 是否已存在。"""
    user_id = request.args.get("id")
    if not user_id:
        return fail_response("Missing id parameter", 400)

    exists = check_user_id_exists(user_id)
    if exists:
        return jsonify({"status": "success", "exists": True, "msg": "User ID exists"})
    return jsonify({"status": "success", "exists": False, "msg": "User ID available"})
