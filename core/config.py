from datetime import timedelta
import os

try:
    from project_config import JWT_SECRET_KEY as PROJECT_JWT_SECRET_KEY
except ImportError:
    PROJECT_JWT_SECRET_KEY = None


BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
DATABASE_PATH_CANDIDATES = (
    os.path.join(BACKEND_DIR, "instance", "project.db"),
    os.path.join(PROJECT_ROOT_DIR, "instance", "project.db"),
)


def resolve_default_database_path() -> str:
    for candidate in DATABASE_PATH_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    fallback_path = DATABASE_PATH_CANDIDATES[0]
    os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
    return fallback_path


DEFAULT_DATABASE_PATH = resolve_default_database_path()
DEFAULT_QUESTION_IMAGE_UPLOAD_DIR = os.path.join(BACKEND_DIR, "instance", "question_images")
os.makedirs(DEFAULT_QUESTION_IMAGE_UPLOAD_DIR, exist_ok=True)


class AppConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "ELA_DATABASE_URI",
        f"sqlite:///{DEFAULT_DATABASE_PATH.replace(os.sep, '/')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    QUESTION_IMAGE_UPLOAD_DIR = os.getenv(
        "ELA_QUESTION_IMAGE_UPLOAD_DIR",
        DEFAULT_QUESTION_IMAGE_UPLOAD_DIR,
    )
    MAX_QUESTION_IMAGE_SIZE = int(os.getenv("ELA_MAX_QUESTION_IMAGE_SIZE", str(10 * 1024 * 1024)))
    JWT_SECRET_KEY = (
        PROJECT_JWT_SECRET_KEY
        or os.getenv("ELA_JWT_SECRET_KEY")
        or "dev-jwt-secret-change-me"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("ELA_JWT_ACCESS_TOKEN_EXPIRES_DAYS", "7"))
    )
    JSON_AS_ASCII = False
