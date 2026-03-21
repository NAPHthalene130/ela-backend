from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.responses import fail_response, success_response
from services.group_service import get_groups_by_teacher

group_bp = Blueprint("group", __name__)


@group_bp.get("/list")
@jwt_required()
def get_group_list():
    teacher_id = request.args.get("teacherID") or get_jwt_identity()
    current_user_id = get_jwt_identity()
    if teacher_id != current_user_id:
        return fail_response("Forbidden", 403)
    return success_response(get_groups_by_teacher(teacher_id))
