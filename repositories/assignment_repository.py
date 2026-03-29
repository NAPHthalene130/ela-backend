from datetime import datetime

from core.extensions import db
from database.models import QuestionSetAssignment, StudentAnswer


def get_assignment_by_teacherID(teacherID: str) -> list[QuestionSetAssignment]:
    """按教师 ID 查询其创建的任务列表。"""
    try:
        return (
            QuestionSetAssignment.query.filter_by(create_teacher_id=teacherID)
            .order_by(QuestionSetAssignment.id.asc())
            .all()
        )
    except Exception:
        return []


def get_assignment_by_id(assignment_id: int) -> QuestionSetAssignment | None:
    try:
        return QuestionSetAssignment.query.filter_by(id=assignment_id).first()
    except Exception:
        return None


def get_student_answers_by_assignment_and_student(
    assignment_id: int, student_id: str
) -> list[StudentAnswer]:
    try:
        return (
            StudentAnswer.query.filter_by(
                assignmentID=assignment_id,
                studentID=student_id,
            )
            .order_by(StudentAnswer.questionID.asc())
            .all()
        )
    except Exception:
        return []


def add_assignment(
    set_id: int,
    group_id: int,
    teacher_id: str,
    assignment_name: str,
    begin_time: datetime | None,
    end_time: datetime | None,
) -> QuestionSetAssignment | None:
    """新增任务并返回创建后的任务对象。"""
    assignment = QuestionSetAssignment(
        set_id=set_id,
        group_id=group_id,
        create_teacher_id=teacher_id,
        assignment_name=assignment_name,
        begin_time=begin_time,
        end_time=end_time,
    )
    try:
        db.session.add(assignment)
        db.session.commit()
        return assignment
    except Exception:
        db.session.rollback()
        return None
