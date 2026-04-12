from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from repositories.auth_repository import get_user_by_id
from repositories.student_exam_repository import (
    get_assignments_for_student,
    get_exam_paper_details,
    is_student_in_assignment_group,
    upsert_student_answers,
)

student_bp = Blueprint("student", __name__)


def _format_datetime(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return str(value)


def _build_assignment_status(begin_time, end_time, force_in_progress: bool) -> str:
    if force_in_progress:
        return "in_progress"

    now = datetime.now()
    if begin_time and end_time:
        if now < begin_time:
            return "not_started"
        if now > end_time:
            return "ended"
        return "in_progress"
    if begin_time and not end_time:
        return "not_started" if now < begin_time else "in_progress"
    if not begin_time and end_time:
        return "in_progress" if now <= end_time else "ended"
    return "in_progress"


@student_bp.get("/assignments")
@jwt_required()
def get_student_assignments():
    current_user_id = get_jwt_identity()
    user = get_user_by_id(current_user_id)
    if not user:
        return fail_response("User not found", 404)
    if (user.type or "").lower() != "student":
        return fail_response("Forbidden", 403)

    bypass_time = str(request.args.get("debug_bypass_time", "false")).strip().lower() == "true"
    assignments = get_assignments_for_student(current_user_id)
    items = []
    for item in assignments:
        begin_time = item.get("beginTime")
        end_time = item.get("endTime")
        items.append(
            {
                "assignmentID": item.get("assignmentID"),
                "assignmentName": item.get("assignmentName", ""),
                "setID": item.get("setID"),
                "setName": item.get("setName", ""),
                "groupID": item.get("groupID"),
                "groupName": item.get("groupName", ""),
                "beginTime": _format_datetime(begin_time),
                "endTime": _format_datetime(end_time),
                "status": _build_assignment_status(begin_time, end_time, bypass_time),
            }
        )
    return success_response(
        {
            "debugBypassTime": bypass_time,
            "items": items,
        },
        "Assignments fetched",
    )


@student_bp.get("/exam/<int:assignment_id>")
@jwt_required()
def get_student_exam_paper(assignment_id: int):
    current_user_id = get_jwt_identity()
    user = get_user_by_id(current_user_id)
    if not user:
        return fail_response("User not found", 404)
    if (user.type or "").lower() != "student":
        return fail_response("Forbidden", 403)

    exam_detail = get_exam_paper_details(assignment_id)
    if not exam_detail:
        return fail_response("Assignment not found", 404)
    if not is_student_in_assignment_group(current_user_id, assignment_id):
        return fail_response("Forbidden", 403)

    assignment_payload = exam_detail.get("assignment", {})
    assignment_payload["beginTime"] = _format_datetime(assignment_payload.get("beginTime"))
    assignment_payload["endTime"] = _format_datetime(assignment_payload.get("endTime"))
    exam_detail["assignment"] = assignment_payload
    return success_response(exam_detail, "Exam detail fetched")


@student_bp.post("/exam/submit")
@jwt_required()
def submit_student_exam_answers():
    current_user_id = get_jwt_identity()
    user = get_user_by_id(current_user_id)
    if not user:
        return fail_response("User not found", 404)
    if (user.type or "").lower() != "student":
        return fail_response("Forbidden", 403)

    payload = request.get_json(silent=True) or {}
    assignment_id = payload.get("assignmentID")
    mode = str(payload.get("mode", "")).strip().lower()
    answers = payload.get("answers")

    if assignment_id is None:
        return fail_response("Missing assignmentID", 400)
    if mode not in {"save", "submit"}:
        return fail_response("Invalid mode", 400)
    if not isinstance(answers, list):
        return fail_response("Invalid answers", 400)

    try:
        assignment_id_int = int(assignment_id)
    except (TypeError, ValueError):
        return fail_response("Invalid assignmentID", 400)

    exam_detail = get_exam_paper_details(assignment_id_int)
    if not exam_detail:
        return fail_response("Assignment not found", 404)
    if not is_student_in_assignment_group(current_user_id, assignment_id_int):
        return fail_response("Forbidden", 403)

    result = upsert_student_answers(current_user_id, assignment_id_int, answers)
    if result is None:
        return fail_response("Failed to save answers", 500)

    return success_response(
        {
            "assignmentID": assignment_id_int,
            "mode": mode,
            "savedCount": result.get("savedCount", 0),
            "ignoredQuestionIDs": result.get("ignoredQuestionIDs", []),
        },
        "Answers saved" if mode == "save" else "Answers submitted",
    )
