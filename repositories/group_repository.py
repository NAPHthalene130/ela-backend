from core.extensions import db
from database.models import StudentGroup, StudentGroupMember, User


def add_student_group(name: str, teacher_id: str) -> int | None:
    """新增教师小组并返回小组 ID。"""
    student_group = StudentGroup(name=name, teacher_id=teacher_id)
    try:
        db.session.add(student_group)
        db.session.commit()
        return student_group.id
    except Exception:
        db.session.rollback()
        return None


def add_student_group_member(group_id: int, student_id: str) -> tuple[bool, str]:
    """向指定小组添加学生成员，并返回执行结果与提示信息。"""
    student = User.query.filter_by(id=student_id).first()
    if not student:
        return False, "Student ID does not exist"

    target_group = StudentGroup.query.filter_by(id=group_id).first()
    if not target_group:
        return False, "Group not found"

    exists_member = StudentGroupMember.query.filter_by(
        group_id=group_id, student_id=student_id
    ).first()
    if exists_member:
        return False, "Student already in group"

    group_member = StudentGroupMember(group_id=group_id, student_id=student_id)
    try:
        db.session.add(group_member)
        db.session.commit()
        return True, "success"
    except Exception:
        db.session.rollback()
        return False, "Failed to add student"


def get_group_info_from_studentGroupTable(teacherID: str) -> list[dict]:
    """返回指定教师的小组简要信息列表。"""
    try:
        groups = (
            StudentGroup.query.filter_by(teacher_id=teacherID)
            .order_by(StudentGroup.id.asc())
            .all()
        )
        return [{"id": group.id, "name": group.name} for group in groups]
    except Exception:
        return []


def get_groups_by_teacherID(teacherID: str) -> list[StudentGroup]:
    """按教师 ID 返回 StudentGroup 模型对象列表。"""
    try:
        return (
            StudentGroup.query.filter_by(teacher_id=teacherID)
            .order_by(StudentGroup.id.asc())
            .all()
        )
    except Exception:
        return []


def get_students_from_groups(groupID: int) -> list[str]:
    """返回指定小组内的学生 ID 列表。"""
    try:
        group_members = (
            StudentGroupMember.query.filter_by(group_id=groupID)
            .order_by(StudentGroupMember.student_id.asc())
            .all()
        )
        return [member.student_id for member in group_members]
    except Exception:
        return []


def is_group_owned_by_teacher(group_id: int, teacher_id: str) -> bool:
    """校验小组是否属于指定教师。"""
    try:
        target_group = StudentGroup.query.filter_by(
            id=group_id, teacher_id=teacher_id
        ).first()
        return target_group is not None
    except Exception:
        return False
