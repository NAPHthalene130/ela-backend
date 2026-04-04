import base64
import os
import uuid
from datetime import datetime, timezone

from flask import current_app

from repositories.assignment_repository import (
    add_assignment,
    delete_assignment_by_teacher,
    get_assignment_by_id,
    get_assignments_by_group_ids,
    get_assignment_by_teacherID,
    get_student_answers_by_assignment_and_student,
    save_student_answers,
)
from repositories.group_repository import (
    get_group_by_id,
    get_group_ids_by_student,
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

IMAGE_EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

STUDENT_ANSWER_ASSET_PREFIX = "/api/student/answer-assets/"


def _format_datetime(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _is_answer_filled(content: str = "", image_url: str = "") -> bool:
    return bool(str(content or "").strip() or str(image_url or "").strip())


def _save_student_answer_image(
    image_data: str, image_name: str = ""
) -> tuple[str | None, str | None]:
    if not image_data or not image_data.startswith("data:"):
        return None, "Missing image data"

    try:
        header, encoded_payload = image_data.split(",", 1)
    except ValueError:
        return None, "Invalid image data"

    mime_type = header[5:].split(";", 1)[0].lower()
    extension = IMAGE_EXTENSION_MAP.get(mime_type)
    if not extension:
        return None, "Unsupported image type"

    try:
        file_bytes = base64.b64decode(encoded_payload)
    except Exception:
        return None, "Invalid image data"

    max_file_size = int(
        current_app.config.get("MAX_STUDENT_ANSWER_IMAGE_SIZE", 10 * 1024 * 1024)
    )
    if not file_bytes:
        return None, "Empty image data"
    if len(file_bytes) > max_file_size:
        return None, "Image file is too large"

    upload_dir = current_app.config.get("STUDENT_ANSWER_IMAGE_UPLOAD_DIR")
    if not upload_dir:
        return None, "Upload directory is not configured"

    os.makedirs(upload_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(image_name or ""))[0].strip() or "answer"
    safe_name = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in base_name
    ).strip("_") or "answer"
    file_name = f"{safe_name}_{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(upload_dir, file_name)

    with open(file_path, "wb") as image_file:
        image_file.write(file_bytes)

    return f"{STUDENT_ANSWER_ASSET_PREFIX}{file_name}", None


def _delete_student_answer_asset(image_url: str) -> None:
    normalized_url = str(image_url or "").strip()
    if not normalized_url.startswith(STUDENT_ANSWER_ASSET_PREFIX):
        return

    upload_dir = current_app.config.get("STUDENT_ANSWER_IMAGE_UPLOAD_DIR")
    if not upload_dir:
        return

    file_name = normalized_url.removeprefix(STUDENT_ANSWER_ASSET_PREFIX).strip()
    if not file_name:
        return

    file_path = os.path.join(upload_dir, os.path.basename(file_name))
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            return


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


def _get_assignment_status(assignment, current_time: datetime) -> str:
    begin_time = assignment.begin_time
    end_time = assignment.end_time
    if begin_time and current_time < begin_time:
        return "not_started"
    if end_time and current_time > end_time:
        return "ended"
    return "in_progress"


def get_assignments_by_student(
    student_id: str, debug_bypass_time: bool = False
) -> dict:
    """返回学生可见的考试任务列表。"""
    group_ids = get_group_ids_by_student(student_id)
    assignments = get_assignments_by_group_ids(group_ids)
    current_time = datetime.utcnow()
    items = []

    for assignment in assignments:
        group = get_group_by_id(assignment.group_id)
        status = (
            "in_progress"
            if debug_bypass_time
            else _get_assignment_status(assignment, current_time)
        )
        items.append(
            {
                "assignmentID": assignment.id,
                "assignmentName": assignment.assignment_name or f"任务 {assignment.id}",
                "groupID": assignment.group_id,
                "groupName": group.name if group else "",
                "beginTime": _format_datetime(assignment.begin_time),
                "endTime": _format_datetime(assignment.end_time),
                "status": status,
            }
        )

    return {"items": items}


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


def _build_student_question_payload(question_id: int) -> dict | None:
    question_node = get_question_node_by_id(question_id)
    if not question_node:
        return None

    question_type = (question_node.type or "").lower()
    question_item = {
        "questionID": question_node.id,
        "type": question_type,
    }

    if question_type == "choice":
        choice_question = get_choice_question_by_id(question_node.id)
        if not choice_question:
            return None
        question_item.update(
            {
                "brief": choice_question.brief or "",
                "content": choice_question.content or "",
                "options": [
                    {"key": "A", "text": choice_question.optionA or ""},
                    {"key": "B", "text": choice_question.optionB or ""},
                    {"key": "C", "text": choice_question.optionC or ""},
                    {"key": "D", "text": choice_question.optionD or ""},
                ],
            }
        )
        return question_item

    if question_type == "fill":
        fill_question = get_fill_question_by_id(question_node.id)
        if not fill_question:
            return None
        question_item.update(
            {
                "brief": fill_question.brief or "",
                "content": fill_question.content or "",
            }
        )
        return question_item

    if question_type == "subjective":
        subjective_question = get_subjective_question_by_id(question_node.id)
        if not subjective_question:
            return None
        question_item.update(
            {
                "brief": subjective_question.brief or "",
                "content": subjective_question.content or "",
            }
        )
        return question_item

    if question_type == "custom":
        custom_question = get_custom_question_by_id(question_node.id)
        if not custom_question:
            return None
        question_item.update(
            {
                "brief": custom_question.brief or "",
                "imageURL": custom_question.imageURL or "",
            }
        )
        return question_item

    return None


def get_assignment_exam_detail_for_student(
    student_id: str, assignment_id: int
) -> tuple[dict | None, int, str]:
    """返回学生考试详情页所需的任务与题目数据。"""
    assignment = get_assignment_by_id(assignment_id)
    if not assignment:
        return None, 404, "任务不存在"

    if student_id not in set(get_students_from_groups(assignment.group_id)):
        return None, 403, "无权访问该考试任务"

    current_status = _get_assignment_status(assignment, datetime.utcnow())
    if current_status == "not_started":
        return None, 403, "考试尚未开始"
    if current_status == "ended":
        return None, 403, "考试已结束"

    group = get_group_by_id(assignment.group_id)
    answer_items = get_student_answers_by_assignment_and_student(assignment_id, student_id)
    answer_map = {item.questionID: item for item in answer_items}
    question_list = []

    for set_question in get_question_set_questions_by_set_id(assignment.set_id):
        question_payload = _build_student_question_payload(set_question.question_id)
        if not question_payload:
            continue

        student_answer = answer_map.get(set_question.question_id)
        question_payload["studentAnswer"] = {
            "content": student_answer.content if student_answer else "",
            "imgURL": student_answer.imgURL if student_answer else "",
        }
        question_list.append(question_payload)

    return (
        {
            "assignment": {
                "assignmentID": assignment.id,
                "assignmentName": assignment.assignment_name or f"任务 {assignment.id}",
                "groupID": assignment.group_id,
                "groupName": group.name if group else "",
                "beginTime": _format_datetime(assignment.begin_time),
                "endTime": _format_datetime(assignment.end_time),
                "status": current_status,
            },
            "questions": question_list,
        },
        200,
        "success",
    )


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


def save_assignment_answers_for_student(
    student_id: str, payload: dict
) -> tuple[dict | None, int, str]:
    """保存学生在考试中的答案。"""
    assignment_id = payload.get("assignmentID")
    mode = str(payload.get("mode") or "save").strip().lower()
    answers = payload.get("answers")

    if assignment_id is None:
        return None, 400, "缺少 assignmentID"
    if not isinstance(answers, list):
        return None, 400, "缺少 answers"
    if mode not in {"save", "submit"}:
        return None, 400, "无效的 mode 参数"

    try:
        assignment_id_int = int(assignment_id)
    except (TypeError, ValueError):
        return None, 400, "assignmentID 格式错误"

    assignment = get_assignment_by_id(assignment_id_int)
    if not assignment:
        return None, 404, "任务不存在"

    if student_id not in set(get_students_from_groups(assignment.group_id)):
        return None, 403, "无权提交该考试任务"

    valid_question_ids = {
        set_question.question_id
        for set_question in get_question_set_questions_by_set_id(assignment.set_id)
    }
    if not valid_question_ids:
        return None, 400, "当前任务暂无题目"

    existing_answers = {
        item.questionID: item
        for item in get_student_answers_by_assignment_and_student(assignment_id_int, student_id)
    }
    normalized_answers = []
    for answer_item in answers:
        if not isinstance(answer_item, dict):
            return None, 400, "answers 数据格式错误"
        try:
            question_id = int(answer_item.get("questionID"))
        except (TypeError, ValueError):
            return None, 400, "questionID 格式错误"
        if question_id not in valid_question_ids:
            return None, 400, "提交了不属于当前任务的题目"

        content = str(answer_item.get("content") or "")
        image_data = str(answer_item.get("imageData") or "").strip()
        image_name = str(answer_item.get("imageFileName") or "").strip()
        image_url = str(answer_item.get("imgURL") or "").strip()
        remove_image = bool(answer_item.get("removeImage"))
        previous_answer = existing_answers.get(question_id)
        previous_image_url = previous_answer.imgURL if previous_answer else ""

        if image_data:
            saved_image_url, error_message = _save_student_answer_image(image_data, image_name)
            if error_message:
                return None, 400, error_message
            image_url = saved_image_url or ""
            if previous_image_url and previous_image_url != image_url:
                _delete_student_answer_asset(previous_image_url)
        elif remove_image:
            image_url = ""
            if previous_image_url:
                _delete_student_answer_asset(previous_image_url)
        elif not image_url and previous_image_url:
            image_url = previous_image_url
        elif image_url and previous_image_url and previous_image_url != image_url:
            _delete_student_answer_asset(previous_image_url)

        normalized_answers.append(
            {
                "questionID": question_id,
                "content": content,
                "imgURL": image_url,
            }
        )

    saved_answers = save_student_answers(assignment_id_int, student_id, normalized_answers)
    if saved_answers is None:
        return None, 500, "保存作答失败"

    serialized_answers = [
        {
            "questionID": item.questionID,
            "content": item.content or "",
            "imgURL": item.imgURL or "",
        }
        for item in saved_answers
    ]
    answered_question_ids = [
        item["questionID"]
        for item in serialized_answers
        if _is_answer_filled(item.get("content"), item.get("imgURL"))
    ]

    return (
        {
            "assignmentID": assignment_id_int,
            "studentID": student_id,
            "savedCount": len(normalized_answers),
            "mode": "save" if mode == "submit" else mode,
            "savedAt": _format_datetime(datetime.utcnow()),
            "answeredCount": len(answered_question_ids),
            "answeredQuestionIDs": answered_question_ids,
            "answers": serialized_answers,
        },
        200,
        "作答已保存",
    )


def delete_assignment_for_teacher(
    teacher_id: str, assignment_id: int
) -> tuple[dict | None, int, str]:
    """删除教师创建的任务。"""
    assignment = get_assignment_by_id(assignment_id)
    if not assignment:
        return None, 404, "任务不存在"

    if assignment.create_teacher_id != teacher_id:
        return None, 403, "Forbidden"

    deleted = delete_assignment_by_teacher(assignment_id, teacher_id)
    if not deleted:
        return None, 500, "删除任务失败"

    return (
        {
            "id": assignment_id,
        },
        200,
        "任务删除成功",
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
