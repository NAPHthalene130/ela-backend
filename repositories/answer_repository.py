from datetime import datetime, timezone

from core.extensions import db
from database.models import (
    AnswerHistory,
    ChoiceQuestionNode,
    CustomQuestionNode,
    FillQuestionNode,
    QuestionNode,
    SubjectiveQuestionNode,
)


def add_answer_history(userID: str, questionID: int, isCorrect: bool) -> AnswerHistory | None:
    normalized_user_id = str(userID or "").strip()
    if not normalized_user_id:
        return None
    try:
        normalized_question_id = int(questionID)
    except Exception:
        return None
    if normalized_question_id <= 0:
        return None
    question_brief = ""
    question_course = ""
    target_question = ChoiceQuestionNode.query.filter_by(id=normalized_question_id).first()
    if target_question is None:
        target_question = FillQuestionNode.query.filter_by(id=normalized_question_id).first()
    if target_question is None:
        target_question = SubjectiveQuestionNode.query.filter_by(id=normalized_question_id).first()
    if target_question is None:
        target_question = CustomQuestionNode.query.filter_by(id=normalized_question_id).first()
    if target_question is not None:
        question_brief = str(getattr(target_question, "brief", "") or "").strip()
        question_course = str(getattr(target_question, "course", "") or "").strip()
    if not question_course:
        question_node = QuestionNode.query.filter_by(id=normalized_question_id).first()
        if question_node is not None:
            question_course = str(getattr(question_node, "course", "") or "").strip()
    answer_history = AnswerHistory(
        userID=normalized_user_id,
        course=question_course,
        questionID=normalized_question_id,
        questionBrief=question_brief,
        isCorrect=bool(isCorrect),
        date=datetime.now(timezone.utc).date(),
    )
    try:
        db.session.add(answer_history)
        db.session.commit()
        return answer_history
    except Exception:
        db.session.rollback()
        return None


def get_answer_history(userID: str, course: str, k: int) -> list[AnswerHistory]:
    normalized_user_id = str(userID or "").strip()
    if not normalized_user_id:
        return []
    try:
        normalized_k = int(k)
    except Exception:
        return []
    if normalized_k <= 0:
        return []
    normalized_course = str(course or "").strip()
    try:
        query = AnswerHistory.query.filter_by(userID=normalized_user_id)
        if normalized_course != "$ALL$":
            query = query.filter_by(course=normalized_course)
        return (
            query.order_by(AnswerHistory.date.desc(), AnswerHistory.id.desc())
            .limit(normalized_k)
            .all()
        )
    except Exception:
        return []
