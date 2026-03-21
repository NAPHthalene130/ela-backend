from core.extensions import db
from database.models import CQNode, QuestionNode


def add_cq_node(cq_node: CQNode) -> bool:
    try:
        question_node = QuestionNode(type="choice", course=cq_node.course)
        db.session.add(question_node)
        db.session.flush()
        cq_node.id = question_node.id
        db.session.add(cq_node)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def update_cq_node(cq_node: CQNode) -> bool:
    try:
        target = CQNode.query.filter_by(id=cq_node.id).first()
        if not target:
            return False
        target.course = cq_node.course
        target.content = cq_node.content
        target.optionA = cq_node.optionA
        target.optionB = cq_node.optionB
        target.optionC = cq_node.optionC
        target.optionD = cq_node.optionD
        target.answer = cq_node.answer
        target.brief = cq_node.brief
        target.explanation = cq_node.explanation
        target.difficulty = cq_node.difficulty
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False
