import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
GRAPH_DB_PATH = BACKEND_ROOT / "instance" / "kuzu_graph.db"
GRAPH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("ELA_KUZU_DB_PATH", str(GRAPH_DB_PATH))

from core.config import AppConfig
from core.extensions import db
from database.models import graphCourseNode, init_all_tables
from repositories.graph_repository import (
    get_last_graph_error,
    import_relation,
    init_graph_db,
    relation_exists,
)

UNCOMPLETED_DIR = Path(__file__).resolve().parent / "uncompleted"
COMPLETED_DIR = Path(__file__).resolve().parent / "completed"
_NODE_CACHE: set[tuple[str, str]] = set()
_RELATION_CACHE: set[tuple[str, str, str, str]] = set()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _available_destination(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def _move_to_completed(file_path: Path) -> None:
    relative_path = file_path.relative_to(UNCOMPLETED_DIR)
    target_path = COMPLETED_DIR / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    final_target_path = _available_destination(target_path)
    shutil.move(str(file_path), str(final_target_path))


def _remove_empty_directories(root: Path) -> None:
    if not root.exists():
        return
    for directory in sorted(
        (item for item in root.rglob("*") if item.is_dir()),
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        if not any(directory.iterdir()):
            directory.rmdir()


def _read_items(json_file: Path) -> list[dict[str, Any]]:
    payload = json.loads(json_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _ensure_graph_course_node(course: str, node_name: str) -> None:
    key = (course, node_name)
    if key in _NODE_CACHE:
        return
    exists = graphCourseNode.query.filter_by(course=course, nodeName=node_name).first()
    if exists is None:
        db.session.add(graphCourseNode(course=course, nodeName=node_name))
        db.session.commit()
    _NODE_CACHE.add(key)


def _ensure_graph_course_nodes(course: str, node1: str, node2: str) -> None:
    _ensure_graph_course_node(course, node1)
    _ensure_graph_course_node(course, node2)


def _relation_key(course: str, node1: str, node2: str, relation: str) -> tuple[str, str, str, str]:
    return (course, node1, node2, relation)


def _relation_already_exists(course: str, node1: str, node2: str, relation: str) -> bool:
    key = _relation_key(course, node1, node2, relation)
    if key in _RELATION_CACHE:
        return True
    if relation_exists(node1=node1, node2=node2, relation=relation, course=course):
        _RELATION_CACHE.add(key)
        return True
    return False


def _import_file(json_file: Path) -> tuple[int, int]:
    items = _read_items(json_file)
    total = len(items)
    success = 0
    for index, item in enumerate(items, start=1):
        course = _normalize(item.get("course"))
        node1 = _normalize(item.get("node1"))
        node2 = _normalize(item.get("node2"))
        relation = _normalize(item.get("relation"))
        ok = False
        already_exists = False
        if course and node1 and node2 and relation:
            if _relation_already_exists(course=course, node1=node1, node2=node2, relation=relation):
                ok = True
                already_exists = True
            else:
                _ensure_graph_course_nodes(course=course, node1=node1, node2=node2)
                ok = import_relation(node1=node1, node2=node2, relation=relation, course=course)
                if ok:
                    _RELATION_CACHE.add(_relation_key(course, node1, node2, relation))
        if ok:
            success += 1
            if already_exists:
                print(f"已完成{index}/{total}条[{json_file.name}] 已存在", flush=True)
            else:
                print(f"已完成{index}/{total}条[{json_file.name}]", flush=True)
        else:
            error_message = _normalize(get_last_graph_error())
            if error_message:
                print(f"已完成{index}/{total}条[{json_file.name}] 失败: {error_message}", flush=True)
            else:
                print(f"已完成{index}/{total}条[{json_file.name}] 失败", flush=True)
    return success, total


def run_import() -> dict[str, int]:
    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
    if not UNCOMPLETED_DIR.exists():
        print("未找到uncompleted目录", flush=True)
        return {"files_total": 0, "files_success": 0, "relations_total": 0, "relations_success": 0}
    json_files = sorted(UNCOMPLETED_DIR.rglob("*.json"))
    if not json_files:
        print("未找到可导入JSON文件", flush=True)
        return {"files_total": 0, "files_success": 0, "relations_total": 0, "relations_success": 0}

    files_success = 0
    relations_total = 0
    relations_success = 0
    for json_file in json_files:
        try:
            success, total = _import_file(json_file)
            relations_total += total
            relations_success += success
            if total > 0 and success == total:
                _move_to_completed(json_file)
                files_success += 1
        except Exception:
            continue
    _remove_empty_directories(UNCOMPLETED_DIR)
    return {
        "files_total": len(json_files),
        "files_success": files_success,
        "relations_total": relations_total,
        "relations_success": relations_success,
    }


def _create_db_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(AppConfig)
    db.init_app(app)
    init_all_tables(app)
    return app


def main() -> None:
    app = _create_db_app()
    with app.app_context():
        if not init_graph_db():
            error_message = _normalize(get_last_graph_error()) or "图数据库初始化失败"
            print(f"图数据库初始化失败: {error_message}", flush=True)
            return
        summary = run_import()
    print(
        "图谱导入完成: 文件 {}/{}，关系 {}/{}".format(
            summary["files_success"],
            summary["files_total"],
            summary["relations_success"],
            summary["relations_total"],
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
