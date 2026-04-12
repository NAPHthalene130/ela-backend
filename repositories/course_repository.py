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


def ensure_course_exists(course: str) -> bool:
    course_name = (course or "").strip()
    if not course_name:
        return False
    try:
        existing = CrourseNode.query.filter_by(course=course_name).first()
        if existing:
            return True
        db.session.add(CrourseNode(course=course_name))
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
    try:
        columns = {column["name"] for column in inspect(db.engine).get_columns("courseTable")}
        target_column = "course" if "course" in columns else "courseName" if "courseName" in columns else None
        if not target_column:
            return False
        existing = db.session.execute(
            text(f'SELECT 1 FROM "courseTable" WHERE "{target_column}" = :course LIMIT 1'),
            {"course": course_name},
        ).first()
        if existing:
            return True
        db.session.execute(
            text(f'INSERT INTO "courseTable" ("{target_column}") VALUES (:course)'),
            {"course": course_name},
        )
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False
