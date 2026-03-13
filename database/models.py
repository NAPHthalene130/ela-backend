from database.extensions import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(50), primary_key=True)
    email = db.Column(db.String(120), unique=True)
    passwordHash = db.Column(db.String(256))


class UserChatWindowTable(db.Model):
    __tablename__ = 'userChatWindowTable'
    id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    windowsId = db.Column(db.String(256), primary_key=True)
    title = db.Column(db.String(1024), nullable=False, default='新对话')
    createTime = db.Column(db.String(64), nullable=False)


class WindowChatNode(db.Model):
    __tablename__ = 'WindowChatTable'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    windowID = db.Column(db.String(256), db.ForeignKey('userChatWindowTable.windowsId'), nullable=False)
    content = db.Column(db.String(102400), nullable=False)
    isUserSend = db.Column(db.Boolean, nullable=False)
    sendTime = db.Column(db.String(64), nullable=False)


class CourseTabel(db.Model):
    __tablename__ = 'courseTabel'
    couse = db.Column(db.String(1024), primary_key=True)
