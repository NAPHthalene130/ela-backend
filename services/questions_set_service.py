from repositories.questions_set_repository import (
    get_choice_question_by_id,
    get_custom_question_by_id,
    get_fill_question_by_id,
    get_question_node_by_id,
    get_question_set_by_id,
    get_question_set_questions_by_set_id,
    get_questions_set_by_teacherID,
    get_subjective_question_by_id,
)


def get_question_sets_by_teacher(teacher_id: str) -> list[dict]:
    question_sets = get_questions_set_by_teacherID(teacher_id)
    return [{"id": item.id, "name": item.name} for item in question_sets]


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
