from core.extensions import db
from database.models import (
    ChoiceQuestionNode,
    CustomQuestionNode,
    FillQuestionNode,
    QuestionNode,
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


def add_custom_question(course: str, content: str) -> int | None:
    question_node = QuestionNode(type="custom", course=course)
    custom_question = CustomQuestionNode(course=course, imageURL=content)
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
