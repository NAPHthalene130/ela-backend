from flask import Flask

from api import register_blueprints
from core.config import AppConfig
from core.extensions import cors, db, jwt
from database.models import init_all_tables


def create_app(config: type[AppConfig] = AppConfig) -> Flask:
    """创建并初始化 Flask 应用实例。"""
    app = Flask(__name__)
    app.config.from_object(config)

    # 初始化扩展组件
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)

    # 注册路由并完成数据库结构初始化
    register_blueprints(app)
    init_all_tables(app)

    @app.get("/")
    def health_check():
        return {"status": "ok", "message": "ELA backend is running"}

    return app
