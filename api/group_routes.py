from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from services.group_service import (
    add_student_to_group_for_teacher,
    create_group_for_teacher,
    get_group_students_for_teacher,
    get_groups_by_teacher,
)

group_bp = Blueprint("group", __name__)


@group_bp.get("/list")
@jwt_required()
def get_group_list():
    """查询当前教师的小组列表。"""
    teacher_id = request.args.get("teacherID") or get_jwt_identity()
    current_user_id = get_jwt_identity()
    if teacher_id != current_user_id:
        return fail_response("Forbidden", 403)
    return success_response(get_groups_by_teacher(teacher_id))


@group_bp.post("/create")
@jwt_required()
def create_group():
    """创建教师小组。"""
    data = request.get_json(silent=True) or {}
    group_name = (data.get("name") or "").strip()
    if not group_name:
        return fail_response("Missing group name", 400)

    teacher_id = get_jwt_identity()
    group_id = create_group_for_teacher(teacher_id, group_name)
    if not group_id:
        return fail_response("Failed to create group", 500)
    return success_response({"id": group_id, "name": group_name}, "Group created")


@group_bp.get("/students")
@jwt_required()
def get_group_students():
    """查询指定小组的学生 ID 列表。"""
    group_id = request.args.get("groupID")
    if not group_id:
        return fail_response("Missing groupID", 400)

    try:
        group_id_int = int(group_id)
    except ValueError:
        return fail_response("Invalid groupID", 400)

    teacher_id = get_jwt_identity()
    students = get_group_students_for_teacher(teacher_id, group_id_int)
    if students is None:
        return fail_response("Forbidden", 403)
    return success_response(students)


@group_bp.post("/add-student")
@jwt_required()
def add_group_student():
    """向指定小组添加学生。"""
    data = request.get_json(silent=True) or {}
    group_id = data.get("groupID")
    student_id = (data.get("studentID") or "").strip()
    if group_id is None or not student_id:
        return fail_response("Missing parameters", 400)

    try:
        group_id_int = int(group_id)
    except ValueError:
        return fail_response("Invalid groupID", 400)

    teacher_id = get_jwt_identity()
    success, message = add_student_to_group_for_teacher(
        teacher_id, group_id_int, student_id
    )
    if not success:
        if message == "Forbidden":
            return fail_response(message, 403)
        return fail_response(message, 400)
    return success_response(msg="Student added")
