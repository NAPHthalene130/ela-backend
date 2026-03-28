import base64
import os
import uuid

from flask import current_app

from repositories.questions_set_repository import (
    add_question_to_set,
    add_choice_question,
    create_question_set,
    add_custom_question,
    add_fill_question,
    add_subjective_question,
    delete_question_set,
    get_choice_question_by_id,
    get_custom_question_by_id,
    get_fill_question_by_id,
    get_ids_by_course_and_type,
    get_question_node_by_id,
    get_question_set_by_id,
    get_question_set_questions_by_set_id,
    get_questions_set_by_teacherID,
    get_subjective_question_by_id,
    is_question_in_set,
    remove_question_from_set,
    update_question_set_name,
)


IMAGE_EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def get_question_sets_by_teacher(teacher_id: str) -> list[dict]:
    question_sets = get_questions_set_by_teacherID(teacher_id)
    return [{"id": item.id, "name": item.name} for item in question_sets]


def _normalize_question_set_name(name: str | None) -> str:
    normalized_name = str(name or "").strip()
    return normalized_name[:1024]


def create_empty_question_set_for_teacher(teacher_id: str, name: str | None = None) -> tuple[dict | None, int, str]:
    set_name = _normalize_question_set_name(name)
    if not set_name:
        return None, 400, "Missing question set name"
    created_set = create_question_set(teacher_id, set_name)
    if not created_set:
        return None, 500, "Failed to create question set"
    return {"id": created_set.id, "name": created_set.name}, 201, "Question set created"


def rename_question_set_for_teacher(teacher_id: str, set_id: int, name: str | None) -> tuple[dict | None, int, str]:
    question_set = get_question_set_by_id(set_id)
    if not question_set:
        return None, 404, "Question set not found"
    if question_set.teacher_id != teacher_id:
        return None, 403, "Forbidden"

    next_name = _normalize_question_set_name(name)
    if not next_name:
        return None, 400, "Missing question set name"

    updated_set = update_question_set_name(set_id, next_name)
    if not updated_set:
        return None, 500, "Failed to rename question set"
    return {"id": updated_set.id, "name": updated_set.name}, 200, "Question set renamed"


def get_question_pool_by_course_and_type(question_type: str, course: str) -> list[dict]:
    question_items = get_ids_by_course_and_type(question_type, course)
    return [{"id": question_id, "brief": brief} for question_id, brief in question_items]


def get_question_detail_by_id(question_id: int) -> dict | None:
    question_node = get_question_node_by_id(question_id)
    if not question_node:
        return None

    question_type = (question_node.type or "").lower()
    base_data = {
        "id": question_id,
        "type": question_type,
        "course": getattr(question_node, "course", "") or "",
        "belongID": getattr(question_node, "belongID", "$PUBLIC$") or "$PUBLIC$",
    }

    if question_type == "choice":
        question = get_choice_question_by_id(question_id)
        if not question:
            return None
        base_data.update(
            {
                "brief": question.brief or "",
                "content": question.content or "",
                "optionA": question.optionA or "",
                "optionB": question.optionB or "",
                "optionC": question.optionC or "",
                "optionD": question.optionD or "",
                "answer": question.answer or "",
            }
        )
        return base_data

    if question_type == "fill":
        question = get_fill_question_by_id(question_id)
        if not question:
            return None
        base_data.update(
            {
                "brief": question.brief or "",
                "content": question.content or "",
                "answer": question.answer or "",
            }
        )
        return base_data

    if question_type == "subjective":
        question = get_subjective_question_by_id(question_id)
        if not question:
            return None
        base_data.update(
            {
                "brief": question.brief or "",
                "content": question.content or "",
                "answer": question.answer or "",
            }
        )
        return base_data

    if question_type == "custom":
        question = get_custom_question_by_id(question_id)
        if not question:
            return None
        base_data.update(
            {
                "brief": question.brief or "",
                "imageURL": question.imageURL or "",
            }
        )
        return base_data

    return None


def _resolve_belong_id(visibility: str, user_id: str) -> str:
    return "$PUBLIC$" if visibility != "private" else user_id


def _build_brief(content: str, fallback: str = "") -> str:
    normalized_content = " ".join((content or "").split())
    if normalized_content:
        return normalized_content[:120]
    normalized_fallback = " ".join((fallback or "").split())
    return normalized_fallback[:120]


def _save_custom_question_image(image_data: str, image_name: str = "") -> tuple[str | None, str | None]:
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

    max_file_size = int(current_app.config.get("MAX_QUESTION_IMAGE_SIZE", 10 * 1024 * 1024))
    if not file_bytes:
        return None, "Empty image data"
    if len(file_bytes) > max_file_size:
        return None, "Image file is too large"

    upload_dir = current_app.config.get("QUESTION_IMAGE_UPLOAD_DIR")
    if not upload_dir:
        return None, "Upload directory is not configured"

    os.makedirs(upload_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(image_name or ""))[0].strip() or "question"
    safe_name = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in base_name
    ).strip("_") or "question"
    file_name = f"{safe_name}_{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(upload_dir, file_name)

    with open(file_path, "wb") as image_file:
        image_file.write(file_bytes)

    return f"/api/question/assets/{file_name}", None


