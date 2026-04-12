import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

GRAPH_DB_PATH = BACKEND_ROOT / "instance" / "kuzu_graph.db"
GRAPH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("ELA_KUZU_DB_PATH", str(GRAPH_DB_PATH))

from repositories.graph_repository import get_last_graph_error, get_relation, init_graph_db


def main() -> None:
    node_need = "链表"
    course_need = "数据结构"
    max_hop = 3
    if not init_graph_db():
        print(f"图数据库初始化失败: {get_last_graph_error()}")
        return
    relations = get_relation(nodeName=node_need, course=course_need, k=max_hop)
    print(f"节点[{node_need}] 课程[{course_need}] {max_hop}跳范围关系总数: {len(relations)}")
    for index, item in enumerate(relations, start=1):
        print(f"{index}. [{item.course}] {item.node1} -({item.relation})-> {item.node2}")


if __name__ == "__main__":
    main()
