from core.extensions import db
from sqlalchemy import text
from types import SimpleNamespace
from database.models import (
    ChoiceQuestionNode,
    CustomQuestionNode,
    FillQuestionNode,
    QuestionNode,
    QuestionSet,
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
) -> int | None:
    question_node = QuestionNode(type="choice", course=course)
    choice_question = ChoiceQuestionNode(
        course=course,
        content=content,
        optionA=optionA,
        optionB=optionB,
        optionC=optionC,
        optionD=optionD,
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


def add_fill_question(course: str, content: str) -> int | None:
    question_node = QuestionNode(type="fill", course=course)
    fill_question = FillQuestionNode(course=course, content=content)
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


def add_subjective_question(course: str, content: str) -> int | None:
    question_node = QuestionNode(type="subjective", course=course)
    subjective_question = SubjectiveQuestionNode(course=course, content=content)
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


def add_custom_question(course: str, imageURL: str, createUser: str = "") -> int | None:
    question_node = QuestionNode(type="custom", course=course)
    custom_question = CustomQuestionNode(
        course=course,
        imageURL=imageURL,
        createUser=createUser,
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


def get_questions_set_by_teacherID(teacherID: str) -> list[QuestionSet]:
    try:
        return (
            QuestionSet.query.filter_by(teacher_id=teacherID)
            .order_by(QuestionSet.id.asc())
            .all()
        )
    except Exception:
        return []


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


def get_question_node_by_id(question_id: int) -> QuestionNode | None:
    try:
        question_node = QuestionNode.query.filter_by(id=question_id).first()
        if question_node:
            return question_node
    except Exception:
        pass

    try:
        row = db.session.execute(
            text('SELECT id, type FROM "questionTable" WHERE id = :question_id'),
            {"question_id": question_id},
        ).first()
        if not row:
            return None
        return SimpleNamespace(id=row[0], type=row[1])
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