def create_question_for_teacher(teacher_id: str, payload: dict) -> tuple[dict | None, int, str]:
    question_type = str(payload.get("type", "")).strip().lower()
    course = str(payload.get("course", "")).strip()
    visibility = str(payload.get("visibility", "public")).strip().lower()

    if not teacher_id:
        return None, 401, "Unauthorized"
    if not course:
        return None, 400, "Missing course"
    if question_type not in {"choice", "fill", "subjective", "custom"}:
        return None, 400, "Invalid type"

    belong_id = _resolve_belong_id(visibility, teacher_id)
    question_id = None

    if question_type == "choice":
        content = str(payload.get("content", "")).strip()
        option_a = str(payload.get("optionA", "")).strip()
        option_b = str(payload.get("optionB", "")).strip()
        option_c = str(payload.get("optionC", "")).strip()
        option_d = str(payload.get("optionD", "")).strip()
        answer = str(payload.get("answer", "")).strip().upper()
        if not all([content, option_a, option_b, option_c, option_d, answer]):
            return None, 400, "Missing choice question fields"
        if answer not in {"A", "B", "C", "D"}:
            return None, 400, "Invalid choice answer"
        question_id = add_choice_question(
            course=course,
            content=content,
            optionA=option_a,
            optionB=option_b,
            optionC=option_c,
            optionD=option_d,
            belong_id=belong_id,
            answer=answer,
            brief=_build_brief(content),
        )
    elif question_type == "fill":
        content = str(payload.get("content", "")).strip()
        answer = str(payload.get("answer", "")).strip()
        if not content or not answer:
            return None, 400, "Missing fill question fields"
        question_id = add_fill_question(
            course=course,
            content=content,
            belong_id=belong_id,
            answer=answer,
            brief=_build_brief(content),
        )
    elif question_type == "subjective":
        content = str(payload.get("content", "")).strip()
        answer = str(payload.get("answer", "")).strip()
        if not content or not answer:
            return None, 400, "Missing subjective question fields"
        question_id = add_subjective_question(
            course=course,
            content=content,
            belong_id=belong_id,
            answer=answer,
            brief=_build_brief(content),
        )
    else:
        image_data = str(payload.get("imageData", "")).strip()
        image_name = str(payload.get("imageFileName", "")).strip()
        image_url, error_message = _save_custom_question_image(image_data, image_name)
        if error_message:
            return None, 400, error_message
        question_id = add_custom_question(
            course=course,
            imageURL=image_url or "",
            belong_id=belong_id,
            brief=_build_brief(image_name, "自定义题"),
        )

    if not question_id:
        return None, 500, "Failed to create question"

    question_detail = get_question_detail_by_id(question_id)
    if not question_detail:
        return None, 500, "Failed to load created question"
    return question_detail, 201, "Question created"


def add_question_to_set_for_teacher(
    teacher_id: str,
    set_id: int,
    question_id: int,
) -> tuple[dict | None, int, str]:
    target_set = get_question_set_by_id(set_id)
    if not target_set or target_set.teacher_id != teacher_id:
        return None, 403, "Forbidden"

    question_node = get_question_node_by_id(question_id)
    if not question_node:
        return None, 404, "Question not found"

    if is_question_in_set(set_id, question_id):
        return None, 409, "Question already exists in set"

    if not add_question_to_set(set_id, question_id):
        return None, 500, "Failed to add question to set"

    return {"setID": set_id, "questionID": question_id}, 200, "Question added to set"


def remove_question_from_set_for_teacher(
    teacher_id: str,
    set_id: int,
    question_id: int,
) -> tuple[dict | None, int, str]:
    target_set = get_question_set_by_id(set_id)
    if not target_set or target_set.teacher_id != teacher_id:
        return None, 403, "Forbidden"

    if not is_question_in_set(set_id, question_id):
        return None, 404, "Question not found in set"

    if not remove_question_from_set(set_id, question_id):
        return None, 500, "Failed to remove question from set"

    return {"setID": set_id, "questionID": question_id}, 200, "Question removed from set"


def delete_question_set_for_teacher(teacher_id: str, set_id: int) -> tuple[dict | None, int, str]:
    target_set = get_question_set_by_id(set_id)
    if not target_set or target_set.teacher_id != teacher_id:
        return None, 403, "Forbidden"

    if not delete_question_set(set_id):
        return None, 500, "Failed to delete question set"

    return {"setID": set_id}, 200, "Question set deleted"


def get_questions_by_set_for_teacher(teacher_id: str, set_id: int) -> list[dict] | None:
    target_set = get_question_set_by_id(set_id)
    if not target_set or target_set.teacher_id != teacher_id:
        return None

    set_questions = get_question_set_questions_by_set_id(set_id)
    result = []

    for set_question in set_questions:
        question_node = get_question_node_by_id(set_question.question_id)
        if not question_node:
            continue

        question_type = (question_node.type or "").lower()
        question_item = {
            "id": question_node.id,
            "type": question_type,
            "belongID": getattr(question_node, "belongID", "$PUBLIC$") or "$PUBLIC$",
        }

        if question_type == "choice":
            choice_question = get_choice_question_by_id(question_node.id)
            if not choice_question:
                continue
            question_item.update(
                {
                    "content": choice_question.content,
                    "optionA": choice_question.optionA,
                    "optionB": choice_question.optionB,
                    "optionC": choice_question.optionC,
                    "optionD": choice_question.optionD,
                }
            )
        elif question_type == "fill":
            fill_question = get_fill_question_by_id(question_node.id)
            if not fill_question:
                continue
            question_item.update({"content": fill_question.content})
        elif question_type == "subjective":
            subjective_question = get_subjective_question_by_id(question_node.id)
            if not subjective_question:
                continue
            question_item.update({"content": subjective_question.content})
        elif question_type == "custom":
            custom_question = get_custom_question_by_id(question_node.id)
            if not custom_question:
                continue
            question_item.update({"imageURL": custom_question.imageURL})
        else:
            continue

        result.append(question_item)

    return result
