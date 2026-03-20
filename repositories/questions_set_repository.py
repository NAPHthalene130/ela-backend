from datetime import datetime

from core.extensions import db
from database.models import QuestionSet, QuestionSetAssignment, QuestionSetQuestion


def add_question_set(name: str, teacher_id: str) -> int | None:
    question_set = QuestionSet(name=name, teacher_id=teacher_id)
    try:
        db.session.add(question_set)
        db.session.commit()
        return question_set.id
    except Exception:
        db.session.rollback()
        return None


def add_question_set_question(set_id: int, question_id: int, order_num: int) -> bool:
    question_set_question = QuestionSetQuestion(
        set_id=set_id,
        question_id=question_id,
        order_num=order_num,
    )
    try:
        db.session.add(question_set_question)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def add_question_set_assignment(
    set_id: int,
    group_id: int,
    begin_time: datetime | None,
    end_time: datetime | None,
) -> int | None:
    question_set_assignment = QuestionSetAssignment(
        set_id=set_id,
        group_id=group_id,
        begin_time=begin_time,
        end_time=end_time,
    )
    try:
        db.session.add(question_set_assignment)
        db.session.commit()
        return question_set_assignment.id
    except Exception:
        db.session.rollback()
        return None
