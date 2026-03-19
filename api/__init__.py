from flask import Flask

from api.auth_routes import auth_bp
from api.chat_routes import chat_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
