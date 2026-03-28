from core.extensions import db
from sqlalchemy import inspect, text
from types import SimpleNamespace
from database.models import (
    ChoiceQuestionNode,
    CustomQuestionNode,
    FillQuestionNode,
    QuestionNode,
    QuestionSet,
    QuestionSetAssignment,
    QuestionSetQuestion,
    SubjectiveQuestionNode,
)


def add_choice_question(
    course: str,
    content: str,
    optionA: str,
    optionB: str,
    optionC: str,
    optionD: str,
    belong_id: str = "$PUBLIC$",
    answer: str = "",
    brief: str = "",
) -> int | None:
    question_node = QuestionNode(type="choice", course=course, belongID=belong_id)
    choice_question = ChoiceQuestionNode(
        course=course,
        content=content,
        optionA=optionA,
        optionB=optionB,
        optionC=optionC,
        optionD=optionD,
        answer=answer,
        brief=brief,
        belongID=belong_id,
    )
    try:
        db.session.add(question_node)
        db.session.flush()
        choice_question.id = question_node.id
        db.session.add(choice_question)
        db.session.commit()
        return question_node.id
    except Exception:
        db.session.rollback()
        return None


def add_fill_question(
    course: str,
    content: str,
    belong_id: str = "$PUBLIC$",
    answer: str = "",
    brief: str = "",
) -> int | None:
    question_node = QuestionNode(type="fill", course=course, belongID=belong_id)
    fill_question = FillQuestionNode(
        course=course,
        content=content,
        answer=answer,
        brief=brief,
        belongID=belong_id,
    )
    try:
        db.session.add(question_node)
        db.session.flush()
        fill_question.id = question_node.id
        db.session.add(fill_question)
        db.session.commit()
        return question_node.id
    except Exception:
        db.session.rollback()
        return None


def add_subjective_question(
    course: str,
    content: str,
    belong_id: str = "$PUBLIC$",
    answer: str = "",
    brief: str = "",
) -> int | None:
    question_node = QuestionNode(type="subjective", course=course, belongID=belong_id)
    subjective_question = SubjectiveQuestionNode(
        course=course,
        content=content,
        answer=answer,
        brief=brief,
        belongID=belong_id,
    )
    try:
        db.session.add(question_node)
        db.session.flush()
        subjective_question.id = question_node.id
        db.session.add(subjective_question)
        db.session.commit()
        return question_node.id
    except Exception:
        db.session.rollback()
        return None


def add_custom_question(
    course: str,
    imageURL: str,
    belong_id: str = "$PUBLIC$",
    brief: str = "",
) -> int | None:
    question_node = QuestionNode(type="custom", course=course, belongID=belong_id)
    custom_question = CustomQuestionNode(
        course=course,
        imageURL=imageURL,
        brief=brief,
        belongID=belong_id,
    )
    try:
        db.session.add(question_node)
        db.session.flush()
        custom_question.id = question_node.id
        db.session.add(custom_question)
        db.session.commit()
        return question_node.id
    except Exception:
        db.session.rollback()
        return None


def get_ids_by_course_and_type(id, course: str) -> list[tuple[int, str]]:
    type_alias_map = {
        "0": "choice",
        "1": "fill",
        "2": "subjective",
        "3": "custom",
        "choice": "choice",
        "fill": "fill",
        "subjective": "subjective",
        "custom": "custom",
    }
    normalized_type = type_alias_map.get(str(id).strip().lower())
    if not normalized_type or not course:
        return []

    model_map = {
        "choice": ChoiceQuestionNode,
        "fill": FillQuestionNode,
        "subjective": SubjectiveQuestionNode,
        "custom": CustomQuestionNode,
    }
    table_map = {
        "choice": "choiceQuestionTable",
        "fill": "fillQuestionTable",
        "subjective": "subjectiveQuestionTable",
        "custom": "customQuestionTable",
    }

    model_class = model_map[normalized_type]
    table_name = table_map[normalized_type]

    try:
        records = (
            model_class.query.filter_by(course=course)
            .order_by(model_class.id.asc())
            .all()
        )
        return [(item.id, getattr(item, "brief", "") or "") for item in records]
    except Exception:
        pass

    try:
        columns = {column["name"] for column in inspect(db.engine).get_columns(table_name)}
        if "id" not in columns or "course" not in columns:
            return []
        brief_select = '"brief"' if "brief" in columns else "''"
        rows = db.session.execute(
            text(
                f'SELECT "id", {brief_select} AS brief '
                f'FROM "{table_name}" '
                'WHERE "course" = :course '
                'ORDER BY "id" ASC'
            ),
            {"course": course},
        ).all()
        return [(row[0], row[1] or "") for row in rows]
    except Exception:
        return []


