from sqlalchemy import inspect, text

from core.extensions import db

USER_TYPES = ("student", "teacher")


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint("type IN ('student', 'teacher')", name="ck_users_type"),
    )

    id = db.Column(db.String(50), primary_key=True)
    email = db.Column(db.String(120), unique=True)
    passwordHash = db.Column(db.String(256))
    type = db.Column(
        db.String(16),
        nullable=False,
        default="student",
        server_default="student",
    )


class UserChatWindowTable(db.Model):
    __tablename__ = "userChatWindowTable"

    id = db.Column(db.String(50), db.ForeignKey("users.id"), nullable=False)
    windowsId = db.Column(db.String(256), primary_key=True)
    title = db.Column(db.String(1024), nullable=False, default="新对话")
    createTime = db.Column(db.String(64), nullable=False)


class WindowChatNode(db.Model):
    __tablename__ = "WindowChatTable"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    windowID = db.Column(
        db.String(256),
        db.ForeignKey("userChatWindowTable.windowsId"),
        nullable=False,
    )
    content = db.Column(db.String(102400), nullable=False)
    isUserSend = db.Column(db.Boolean, nullable=False)
    sendTime = db.Column(db.String(64), nullable=False)


class CrourseNode(db.Model):
    __tablename__ = "courseTable"
    course = db.Column(db.String(1024), primary_key=True)


class CQNode(db.Model):
    __tablename__ = "choiceQuestionTable"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course = db.Column(db.String(1024), nullable=True, default="")
    content = db.Column(db.String(1024), nullable=False)
    optionA = db.Column(db.String(1024), nullable=True, default="")
    optionB = db.Column(db.String(1024), nullable=True, default="")
    optionC = db.Column(db.String(1024), nullable=True, default="")
    optionD = db.Column(db.String(1024), nullable=True, default="")
    answer = db.Column(db.String(16), nullable=True, default="")
    brief = db.Column(db.String(1024), nullable=True, default="")
    explanation = db.Column(db.String(4096), nullable=True, default="")
    difficulty = db.Column(db.Integer, nullable=False, default=0)


def init_all_tables(app):
    with app.app_context():
        db.create_all()
        ensure_user_type_schema()


def ensure_user_type_schema():
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "type" not in user_columns:
        db.session.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN type VARCHAR(16) NOT NULL DEFAULT 'student'"
            )
        )
        db.session.commit()

    db.session.execute(
        text(
            "UPDATE users "
            "SET type = 'student' "
            "WHERE type IS NULL OR type NOT IN ('student', 'teacher')"
        )
    )
    db.session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS users_type_insert_check
            BEFORE INSERT ON users
            FOR EACH ROW
            WHEN NEW.type IS NULL OR NEW.type NOT IN ('student', 'teacher')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid user type');
            END;
            """
        )
    )
    db.session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS users_type_update_check
            BEFORE UPDATE OF type ON users
            FOR EACH ROW
            WHEN NEW.type IS NULL OR NEW.type NOT IN ('student', 'teacher')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid user type');
            END;
            """
        )
    )
    db.session.commit()
