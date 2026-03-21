from sqlalchemy import inspect, text

from core.extensions import db

USER_TYPES = ("student", "teacher")


class User(db.Model):
    __tablename__ = "usersTable"
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

    id = db.Column(db.String(50), db.ForeignKey("usersTable.id"), nullable=False)
    windowsId = db.Column(db.String(256), primary_key=True)
    title = db.Column(db.String(1024), nullable=False, default="新对话")
    createTime = db.Column(db.String(64), nullable=False)


class WindowChatNode(db.Model):
    __tablename__ = "windowChatTable"

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

# 小组表
class StudentGroup(db.Model):
    __tablename__ = "studentGroupTable"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(1024), nullable=False)
    teacher_id = db.Column(
        db.String(50),
        db.ForeignKey("usersTable.id", ondelete="CASCADE"),
        nullable=False,
    )


# 小组成员表
class StudentGroupMember(db.Model):
    __tablename__ = "studentGroupMemberTable"

    group_id = db.Column(
        db.Integer,
        db.ForeignKey("studentGroupTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    student_id = db.Column(
        db.String(50),
        db.ForeignKey("usersTable.id", ondelete="CASCADE"),
        primary_key=True,
    )

#题目类
class QuestionNode(db.Model):
    __tablename__ = "questionTable"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.String(1024), nullable=True, default="UnKnown")
    course = db.Column(db.String(1024), nullable=True, default="UnKnown")

#选择题类
class ChoiceQuestionNode(db.Model):
    __tablename__ = "choiceQuestionTable"

    id = db.Column(
        db.Integer,
        db.ForeignKey("questionTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
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

#填空题类
class FillQuestionNode(db.Model):
    __tablename__ = "fillQuestionTable"

    id = db.Column(
        db.Integer,
        db.ForeignKey("questionTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    course = db.Column(db.String(1024), nullable=True, default="")
    content = db.Column(db.String(1024), nullable=False)
    answer = db.Column(db.String(1024), nullable=True, default="")
    brief = db.Column(db.String(1024), nullable=True, default="")
    explanation = db.Column(db.String(4096), nullable=True, default="")
    difficulty = db.Column(db.Integer, nullable=False, default=0)


class SubjectiveQuestionNode(db.Model):
    __tablename__ = "subjectiveQuestionTable"

    id = db.Column(
        db.Integer,
        db.ForeignKey("questionTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    course = db.Column(db.String(1024), nullable=True, default="")
    content = db.Column(db.String(1024), nullable=False)
    answer = db.Column(db.String(1024), nullable=True, default="")
    brief = db.Column(db.String(1024), nullable=True, default="")
    explanation = db.Column(db.String(4096), nullable=True, default="")
    difficulty = db.Column(db.Integer, nullable=False, default=0)


class CustomQuestionNode(db.Model):
    __tablename__ = "customQuestionTable"

    id = db.Column(
        db.Integer,
        db.ForeignKey("questionTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    course = db.Column(db.String(1024), nullable=True, default="")
    imageURL = db.Column(db.String(2048), nullable=True, default="")


CQNode = ChoiceQuestionNode
FQNode = FillQuestionNode
    

# 题单表
class QuestionSet(db.Model):
    __tablename__ = "questionSetTable"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(1024), nullable=False)
    teacher_id = db.Column(
        db.String(50),
        db.ForeignKey("usersTable.id", ondelete="CASCADE"),
        nullable=False,
    )


# 题单题目关联表
class QuestionSetQuestion(db.Model):
    __tablename__ = "questionSetQuestionTable"

    set_id = db.Column(
        db.Integer,
        db.ForeignKey("questionSetTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questionTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    order_num = db.Column(db.Integer, nullable=False, default=0)


# 题单下发表
class QuestionSetAssignment(db.Model):
    __tablename__ = "questionSetAssignmentTable"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    set_id = db.Column(
        db.Integer,
        db.ForeignKey("questionSetTable.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("studentGroupTable.id", ondelete="CASCADE"),
        nullable=False,
    )
    begin_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("set_id", "group_id", name="uq_set_group"),
    )


def init_all_tables(app):
    with app.app_context():
        db.create_all()
        ensure_user_type_schema()


def ensure_user_type_schema():
    inspector = inspect(db.engine)
    if "usersTable" not in inspector.get_table_names():
        return

    user_columns = {column["name"] for column in inspector.get_columns("usersTable")}
    if "type" not in user_columns:
        db.session.execute(
            text(
                "ALTER TABLE usersTable "
                "ADD COLUMN type VARCHAR(16) NOT NULL DEFAULT 'student'"
            )
        )
        db.session.commit()

    db.session.execute(
        text(
            "UPDATE usersTable "
            "SET type = 'student' "
            "WHERE type IS NULL OR type NOT IN ('student', 'teacher')"
        )
    )
    db.session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS users_type_insert_check
            BEFORE INSERT ON usersTable
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
            BEFORE UPDATE OF type ON usersTable
            FOR EACH ROW
            WHEN NEW.type IS NULL OR NEW.type NOT IN ('student', 'teacher')
            BEGIN
                SELECT RAISE(ABORT, 'Invalid user type');
            END;
            """
        )
    )
    db.session.commit()
