from sqlalchemy import inspect, text

from core.extensions import db
from database.models import CrourseNode


def get_course_list() -> list[str]:
    try:
        courses = CrourseNode.query.all()
        result = []
        for course in courses:
            course_name = getattr(course, "courseName", None) or getattr(course, "course", None)
            if course_name:
                result.append(course_name)
        return result
    except Exception:
        return get_course_list_by_fallback_sql()


def get_course_list_by_fallback_sql() -> list[str]:
    try:
        columns = {column["name"] for column in inspect(db.engine).get_columns("courseTable")}
        target_column = "course" if "course" in columns else "courseName" if "courseName" in columns else None
        if not target_column:
            return []
        rows = db.session.execute(text(f'SELECT "{target_column}" FROM "courseTable"')).all()
        return [row[0] for row in rows if row and row[0]]
    except Exception:
        return []
