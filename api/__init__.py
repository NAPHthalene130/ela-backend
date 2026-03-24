from flask import Flask

from api.auth_routes import auth_bp
from api.chat_routes import chat_bp
from api.group_routes import group_bp
from api.question_routes import question_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(group_bp, url_prefix="/api/group")
    app.register_blueprint(question_bp, url_prefix="/api/question")