def get_questions_set_by_teacherID(teacherID: str) -> list[QuestionSet]:
    try:
        return (
            QuestionSet.query.filter_by(teacher_id=teacherID)
            .order_by(QuestionSet.id.asc())
            .all()
        )
    except Exception:
        return []


def create_question_set(teacher_id: str, name: str) -> QuestionSet | None:
    try:
        question_set = QuestionSet(name=name, teacher_id=teacher_id)
        db.session.add(question_set)
        db.session.commit()
        return question_set
    except Exception:
        db.session.rollback()
        return None


def update_question_set_name(set_id: int, name: str) -> QuestionSet | None:
    try:
        question_set = QuestionSet.query.filter_by(id=set_id).first()
        if not question_set:
            return None
        question_set.name = name
        db.session.commit()
        return question_set
    except Exception:
        db.session.rollback()
        return None


def get_question_set_questions_by_set_id(set_id: int) -> list[QuestionSetQuestion]:
    try:
        return (
            QuestionSetQuestion.query.filter_by(set_id=set_id)
            .order_by(QuestionSetQuestion.order_num.asc(), QuestionSetQuestion.question_id.asc())
            .all()
        )
    except Exception:
        return []


def get_question_set_by_id(set_id: int) -> QuestionSet | None:
    try:
        return QuestionSet.query.filter_by(id=set_id).first()
    except Exception:
        return None


def is_question_in_set(set_id: int, question_id: int) -> bool:
    try:
        return (
            QuestionSetQuestion.query.filter_by(set_id=set_id, question_id=question_id).first()
            is not None
        )
    except Exception:
        return False


def add_question_to_set(set_id: int, question_id: int) -> bool:
    try:
        max_order = (
            db.session.query(db.func.max(QuestionSetQuestion.order_num))
            .filter_by(set_id=set_id)
            .scalar()
        )
        relation = QuestionSetQuestion(
            set_id=set_id,
            question_id=question_id,
            order_num=(max_order or 0) + 1,
        )
        db.session.add(relation)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def remove_question_from_set(set_id: int, question_id: int) -> bool:
    try:
        deleted_count = (
            QuestionSetQuestion.query.filter_by(set_id=set_id, question_id=question_id).delete()
        )
        db.session.commit()
        return deleted_count > 0
    except Exception:
        db.session.rollback()
        return False


def delete_question_set(set_id: int) -> bool:
    try:
        QuestionSetAssignment.query.filter_by(set_id=set_id).delete()
        QuestionSetQuestion.query.filter_by(set_id=set_id).delete()
        deleted_count = QuestionSet.query.filter_by(id=set_id).delete()
        db.session.commit()
        return deleted_count > 0
    except Exception:
        db.session.rollback()
        return False


def get_question_node_by_id(question_id: int) -> QuestionNode | None:
    try:
        question_node = QuestionNode.query.filter_by(id=question_id).first()
        if question_node:
            return question_node
    except Exception:
        pass

    try:
        row = db.session.execute(
            text('SELECT id, type, course, belongID FROM "questionTable" WHERE id = :question_id'),
            {"question_id": question_id},
        ).first()
        if not row:
            return None
        return SimpleNamespace(id=row[0], type=row[1], course=row[2], belongID=row[3])
    except Exception:
        return None


def get_choice_question_by_id(id: int) -> ChoiceQuestionNode | None:
    try:
        return ChoiceQuestionNode.query.filter_by(id=id).first()
    except Exception:
        return None


def get_fill_question_by_id(id: int) -> FillQuestionNode | None:
    try:
        return FillQuestionNode.query.filter_by(id=id).first()
    except Exception:
        return None


def get_custom_question_by_id(id: int) -> CustomQuestionNode | None:
    try:
        return CustomQuestionNode.query.filter_by(id=id).first()
    except Exception:
        return None


def get_subjective_question_by_id(id: int) -> SubjectiveQuestionNode | None:
    try:
        return SubjectiveQuestionNode.query.filter_by(id=id).first()
    except Exception:
        return None
