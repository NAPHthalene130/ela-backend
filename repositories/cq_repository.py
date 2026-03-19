from core.extensions import db
from database.models import CQNode


def add_cq_node(cq_node: CQNode) -> bool:
    try:
        cq_count = CQNode.query.count()
        cq_node.id = cq_count + 1
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
