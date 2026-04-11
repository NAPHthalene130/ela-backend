from core.extensions import db
from database.models import (
    ChoiceQuestionNode,
    CustomQuestionNode,
    FillQuestionNode,
    QuestionNode,
    QuestionSet,
    QuestionSetQuestion,
    SubjectiveQuestionNode,
)

PUBLIC_BELONG_ID = "$PUBLIC$"

QUESTION_TYPE_MODEL_MAP = {
    "choice": ChoiceQuestionNode,
    "fill": FillQuestionNode,
    "subjective": SubjectiveQuestionNode,
    "custom": CustomQuestionNode,
}

QUESTION_TYPE_ALIAS_MAP = {
    "0": "choice",
    "1": "fill",
    "2": "subjective",
    "3": "custom",
    "choice": "choice",
    "fill": "fill",
    "subjective": "subjective",
    "custom": "custom",
}


def normalize_question_type(question_type: str) -> str:
    return QUESTION_TYPE_ALIAS_MAP.get(str(question_type or "").strip().lower(), "")


def get_public_course_list() -> list[str]:
    try:
        rows = (
            db.session.query(QuestionNode.course)
            .filter(
                QuestionNode.belongID == PUBLIC_BELONG_ID,
                QuestionNode.course.isnot(None),
                QuestionNode.course != "",
            )
            .distinct()
            .order_by(QuestionNode.course.asc())
            .all()
        )
        return [row[0] for row in rows if row and row[0]]
    except Exception:
        return []


def get_public_question_node_by_id(question_id: int) -> QuestionNode | None:
    try:
        return QuestionNode.query.filter_by(id=question_id, belongID=PUBLIC_BELONG_ID).first()
    except Exception:
        return None


def get_public_choice_question_by_id(question_id: int) -> ChoiceQuestionNode | None:
    try:
        return ChoiceQuestionNode.query.filter_by(id=question_id, belongID=PUBLIC_BELONG_ID).first()
    except Exception:
        return None


def get_public_fill_question_by_id(question_id: int) -> FillQuestionNode | None:
    try:
        return FillQuestionNode.query.filter_by(id=question_id, belongID=PUBLIC_BELONG_ID).first()
    except Exception:
        return None


def get_public_subjective_question_by_id(question_id: int) -> SubjectiveQuestionNode | None:
    try:
        return SubjectiveQuestionNode.query.filter_by(id=question_id, belongID=PUBLIC_BELONG_ID).first()
    except Exception:
        return None


def get_public_custom_question_by_id(question_id: int) -> CustomQuestionNode | None:
    try:
        return CustomQuestionNode.query.filter_by(id=question_id, belongID=PUBLIC_BELONG_ID).first()
    except Exception:
        return None


def get_public_question_pool_by_course_and_type(question_type: str, course: str) -> list[tuple[int, str]]:
    normalized_type = normalize_question_type(question_type)
    normalized_course = str(course or "").strip()
    model = QUESTION_TYPE_MODEL_MAP.get(normalized_type)
    if not model or not normalized_course:
        return []
    try:
        rows = (
            db.session.query(model.id, model.brief)
            .join(QuestionNode, QuestionNode.id == model.id)
            .filter(
                QuestionNode.type == normalized_type,
                QuestionNode.course == normalized_course,
                QuestionNode.belongID == PUBLIC_BELONG_ID,
            )
            .order_by(model.id.asc())
            .all()
        )
        return [(int(item_id), brief or "") for item_id, brief in rows]
    except Exception:
        return []


