from database.models import User


def get_user_by_id(user_id: str) -> User | None:
    return User.query.filter_by(id=user_id).first()


def get_user_by_email(email: str) -> User | None:
    return User.query.filter_by(email=email).first()
