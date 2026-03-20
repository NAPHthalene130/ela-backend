from flask import Blueprint, Response, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from services.chat_service import (
    create_window_for_user,
    delete_window_for_user,
    get_course_list,
    get_history_by_window,
    get_windows_by_user,
    save_message,
    stream_chat_response,
)

chat_bp = Blueprint("chat", __name__)


@chat_bp.get("/courses")
@jwt_required()
def get_courses():
    """课程列表接口：返回可选课程名称集合。"""
    return success_response(get_course_list())


@chat_bp.get("/windows")
@jwt_required()
def get_windows():
    """会话窗口列表接口：按用户查询历史会话。"""
    current_user_id = get_jwt_identity()
    return success_response(get_windows_by_user(current_user_id))


@chat_bp.get("/history")
@jwt_required()
def get_history():
    """会话消息接口：返回指定会话下的消息记录。"""
    window_id = request.args.get("windowID")
    if not window_id:
        return fail_response("Missing windowID", 400)
    return success_response(get_history_by_window(window_id))


@chat_bp.post("/create")
@jwt_required()
def create_window():
    """创建会话接口：生成新的对话窗口。"""
    current_user_id = get_jwt_identity()
    window_id = create_window_for_user(current_user_id)
    if not window_id:
        return fail_response("Failed to create chat window", 500)
    return success_response({"windowID": window_id})


@chat_bp.post("/send")
@jwt_required()
def send_message():
    """普通消息接口：直接写入聊天消息。"""
    data = request.get_json(silent=True) or {}
    window_id = data.get("windowID")
    content = data.get("content")
    is_user_send = data.get("isUserSend", True)
    if not window_id or not content:
        return fail_response("Missing parameters", 400)

    if not save_message(window_id, content, bool(is_user_send)):
        return fail_response("Failed to save message", 500)
    return success_response(msg="Message sent")


@chat_bp.post("/stream")
@jwt_required()
def chat_stream():
    """流式聊天接口：边生成边返回文本。"""
    data = request.get_json(silent=True) or {}
    window_id = data.get("windowID")
    content = data.get("content")
    course = data.get("course")
    current_user_id = get_jwt_identity()
    if not window_id or not content:
        return fail_response("Missing parameters", 400)

    generator = stream_chat_response(current_user_id, window_id, content, course)
    return Response(stream_with_context(generator), mimetype="text/plain")


@chat_bp.post("/delete-window")
@jwt_required()
def delete_window():
    """删除会话接口：校验归属后删除窗口及消息。"""
    data = request.get_json(silent=True) or {}
    window_id = data.get("windowID")
    current_user_id = get_jwt_identity()
    if not window_id:
        return fail_response("Missing parameters", 400)

    success, status_code, message = delete_window_for_user(current_user_id, window_id)
    if not success:
        return fail_response(message, status_code)
    return success_response(msg=message)
