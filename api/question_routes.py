from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from services.questions_set_service import (
    get_question_sets_by_teacher,
    get_questions_by_set_for_teacher,
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
