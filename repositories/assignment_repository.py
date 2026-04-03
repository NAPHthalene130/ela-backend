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


def get_assignments_by_group_ids(group_ids: list[int]) -> list[QuestionSetAssignment]:
    """按小组 ID 列表查询任务列表。"""
    if not group_ids:
        return []

    try:
        return (
            QuestionSetAssignment.query.filter(
                QuestionSetAssignment.group_id.in_(group_ids)
            )
            .order_by(
                QuestionSetAssignment.begin_time.asc().nullsfirst(),
                QuestionSetAssignment.id.asc(),
            )
            .all()
        )
    except Exception:
        return []


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


def save_student_answers(
    assignment_id: int, student_id: str, answers: list[dict]
) -> list[StudentAnswer] | None:
    """保存学生在指定任务下的作答内容。"""
    try:
        existing_answers = {
            item.questionID: item
            for item in get_student_answers_by_assignment_and_student(assignment_id, student_id)
        }

        for answer_item in answers:
            question_id = answer_item["questionID"]
            target_answer = existing_answers.get(question_id)
            if not target_answer:
                target_answer = StudentAnswer(
                    assignmentID=assignment_id,
                    studentID=student_id,
                    questionID=question_id,
                )
                db.session.add(target_answer)
                existing_answers[question_id] = target_answer

            target_answer.content = answer_item.get("content", "")
            target_answer.imgURL = answer_item.get("imgURL", "")

        db.session.commit()
        return list(existing_answers.values())
    except Exception:
        db.session.rollback()
        return None


def delete_assignment_by_teacher(assignment_id: int, teacher_id: str) -> bool:
    """删除教师名下的任务及其关联作答数据。"""
    try:
        assignment = QuestionSetAssignment.query.filter_by(
            id=assignment_id,
            create_teacher_id=teacher_id,
        ).first()
        if not assignment:
            return False

        StudentAnswer.query.filter_by(assignmentID=assignment_id).delete()
        db.session.delete(assignment)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


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
