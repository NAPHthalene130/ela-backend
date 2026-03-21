from repositories.group_repository import get_group_info_from_studentGroupTable


def get_groups_by_teacher(teacher_id: str) -> list[dict]:
    return get_group_info_from_studentGroupTable(teacher_id)
