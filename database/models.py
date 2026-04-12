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


class ChatCardNode(db.Model):
    __tablename__ = "chatCardNodeTable"
    __table_args__ = (
        db.UniqueConstraint("windowsID", "no", name="uq_chat_card_window_no"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    windowsID = db.Column(
        db.String(256),
        db.ForeignKey("userChatWindowTable.windowsId", ondelete="CASCADE"),
        nullable=False,
    )
    no = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    json = db.Column(db.String(8196), nullable=False, default="", server_default="")


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
class graphCourseNode(db.Model):
    __tablename__ = "graphCourseNodeTable"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course = db.Column(db.String(1024), nullable=False, index=True)
    nodeName = db.Column(db.String(1024), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("course", "nodeName", name="uq_graph_course_node"),
    )


class StudentGroup(db.Model):
    __tablename__ = "studentGroupTable"
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
    belongID = db.Column(db.String(50), nullable=True, default="$PUBLIC$")

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
    belongID = db.Column(db.String(50), nullable=True, default="$PUBLIC$")

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
    belongID = db.Column(db.String(50), nullable=True, default="$PUBLIC$")

#主观题类
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
    belongID = db.Column(db.String(50), nullable=True, default="$PUBLIC$")

#自定义题类
class CustomQuestionNode(db.Model):
    __tablename__ = "customQuestionTable"

    id = db.Column(
        db.Integer,
        db.ForeignKey("questionTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    course = db.Column(db.String(1024), nullable=True, default="")
    imageURL = db.Column(db.String(2048), nullable=True, default="")
    brief = db.Column(db.String(1024), nullable=True, default="")
    belongID = db.Column(db.String(50), nullable=True, default="$PUBLIC$")


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


# 学生练习题单表
class StudentQuestionSet(db.Model):
    __tablename__ = "studentQuestionSetTable"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(1024), nullable=False)
    student_id = db.Column(
        db.String(50),
        db.ForeignKey("usersTable.id", ondelete="CASCADE"),
        nullable=False,
    )


# 学生练习题单题目关联表
class StudentQuestionSetQuestion(db.Model):
    __tablename__ = "studentQuestionSetQuestionTable"

    set_id = db.Column(
        db.Integer,
        db.ForeignKey("studentQuestionSetTable.id", ondelete="CASCADE"),
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
    create_teacher_id = db.Column(
        db.String(50),
        db.ForeignKey("usersTable.id", ondelete="CASCADE"),
        nullable=True,
    )
    assignment_name = db.Column(
        db.String(1024),
        nullable=False,
        default="",
        server_default="",
    )
    begin_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("set_id", "group_id", name="uq_set_group"),
    )


# 学生作答表
class StudentAnswer(db.Model):
    __tablename__ = "studentAnswerTable"

    studentID = db.Column(
        db.String(50),
        db.ForeignKey("usersTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assignmentID = db.Column(
        db.Integer,
        db.ForeignKey("questionSetAssignmentTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    questionID = db.Column(
        db.Integer,
        db.ForeignKey("questionTable.id", ondelete="CASCADE"),
        primary_key=True,
    )
    content = db.Column(
        db.String(102400),
        nullable=False,
        default="",
        server_default="",
    )
    imgURL = db.Column(
        db.String(2048),
        nullable=False,
        default="",
        server_default="",
    )


class AnswerHistory(db.Model):
    __tablename__ = "answerHistoryTable"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    userID = db.Column(
        db.String(50),
        db.ForeignKey("usersTable.id", ondelete="CASCADE"),
        nullable=False,
    )
    course = db.Column(db.String(1024), nullable=False, default="", server_default="")
    questionID = db.Column(
        db.Integer,
        db.ForeignKey("questionTable.id", ondelete="CASCADE"),
        nullable=False,
    )
    questionBrief = db.Column(db.String(1024), nullable=False, default="", server_default="")
    isCorrect = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    date = db.Column(db.Date, nullable=False)


def init_all_tables(app):
    with app.app_context():
        db.create_all()
        ensure_user_type_schema()
        ensure_question_schema()
        ensure_student_practice_schema()
        ensure_assignment_schema()
        ensure_student_answer_schema()
        ensure_chat_card_schema()


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


def ensure_question_schema():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    if "questionTable" in table_names:
        question_columns = {column["name"] for column in inspector.get_columns("questionTable")}
        if "course" not in question_columns:
            db.session.execute(
                text(
                    "ALTER TABLE questionTable "
                    "ADD COLUMN course VARCHAR(1024) DEFAULT 'UnKnown'"
                )
            )
            db.session.commit()
        if "belongID" not in question_columns:
            db.session.execute(
                text(
                    "ALTER TABLE questionTable "
                    "ADD COLUMN belongID VARCHAR(50) DEFAULT '$PUBLIC$'"
                )
            )
            db.session.commit()


    question_table_names = (
        "choiceQuestionTable",
        "fillQuestionTable",
        "subjectiveQuestionTable",
        "customQuestionTable",
    )
    for table_name in question_table_names:
        if table_name not in table_names:
            continue

        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if table_name == "customQuestionTable" and "brief" not in columns:
            db.session.execute(
                text(
                    "ALTER TABLE customQuestionTable "
                    "ADD COLUMN brief VARCHAR(1024) DEFAULT ''"
                )
            )
            db.session.commit()
            columns.add("brief")

        if "belongID" not in columns:
            db.session.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    "ADD COLUMN belongID VARCHAR(50) DEFAULT '$PUBLIC$'"
                )
            )
            db.session.commit()
            columns.add("belongID")

        if table_name == "customQuestionTable" and "createUser" in columns:
            db.session.execute(
                text(
                    """
                    UPDATE questionTable
                    SET belongID = (
                        SELECT createUser
                        FROM customQuestionTable
                        WHERE customQuestionTable.id = questionTable.id
                    )
                    WHERE id IN (
                        SELECT id
                        FROM customQuestionTable
                        WHERE createUser IS NOT NULL
                          AND createUser != ''
                    )
                      AND (belongID IS NULL OR belongID = '' OR belongID = '$PUBLIC$')
                    """
                )
            )
            db.session.execute(
                text(
                    """
                    UPDATE customQuestionTable
                    SET belongID = createUser
                    WHERE (belongID IS NULL OR belongID = '' OR belongID = '$PUBLIC$')
                      AND createUser IS NOT NULL
                      AND createUser != ''
                    """
                )
            )
            db.session.commit()


def ensure_student_practice_schema():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "studentQuestionSetTable" not in table_names:
        return
    if "studentQuestionSetQuestionTable" not in table_names:
        return
    if "questionSetTable" not in table_names or "questionSetQuestionTable" not in table_names:
        return
    if "usersTable" not in table_names:
        return

    db.session.execute(
        text(
            """
            INSERT INTO studentQuestionSetTable (id, name, student_id)
            SELECT qs.id, qs.name, qs.teacher_id
            FROM questionSetTable qs
            INNER JOIN usersTable u ON u.id = qs.teacher_id
            WHERE LOWER(COALESCE(u.type, '')) = 'student'
              AND NOT EXISTS (
                SELECT 1
                FROM studentQuestionSetTable sqs
                WHERE sqs.id = qs.id
              )
            """
        )
    )
    db.session.execute(
        text(
            """
            INSERT INTO studentQuestionSetQuestionTable (set_id, question_id, order_num)
            SELECT qsq.set_id, qsq.question_id, COALESCE(qsq.order_num, 0)
            FROM questionSetQuestionTable qsq
            INNER JOIN studentQuestionSetTable sqs ON sqs.id = qsq.set_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM studentQuestionSetQuestionTable sqq
                WHERE sqq.set_id = qsq.set_id
                  AND sqq.question_id = qsq.question_id
            )
            """
        )
    )
    db.session.commit()


def ensure_assignment_schema():
    inspector = inspect(db.engine)
    if "questionSetAssignmentTable" not in inspector.get_table_names():
        return

    assignment_columns = {
        column["name"] for column in inspector.get_columns("questionSetAssignmentTable")
    }
    if "create_teacher_id" not in assignment_columns:
        db.session.execute(
            text(
                "ALTER TABLE questionSetAssignmentTable "
                "ADD COLUMN create_teacher_id VARCHAR(50)"
            )
        )
        db.session.commit()

    if "assignment_name" not in assignment_columns:
        db.session.execute(
            text(
                "ALTER TABLE questionSetAssignmentTable "
                "ADD COLUMN assignment_name VARCHAR(1024) NOT NULL DEFAULT ''"
            )
        )
        db.session.commit()

    # 兼容旧数据：若任务来源题单可追溯到教师，则自动回填创建教师。
    db.session.execute(
        text(
            """
            UPDATE questionSetAssignmentTable
            SET create_teacher_id = (
                SELECT questionSetTable.teacher_id
                FROM questionSetTable
                WHERE questionSetTable.id = questionSetAssignmentTable.set_id
            )
            WHERE create_teacher_id IS NULL OR create_teacher_id = ''
            """
        )
    )
    db.session.execute(
        text(
            """
            UPDATE questionSetAssignmentTable
            SET assignment_name = COALESCE(
                NULLIF(assignment_name, ''),
                (
                    SELECT questionSetTable.name
                    FROM questionSetTable
                    WHERE questionSetTable.id = questionSetAssignmentTable.set_id
                ),
                '未命名任务'
            )
            WHERE assignment_name IS NULL OR assignment_name = ''
            """
        )
    )
    db.session.commit()


def ensure_student_answer_schema():
    inspector = inspect(db.engine)
    if "studentAnswerTable" not in inspector.get_table_names():
        return

    answer_columns = {
        column["name"] for column in inspector.get_columns("studentAnswerTable")
    }
    if "questionID" not in answer_columns:
        db.session.execute(
            text(
                "ALTER TABLE studentAnswerTable "
                "ADD COLUMN questionID INTEGER NOT NULL DEFAULT 0"
            )
        )
        db.session.commit()


def ensure_chat_card_schema():
    inspector = inspect(db.engine)
    if "chatCardNodeTable" not in inspector.get_table_names():
        return

    card_columns = {
        column["name"] for column in inspector.get_columns("chatCardNodeTable")
    }
    if "id" not in card_columns:
        db.session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS chatCardNodeTable_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    windowsID VARCHAR(256) NOT NULL,
                    no INTEGER NOT NULL DEFAULT 0,
                    json VARCHAR(8196) NOT NULL DEFAULT '',
                    FOREIGN KEY(windowsID) REFERENCES userChatWindowTable(windowsId) ON DELETE CASCADE
                )
                """
            )
        )
        db.session.execute(
            text(
                """
                INSERT INTO chatCardNodeTable_new (windowsID, no, json)
                SELECT windowsID, COALESCE(no, 0), COALESCE(json, '')
                FROM chatCardNodeTable
                """
            )
        )
        db.session.execute(text("DROP TABLE chatCardNodeTable"))
        db.session.execute(text("ALTER TABLE chatCardNodeTable_new RENAME TO chatCardNodeTable"))
        db.session.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_card_window_no
                ON chatCardNodeTable (windowsID, no)
                """
            )
        )
        db.session.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_chat_card_window_id
                ON chatCardNodeTable (windowsID)
                """
            )
        )
        db.session.commit()
        return

    if "windowsID" not in card_columns:
        db.session.execute(
            text(
                "ALTER TABLE chatCardNodeTable "
                "ADD COLUMN windowsID VARCHAR(256) NOT NULL DEFAULT ''"
            )
        )
        db.session.commit()
    if "no" not in card_columns:
        db.session.execute(
            text(
                "ALTER TABLE chatCardNodeTable "
                "ADD COLUMN no INTEGER NOT NULL DEFAULT 0"
            )
        )
        db.session.commit()
    if "json" not in card_columns:
        db.session.execute(
            text(
                "ALTER TABLE chatCardNodeTable "
                "ADD COLUMN json VARCHAR(8196) NOT NULL DEFAULT ''"
            )
        )
        db.session.commit()
    db.session.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_card_window_no
            ON chatCardNodeTable (windowsID, no)
            """
        )
    )
    db.session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_chat_card_window_id
            ON chatCardNodeTable (windowsID)
            """
        )
    )
    db.session.commit()
