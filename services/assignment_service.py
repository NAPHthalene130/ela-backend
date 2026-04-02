from datetime import datetime, timezone

from repositories.assignment_repository import (
    add_assignment,
    get_assignment_by_id,
    get_assignment_by_teacherID,
    get_student_answers_by_assignment_and_student,
)
from repositories.group_repository import (
    get_group_by_id,
    get_students_from_groups,
    is_group_owned_by_teacher,
)
from repositories.questions_set_repository import (
    get_choice_question_by_id,
    get_custom_question_by_id,
    get_fill_question_by_id,
    get_question_node_by_id,
    get_question_set_by_id,
    get_question_set_questions_by_set_id,
    get_subjective_question_by_id,
)


def _format_datetime(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def get_assignments_by_teacher(teacher_id: str) -> list[dict]:
    """返回前端任务列表所需的基础结构。"""
    assignments = get_assignment_by_teacherID(teacher_id)
    result = []
    for item in assignments:
        target_set = get_question_set_by_id(item.set_id)
        target_group = get_group_by_id(item.group_id)
        result.append(
            {
                "id": item.id,
                "assignmentName": item.assignment_name or f"任务 {item.id}",
                "setID": item.set_id,
                "setName": target_set.name if target_set else "",
                "groupID": item.group_id,
                "groupName": target_group.name if target_group else "",
                "createTeacherID": item.create_teacher_id or "",
                "beginTime": _format_datetime(item.begin_time),
                "endTime": _format_datetime(item.end_time),
            }
        )
    return result


def _build_question_payload(question_id: int) -> dict | None:
    question_node = get_question_node_by_id(question_id)
    if not question_node:
        return None

    question_type = (question_node.type or "").lower()
    question_item = {
        "id": question_node.id,
        "type": question_type,
    }

    if question_type == "choice":
        choice_question = get_choice_question_by_id(question_node.id)
        if not choice_question:
            return None
        question_item.update(
            {
                "content": choice_question.content or "",
                "optionA": choice_question.optionA or "",
                "optionB": choice_question.optionB or "",
                "optionC": choice_question.optionC or "",
                "optionD": choice_question.optionD or "",
                "answer": choice_question.answer or "",
            }
        )
        return question_item

    if question_type == "fill":
        fill_question = get_fill_question_by_id(question_node.id)
        if not fill_question:
            return None
        question_item.update(
            {
                "content": fill_question.content or "",
                "answer": fill_question.answer or "",
            }
        )
        return question_item

    if question_type == "subjective":
        subjective_question = get_subjective_question_by_id(question_node.id)
        if not subjective_question:
            return None
        question_item.update(
            {
                "content": subjective_question.content or "",
                "answer": subjective_question.answer or "",
            }
        )
        return question_item

    if question_type == "custom":
        custom_question = get_custom_question_by_id(question_node.id)
        if not custom_question:
            return None
        question_item.update(
            {
                "imageURL": custom_question.imageURL or "",
            }
        )
        return question_item

    return None


def get_assignment_student_answers_for_teacher(
    teacher_id: str, assignment_id: int, student_id: str
) -> tuple[dict | None, int, str]:
    assignment = get_assignment_by_id(assignment_id)
    if not assignment or assignment.create_teacher_id != teacher_id:
        return None, 403, "Forbidden"

    group_students = set(get_students_from_groups(assignment.group_id))
    if student_id not in group_students:
        return None, 404, "Student not found in group"

    question_set = get_question_set_by_id(assignment.set_id)
    group = get_group_by_id(assignment.group_id)
    answer_items = get_student_answers_by_assignment_and_student(assignment_id, student_id)
    answer_map = {item.questionID: item for item in answer_items}
    questions = []

    for index, set_question in enumerate(
        get_question_set_questions_by_set_id(assignment.set_id), start=1
    ):
        question_payload = _build_question_payload(set_question.question_id)
        if not question_payload:
            continue

        student_answer = answer_map.get(set_question.question_id)
        question_payload.update(
            {
                "orderNum": index,
                "studentAnswer": {
                    "content": student_answer.content if student_answer else "",
                    "imgURL": student_answer.imgURL if student_answer else "",
                },
            }
        )
        questions.append(question_payload)

    return (
        {
            "assignmentID": assignment.id,
            "assignmentName": assignment.assignment_name or f"任务 {assignment.id}",
            "studentID": student_id,
            "groupID": assignment.group_id,
            "groupName": group.name if group else "",
            "setID": assignment.set_id,
            "setName": question_set.name if question_set else "",
            "questions": questions,
        },
        200,
        "success",
    )


def _parse_iso_datetime(value) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("Invalid datetime")

    normalized_value = value.strip()
    if not normalized_value:
        return None

    parsed_datetime = datetime.fromisoformat(
        normalized_value.replace("Z", "+00:00")
    )
    if parsed_datetime.tzinfo is not None:
        return parsed_datetime.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed_datetime


def create_assignment_for_teacher(
    teacher_id: str, payload: dict
) -> tuple[dict | None, int, str]:
    assignment_name = (payload.get("assignmentName") or "").strip()
    if not assignment_name:
        return None, 400, "Missing assignmentName"

    set_id = payload.get("setID")
    group_id = payload.get("groupID")
    if set_id is None or group_id is None:
        return None, 400, "Missing setID or groupID"

    try:
        set_id_int = int(set_id)
        group_id_int = int(group_id)
        begin_time = _parse_iso_datetime(payload.get("beginTime"))
        end_time = _parse_iso_datetime(payload.get("endTime"))
    except (TypeError, ValueError):
        return None, 400, "Invalid parameters"

    if begin_time and end_time and end_time <= begin_time:
        return None, 400, "endTime must be later than beginTime"

    target_set = get_question_set_by_id(set_id_int)
    if not target_set or target_set.teacher_id != teacher_id:
        return None, 403, "Forbidden"

    if not is_group_owned_by_teacher(group_id_int, teacher_id):
        return None, 403, "Forbidden"

    target_group = get_group_by_id(group_id_int)

    created_assignment = add_assignment(
        set_id=set_id_int,
        group_id=group_id_int,
        teacher_id=teacher_id,
        assignment_name=assignment_name,
        begin_time=begin_time,
        end_time=end_time,
    )
    if not created_assignment:
        return None, 400, "Failed to create assignment"

    return (
        {
            "id": created_assignment.id,
            "assignmentName": created_assignment.assignment_name,
            "setID": created_assignment.set_id,
            "setName": target_set.name,
            "groupID": created_assignment.group_id,
            "groupName": target_group.name if target_group else "",
            "createTeacherID": created_assignment.create_teacher_id,
            "beginTime": _format_datetime(created_assignment.begin_time),
            "endTime": _format_datetime(created_assignment.end_time),
        },
        201,
        "Assignment created",
    )
