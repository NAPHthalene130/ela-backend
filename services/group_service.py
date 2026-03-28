from repositories.group_repository import (
    add_student_group,
    add_student_group_member,
    get_groups_by_teacherID,
    get_students_from_groups,
    is_group_owned_by_teacher,
)


def get_groups_by_teacher(teacher_id: str) -> list[dict]:
    """返回前端所需的小组列表结构。"""
    groups = get_groups_by_teacherID(teacher_id)
    return [{"id": group.id, "name": group.name} for group in groups]


def create_group_for_teacher(teacher_id: str, group_name: str) -> int | None:
    """创建教师小组并返回新建小组 ID。"""
    return add_student_group(group_name, teacher_id)


def get_group_students_for_teacher(teacher_id: str, group_id: int) -> list[str] | None:
    """返回教师名下指定小组的成员列表。"""
    if not is_group_owned_by_teacher(group_id, teacher_id):
        return None
    return get_students_from_groups(group_id)


def add_student_to_group_for_teacher(
    teacher_id: str, group_id: int, student_id: str
) -> tuple[bool, str]:
    """向教师名下小组添加学生。"""
    if not is_group_owned_by_teacher(group_id, teacher_id):
        return False, "Forbidden"
    return add_student_group_member(group_id, student_id)
