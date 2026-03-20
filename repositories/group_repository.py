from core.extensions import db
from database.models import StudentGroup, StudentGroupMember


def add_student_group(name: str, teacher_id: str) -> int | None:
    student_group = StudentGroup(name=name, teacher_id=teacher_id)
    try:
        db.session.add(student_group)
        db.session.commit()
        return student_group.id
    except Exception:
        db.session.rollback()
        return None


def add_student_group_member(group_id: int, student_id: str) -> bool:
    group_member = StudentGroupMember(group_id=group_id, student_id=student_id)
    try:
        db.session.add(group_member)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False
