import os

try:
    from project_config import JWT_SECRET_KEY as PROJECT_JWT_SECRET_KEY
except ImportError:
    PROJECT_JWT_SECRET_KEY = None


class AppConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv("ELA_DATABASE_URI", "sqlite:///project.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = (
        PROJECT_JWT_SECRET_KEY
        or os.getenv("ELA_JWT_SECRET_KEY")
        or "dev-jwt-secret-change-me"
    )
    JSON_AS_ASCII = False