def get_public_question_search_candidates(question_type: str, course: str) -> list[dict]:
    normalized_type = normalize_question_type(question_type)
    normalized_course = str(course or "").strip()
    if not normalized_type or not normalized_course:
        return []
    try:
        if normalized_type == "choice":
            rows = (
                db.session.query(ChoiceQuestionNode.id, ChoiceQuestionNode.brief, ChoiceQuestionNode.content)
                .join(QuestionNode, QuestionNode.id == ChoiceQuestionNode.id)
                .filter(
                    QuestionNode.type == normalized_type,
                    QuestionNode.course == normalized_course,
                    QuestionNode.belongID == PUBLIC_BELONG_ID,
                )
                .order_by(ChoiceQuestionNode.id.asc())
                .all()
            )
        elif normalized_type == "fill":
            rows = (
                db.session.query(FillQuestionNode.id, FillQuestionNode.brief, FillQuestionNode.content)
                .join(QuestionNode, QuestionNode.id == FillQuestionNode.id)
                .filter(
                    QuestionNode.type == normalized_type,
                    QuestionNode.course == normalized_course,
                    QuestionNode.belongID == PUBLIC_BELONG_ID,
                )
                .order_by(FillQuestionNode.id.asc())
                .all()
            )
        elif normalized_type == "subjective":
            rows = (
                db.session.query(
                    SubjectiveQuestionNode.id,
                    SubjectiveQuestionNode.brief,
                    SubjectiveQuestionNode.content,
                )
                .join(QuestionNode, QuestionNode.id == SubjectiveQuestionNode.id)
                .filter(
                    QuestionNode.type == normalized_type,
                    QuestionNode.course == normalized_course,
                    QuestionNode.belongID == PUBLIC_BELONG_ID,
                )
                .order_by(SubjectiveQuestionNode.id.asc())
                .all()
            )
        else:
            rows = (
                db.session.query(CustomQuestionNode.id, CustomQuestionNode.brief)
                .join(QuestionNode, QuestionNode.id == CustomQuestionNode.id)
                .filter(
                    QuestionNode.type == normalized_type,
                    QuestionNode.course == normalized_course,
                    QuestionNode.belongID == PUBLIC_BELONG_ID,
                )
                .order_by(CustomQuestionNode.id.asc())
                .all()
            )
            return [
                {"id": int(item_id), "brief": brief or "", "content": ""}
                for item_id, brief in rows
            ]
        return [
            {
                "id": int(item_id),
                "brief": brief or "",
                "content": content or "",
            }
            for item_id, brief, content in rows
        ]
    except Exception:
        return []


def get_practice_sets_by_student(student_id: str) -> list[QuestionSet]:
    try:
        return (
            QuestionSet.query.filter_by(teacher_id=student_id)
            .order_by(QuestionSet.id.asc())
            .all()
        )
    except Exception:
        return []


def get_practice_set_by_id(set_id: int) -> QuestionSet | None:
    try:
        return QuestionSet.query.filter_by(id=set_id).first()
    except Exception:
        return None


def create_practice_set(student_id: str, name: str) -> QuestionSet | None:
    try:
        practice_set = QuestionSet(name=name, teacher_id=student_id)
        db.session.add(practice_set)
        db.session.commit()
        return practice_set
    except Exception:
        db.session.rollback()
        return None


def update_practice_set_name(set_id: int, name: str) -> QuestionSet | None:
    try:
        practice_set = QuestionSet.query.filter_by(id=set_id).first()
        if not practice_set:
            return None
        practice_set.name = name
        db.session.commit()
        return practice_set
    except Exception:
        db.session.rollback()
        return None


def delete_practice_set(set_id: int) -> bool:
    try:
        QuestionSetQuestion.query.filter_by(set_id=set_id).delete()
        deleted_count = QuestionSet.query.filter_by(id=set_id).delete()
        db.session.commit()
        return deleted_count > 0
    except Exception:
        db.session.rollback()
        return False


def get_practice_set_questions(set_id: int) -> list[QuestionSetQuestion]:
    try:
        return (
            QuestionSetQuestion.query.filter_by(set_id=set_id)
            .order_by(QuestionSetQuestion.order_num.asc(), QuestionSetQuestion.question_id.asc())
            .all()
        )
    except Exception:
        return []


def is_question_in_practice_set(set_id: int, question_id: int) -> bool:
    try:
        return (
            QuestionSetQuestion.query.filter_by(set_id=set_id, question_id=question_id).first()
            is not None
        )
    except Exception:
        return False


def add_question_to_practice_set(set_id: int, question_id: int) -> bool:
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


def remove_question_from_practice_set(set_id: int, question_id: int) -> bool:
    try:
        deleted_count = (
            QuestionSetQuestion.query.filter_by(set_id=set_id, question_id=question_id).delete()
        )
        db.session.commit()
        return deleted_count > 0
    except Exception:
        db.session.rollback()
        return False
