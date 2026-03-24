from repositories.questions_set_repository import (
    get_choice_question_by_id,
    get_custom_question_by_id,
    get_fill_question_by_id,
    get_ids_by_course_and_type,
    get_question_node_by_id,
    get_question_set_by_id,
    get_question_set_questions_by_set_id,
    get_questions_set_by_teacherID,
    get_subjective_question_by_id,
)


def get_question_sets_by_teacher(teacher_id: str) -> list[dict]:
    question_sets = get_questions_set_by_teacherID(teacher_id)
    return [{"id": item.id, "name": item.name} for item in question_sets]


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
