from flask import Flask

from api.assignment_routes import assignment_bp, student_assignment_bp
from api.auth_routes import auth_bp
from api.chat_routes import chat_bp
from api.group_routes import group_bp
from api.practice_routes import practice_bp
from api.question_routes import question_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(assignment_bp, url_prefix="/api/assignment")
    app.register_blueprint(student_assignment_bp, url_prefix="/api/student")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(group_bp, url_prefix="/api/group")
    app.register_blueprint(practice_bp, url_prefix="/api/practice")
    app.register_blueprint(question_bp, url_prefix="/api/question")
