from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from services.assignment_service import (
    create_assignment_for_teacher,
    get_assignments_by_teacher,
    get_assignment_student_answers_for_teacher,
)

assignment_bp = Blueprint("assignment", __name__)


@assignment_bp.get("/list")
@jwt_required()
def get_assignment_list():
    """查询当前教师的任务列表。"""
    teacher_id = request.args.get("teacherID") or get_jwt_identity()
    current_user_id = get_jwt_identity()
    if teacher_id != current_user_id:
        return fail_response("Forbidden", 403)
    return success_response(get_assignments_by_teacher(teacher_id))


@assignment_bp.post("/create")
@jwt_required()
def create_assignment():
    """创建教师任务。"""
    payload = request.get_json(silent=True) or {}
    current_user_id = get_jwt_identity()
    created_assignment, status_code, message = create_assignment_for_teacher(
        current_user_id,
        payload,
    )
    if not created_assignment:
        return fail_response(message, status_code)
    return success_response(created_assignment, message, status_code)


@assignment_bp.get("/student-answers")
@jwt_required()
def get_assignment_student_answers():
    """查询指定任务下某个学生的题目与作答详情。"""
    assignment_id = request.args.get("assignmentID")
    student_id = (request.args.get("studentID") or "").strip()
    if not assignment_id or not student_id:
        return fail_response("Missing assignmentID or studentID", 400)

    try:
        assignment_id_int = int(assignment_id)
    except ValueError:
        return fail_response("Invalid assignmentID", 400)

    current_user_id = get_jwt_identity()
    result, status_code, message = get_assignment_student_answers_for_teacher(
        current_user_id,
        assignment_id_int,
        student_id,
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)
