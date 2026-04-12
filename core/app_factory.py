import os
from pathlib import Path

from flask import Flask

from api import register_blueprints
from core.config import AppConfig
from core.extensions import cors, db, jwt
from database.models import init_all_tables
from database.vectorDB import init_vector_db
from repositories.graph_repository import get_last_graph_error, init_graph_db


def create_app(config: type[AppConfig] = AppConfig) -> Flask:
    """创建并初始化 Flask 应用实例。"""
    app = Flask(__name__)
    app.config.from_object(config)
    graph_db_path = Path(app.instance_path) / "kuzu_graph.db"
    graph_db_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("ELA_KUZU_DB_PATH", str(graph_db_path))

    # 初始化扩展组件
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)

    # 注册路由并完成数据库结构初始化
    register_blueprints(app)
    init_all_tables(app)
    init_vector_db()

    graph_db_state = {"initialized": False}

    def _init_graph_db_once() -> None:
        if graph_db_state["initialized"]:
            return
        graph_db_state["initialized"] = True
        if not init_graph_db():
            print(f"图数据库初始化失败: {get_last_graph_error()}")

    if hasattr(app, "before_serving"):
        app.before_serving(_init_graph_db_once)
    else:
        @app.before_request
        def _init_graph_db_before_request():
            _init_graph_db_once()

    @app.get("/")
    def health_check():
        return {"status": "ok", "message": "ELA backend is running"}

    return app
