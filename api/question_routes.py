from flask import Blueprint, current_app, request, send_from_directory
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from services.questions_set_service import (
    add_question_to_set_for_teacher,
    create_empty_question_set_for_teacher,
    create_question_for_teacher,
    delete_question_set_for_teacher,
    get_question_detail_by_id,
    get_question_pool_by_course_and_type,
    get_question_sets_by_teacher,
    get_questions_by_set_for_teacher,
    remove_question_from_set_for_teacher,
    rename_question_set_for_teacher,
)

question_bp = Blueprint("question", __name__)


@question_bp.get("/set/list")
@jwt_required()
def get_question_set_list():
    teacher_id = request.args.get("teacherID") or get_jwt_identity()
    current_user_id = get_jwt_identity()
    if teacher_id != current_user_id:
        return fail_response("Forbidden", 403)
    return success_response(get_question_sets_by_teacher(teacher_id))


@question_bp.post("/set/create")
@jwt_required()
def create_question_set():
    payload = request.get_json(silent=True) or {}
    current_user_id = get_jwt_identity()
    created_set, status_code, message = create_empty_question_set_for_teacher(
        current_user_id,
        payload.get("name"),
    )
    if not created_set:
        return fail_response(message, status_code)
    return success_response(created_set, message, status_code)


@question_bp.get("/set/questions")
@jwt_required()
def get_question_set_questions():
    set_id = request.args.get("setID")
    if not set_id:
        return fail_response("Missing setID", 400)

    try:
        set_id_int = int(set_id)
    except ValueError:
        return fail_response("Invalid setID", 400)

    teacher_id = get_jwt_identity()
    questions = get_questions_by_set_for_teacher(teacher_id, set_id_int)
    if questions is None:
        return fail_response("Forbidden", 403)
    return success_response(questions)


@question_bp.get("/pool")
@jwt_required()
def get_question_pool():
    course = request.args.get("course", "").strip()
    question_type = request.args.get("type", "").strip()
    if not course:
        return fail_response("Missing course", 400)
    if not question_type:
        return fail_response("Missing type", 400)
    return success_response(get_question_pool_by_course_and_type(question_type, course))


@question_bp.get("/detail")
@jwt_required()
def get_question_detail():
    question_id = request.args.get("questionID")
    if not question_id:
        return fail_response("Missing questionID", 400)

    try:
        question_id_int = int(question_id)
    except ValueError:
        return fail_response("Invalid questionID", 400)

    question_detail = get_question_detail_by_id(question_id_int)
    if not question_detail:
        return fail_response("Question not found", 404)
    return success_response(question_detail)


@question_bp.post("/create")
@jwt_required()
def create_question():
    payload = request.get_json(silent=True) or {}
    current_user_id = get_jwt_identity()
    created_question, status_code, message = create_question_for_teacher(current_user_id, payload)
    if not created_question:
        return fail_response(message, status_code)
    return success_response(created_question, message, status_code)


@question_bp.post("/set/add-question")
@jwt_required()
def add_question_into_set():
    payload = request.get_json(silent=True) or {}
    set_id = payload.get("setID")
    question_id = payload.get("questionID")

    if set_id is None or question_id is None:
        return fail_response("Missing setID or questionID", 400)

    try:
        set_id_int = int(set_id)
        question_id_int = int(question_id)
    except (TypeError, ValueError):
        return fail_response("Invalid setID or questionID", 400)

    current_user_id = get_jwt_identity()
    result, status_code, message = add_question_to_set_for_teacher(
        current_user_id,
        set_id_int,
        question_id_int,
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


@question_bp.post("/set/remove-question")
@jwt_required()
def remove_question_from_set():
    payload = request.get_json(silent=True) or {}
    set_id = payload.get("setID")
    question_id = payload.get("questionID")

    if set_id is None or question_id is None:
        return fail_response("Missing setID or questionID", 400)

    try:
        set_id_int = int(set_id)
        question_id_int = int(question_id)
    except (TypeError, ValueError):
        return fail_response("Invalid setID or questionID", 400)

    current_user_id = get_jwt_identity()
    result, status_code, message = remove_question_from_set_for_teacher(
        current_user_id,
        set_id_int,
        question_id_int,
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


@question_bp.post("/set/delete")
@jwt_required()
def delete_question_set():
    payload = request.get_json(silent=True) or {}
    set_id = payload.get("setID")

    if set_id is None:
        return fail_response("Missing setID", 400)

    try:
        set_id_int = int(set_id)
    except (TypeError, ValueError):
        return fail_response("Invalid setID", 400)

    current_user_id = get_jwt_identity()
    result, status_code, message = delete_question_set_for_teacher(current_user_id, set_id_int)
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


@question_bp.post("/set/rename")
@jwt_required()
def rename_question_set():
    payload = request.get_json(silent=True) or {}
    set_id = payload.get("setID")
    if set_id is None:
        return fail_response("Missing setID", 400)

    try:
        set_id_int = int(set_id)
    except (TypeError, ValueError):
        return fail_response("Invalid setID", 400)

    current_user_id = get_jwt_identity()
    result, status_code, message = rename_question_set_for_teacher(
        current_user_id,
        set_id_int,
        payload.get("name"),
    )
    if not result:
        return fail_response(message, status_code)
    return success_response(result, message, status_code)


@question_bp.get("/assets/<path:file_name>")
def get_question_asset(file_name: str):
    upload_dir = current_app.config.get("QUESTION_IMAGE_UPLOAD_DIR")
    if not upload_dir:
        return fail_response("Asset directory is not configured", 500)
    return send_from_directory(upload_dir, file_name)
