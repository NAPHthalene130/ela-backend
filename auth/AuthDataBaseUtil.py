from database.models import User
from database.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import random
import string

# 配置 Redis 连接
# Redis 服务运行在 localhost:6379
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.ping() # 测试连接
except Exception as e:
    print(f"Warning: Redis connection failed: {e}")
    redis_client = None

def login(id, password):
    """
    用户登录
    :param id: 用户ID
    :param password: 密码
    :return: 成功返回 User 对象，失败返回 None
    """
    try:
        user = User.query.filter_by(id=id).first()
        if user and check_password_hash(user.passwordHash, password):
            return user
        return None
    except Exception as e:
        print(f"Login error: {e}")
        return None

def register(id, password, email, emailCode):
    """
    用户注册
    :param id: 用户ID
    :param password: 密码
    :param email: 邮箱
    :param emailCode: 验证码
    :return: (bool, message)
    """
    if not redis_client:
        return False, "Redis service unavailable"

    # 验证邮箱验证码
    redis_key = f"email_code:{email}"
    stored_code = redis_client.get(redis_key)
    
    if not stored_code:
        return False, "Verification code expired or invalid"
    
    if stored_code.decode('utf-8') != emailCode:
        return False, "Incorrect verification code"
        
    # 检查用户是否已存在
    if User.query.filter_by(id=id).first():
        return False, "User ID already exists"
        
    if User.query.filter_by(email=email).first():
        return False, "Email already registered"
        
    # 创建新用户
    hashed_password = generate_password_hash(password)
    new_user = User(id=id, email=email, passwordHash=hashed_password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        # 注册成功后删除验证码
        redis_client.delete(redis_key)
        return True, "Registration successful"
    except Exception as e:
        db.session.rollback()
        return False, f"Database error: {str(e)}"

def requireEmailCode(email):
    """
    生成并发送邮箱验证码
    :param email: 邮箱地址
    :return: (bool, message)
    """
    if not email:
        return False, "Email is required"
        
    if not redis_client:
        return False, "Redis service unavailable"
        
    # 生成6位随机验证码
    # code = ''.join(random.choices(string.digits, k=6))
    code = "000000"

    # 存入 Redis，有效期 120 秒
    redis_key = f"email_code:{email}"
    try:
        redis_client.setex(redis_key, 120, code)


        #TODO:邮箱验证码发送

        print(f"Verification code for {email}: {code}")
        return True, f"Verification code sent: {code}" 
    except Exception as e:
        return False, f"Redis error: {str(e)}"
