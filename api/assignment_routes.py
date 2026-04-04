from flask import Blueprint, current_app, request, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from services.assignment_service import (
    create_assignment_for_teacher,
    delete_assignment_for_teacher,
    get_assignment_exam_detail_for_student,
    get_assignments_by_teacher,
    get_assignments_by_student,
    get_assignment_student_answers_for_teacher,
    save_assignment_answers_for_student,
)

assignment_bp = Blueprint("assignment", __name__)
student_assignment_bp = Blueprint("student_assignment", __name__)


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


@assignment_bp.post("/delete")
@jwt_required()
def delete_assignment():
    """删除当前教师名下的指定任务。"""
    payload = request.get_json(silent=True) or {}
    assignment_id = payload.get("assignmentID")
    if assignment_id is None:
        return fail_response("Missing assignmentID", 400)

    try:
        assignment_id_int = int(assignment_id)
    except ValueError:
        return fail_response("Invalid assignmentID", 400)

    current_user_id = get_jwt_identity()
    result, status_code, message = delete_assignment_for_teacher(
        current_user_id,
        assignment_id_int,
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


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


@student_assignment_bp.get("/assignments")
@jwt_required()
def get_student_assignment_list():
    """查询当前学生可见的考试任务列表。"""
    current_user_id = get_jwt_identity()
    debug_bypass_time = (
        str(request.args.get("debug_bypass_time") or "").strip().lower() == "true"
    )
    return success_response(
        get_assignments_by_student(current_user_id, debug_bypass_time=debug_bypass_time)
    )


@student_assignment_bp.get("/exam/<int:assignment_id>")
@jwt_required()
def get_student_assignment_detail(assignment_id: int):
    """查询当前学生指定考试任务的详情。"""
    current_user_id = get_jwt_identity()
    result, status_code, message = get_assignment_exam_detail_for_student(
        current_user_id,
        assignment_id,
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


def _save_student_assignment_answers():
    current_user_id = get_jwt_identity()
    payload = request.get_json(silent=True) or {}
    result, status_code, message = save_assignment_answers_for_student(
        current_user_id,
        payload,
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


@student_assignment_bp.post("/exam/save")
@jwt_required()
def save_student_assignment_answers():
    """保存当前学生的考试作答。"""
    return _save_student_assignment_answers()


@student_assignment_bp.post("/exam/submit")
@jwt_required()
def submit_student_assignment_answers():
    """兼容旧调用路径，内部仍按保存作答处理。"""
    return _save_student_assignment_answers()


@student_assignment_bp.get("/answer-assets/<path:file_name>")
def get_student_answer_asset(file_name: str):
    upload_dir = current_app.config.get("STUDENT_ANSWER_IMAGE_UPLOAD_DIR")
    if not upload_dir:
        return fail_response("Asset directory is not configured", 500)
    return send_from_directory(upload_dir, file_name)
