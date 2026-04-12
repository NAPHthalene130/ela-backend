from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from repositories.auth_repository import get_user_by_id
from services.practice_service import (
    add_question_into_student_practice_set,
    create_student_practice_set,
    delete_student_practice_set,
    get_practice_courses,
    get_practice_question_detail,
    get_practice_question_pool,
    get_practice_sets,
    get_student_practice_session,
    remove_question_from_student_practice_set,
    recommend_practice_questions,
)

practice_bp = Blueprint("practice", __name__)


def _require_student():
    current_user_id = get_jwt_identity()
    user = get_user_by_id(current_user_id)
    if not user:
        return None, fail_response("User not found", 404)
    if (user.type or "").lower() != "student":
        return None, fail_response("Forbidden", 403)
    return current_user_id, None


@practice_bp.get("/courses")
@jwt_required()
def get_course_list():
    _, error_response = _require_student()
    if error_response:
        return error_response
    return success_response(get_practice_courses())


@practice_bp.get("/pool")
@jwt_required()
def get_question_pool():
    _, error_response = _require_student()
    if error_response:
        return error_response
    course = request.args.get("course", "").strip()
    question_type = request.args.get("type", "").strip()
    if not course:
        return fail_response("Missing course", 400)
    if not question_type:
        return fail_response("Missing type", 400)
    return success_response(get_practice_question_pool(course, question_type))


@practice_bp.get("/detail")
@jwt_required()
def get_question_detail():
    _, error_response = _require_student()
    if error_response:
        return error_response
    question_id = request.args.get("questionID")
    if question_id is None:
        return fail_response("Missing questionID", 400)
    try:
        question_id_int = int(question_id)
    except (TypeError, ValueError):
        return fail_response("Invalid questionID", 400)
    question_detail = get_practice_question_detail(question_id_int)
    if not question_detail:
        return fail_response("Question not found", 404)
    return success_response(question_detail)


@practice_bp.post("/recommend")
@jwt_required()
def get_recommended_questions():
    _, error_response = _require_student()
    if error_response:
        return error_response
    payload = request.get_json(silent=True) or {}
    result, status_code, message = recommend_practice_questions(
        course=payload.get("course", ""),
        question_type=payload.get("type", ""),
        requirement=payload.get("requirement", ""),
        limit=payload.get("limit", 10),
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


@practice_bp.get("/sets")
@jwt_required()
def list_practice_sets():
    student_id, error_response = _require_student()
    if error_response:
        return error_response
    return success_response(get_practice_sets(student_id))


@practice_bp.post("/sets/create")
@jwt_required()
def create_practice_set_route():
    student_id, error_response = _require_student()
    if error_response:
        return error_response
    payload = request.get_json(silent=True) or {}
    result, status_code, message = create_student_practice_set(student_id, payload.get("name", ""))
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


@practice_bp.post("/sets/delete")
@jwt_required()
def delete_practice_set_route():
    student_id, error_response = _require_student()
    if error_response:
        return error_response
    payload = request.get_json(silent=True) or {}
    try:
        set_id = int(payload.get("setID"))
    except (TypeError, ValueError):
        return fail_response("Invalid setID", 400)
    success, status_code, message = delete_student_practice_set(student_id, set_id)
    if not success:
        return fail_response(message, status_code)
    return success_response({"setID": set_id}, message, status_code)


@practice_bp.post("/sets/add-question")
@jwt_required()
def add_question_to_set_route():
    student_id, error_response = _require_student()
    if error_response:
        return error_response
    payload = request.get_json(silent=True) or {}
    try:
        set_id = int(payload.get("setID"))
        question_id = int(payload.get("questionID"))
    except (TypeError, ValueError):
        return fail_response("Invalid setID or questionID", 400)
    result, status_code, message = add_question_into_student_practice_set(
        student_id=student_id,
        set_id=set_id,
        question_id=question_id,
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


@practice_bp.post("/sets/remove-question")
@jwt_required()
def remove_question_from_set_route():
    student_id, error_response = _require_student()
    if error_response:
        return error_response
    payload = request.get_json(silent=True) or {}
    try:
        set_id = int(payload.get("setID"))
        question_id = int(payload.get("questionID"))
    except (TypeError, ValueError):
        return fail_response("Invalid setID or questionID", 400)
    result, status_code, message = remove_question_from_student_practice_set(
        student_id=student_id,
        set_id=set_id,
        question_id=question_id,
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


@practice_bp.get("/sets/session")
@jwt_required()
def get_practice_session():
    student_id, error_response = _require_student()
    if error_response:
        return error_response
    set_id = request.args.get("setID")
    try:
        set_id_int = int(set_id)
    except (TypeError, ValueError):
        return fail_response("Invalid setID", 400)
    result, status_code, message = get_student_practice_session(student_id, set_id_int)
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)
