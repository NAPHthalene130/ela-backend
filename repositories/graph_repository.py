import os
import difflib
from pathlib import Path

from database.graphModels import GraphNode

_CONNECTION = None
_LAST_ERROR = ""


def _escape(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace("'", "''")


def _normalize(value: str) -> str:
    return (value or "").strip()


def _get_db_path() -> str:
    config_path = _normalize(os.getenv("ELA_KUZU_DB_PATH", ""))
    if config_path:
        target = Path(config_path)
    else:
        target = Path(__file__).resolve().parents[1] / "instance" / "kuzu_graph.db"
    if target.suffix:
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        target.mkdir(parents=True, exist_ok=True)
        target = target / "kuzu_graph.db"
    return str(target)


def _get_connection():
    global _CONNECTION
    if _CONNECTION is not None:
        return _CONNECTION
    db_path = _get_db_path()
    import kuzu

    database = kuzu.Database(db_path)
    connection = kuzu.Connection(database)
    _ensure_schema(connection)
    _CONNECTION = connection
    return _CONNECTION


def init_graph_db() -> bool:
    global _LAST_ERROR
    try:
        _get_connection()
        _LAST_ERROR = ""
        return True
    except Exception as error:
        _LAST_ERROR = str(error)
        return False


def get_last_graph_error() -> str:
    return _LAST_ERROR


def _ensure_schema(connection) -> None:
    try:
        connection.execute(
            "CREATE NODE TABLE IF NOT EXISTS Node(id STRING, course STRING, nodeName STRING, PRIMARY KEY(id));"
        )
    except Exception:
        try:
            connection.execute(
                "CREATE NODE TABLE Node(id STRING, course STRING, nodeName STRING, PRIMARY KEY(id));"
            )
        except Exception:
            pass
    try:
        connection.execute(
            "CREATE REL TABLE IF NOT EXISTS RELATES(FROM Node TO Node, course STRING, relation STRING);"
        )
    except Exception:
        try:
            connection.execute(
                "CREATE REL TABLE RELATES(FROM Node TO Node, course STRING, relation STRING);"
            )
        except Exception:
            pass


def _rows(result) -> list[list]:
    output: list[list] = []
    if result is None:
        return output
    if hasattr(result, "has_next") and hasattr(result, "get_next"):
        while result.has_next():
            row = result.get_next()
            if isinstance(row, tuple):
                output.append(list(row))
            elif isinstance(row, list):
                output.append(row)
            else:
                output.append([row])
        return output
    if hasattr(result, "get_as_df"):
        dataframe = result.get_as_df()
        if dataframe is not None:
            for item in dataframe.values.tolist():
                if isinstance(item, list):
                    output.append(item)
                elif isinstance(item, tuple):
                    output.append(list(item))
                else:
                    output.append([item])
    return output


def _first_int(result, default: int = 0) -> int:
    rows = _rows(result)
    if not rows or not rows[0]:
        return default
    try:
        return int(rows[0][0])
    except Exception:
        return default


def _node_id(course: str, node_name: str) -> str:
    return f"{course}::{node_name}"


def _to_graph_node(course: str, node1: str, node2: str, relation: str) -> GraphNode:
    try:
        return GraphNode(course=course, node1=node1, node2=node2, relation=relation)
    except TypeError:
        item = GraphNode()
        item.course = course
        item.node1 = node1
        item.node2 = node2
        item.relation = relation
        return item


def get_all_courses() -> list[str]:
    global _LAST_ERROR
    try:
        connection = _get_connection()
        result = connection.execute("MATCH (n:Node) RETURN DISTINCT n.course;")
        courses: list[str] = []
        for row in _rows(result):
            if not row:
                continue
            course = _normalize(str(row[0]))
            if not course:
                continue
            courses.append(course)
        _LAST_ERROR = ""
        return sorted(set(courses))
    except Exception as error:
        _LAST_ERROR = str(error)
        return []


def resolve_course_name(course: str) -> str:
    clean_course = _normalize(course)
    if not clean_course:
        return ""
    courses = get_all_courses()
    if not courses:
        return clean_course
    if clean_course in courses:
        return clean_course
    lower_mapping = {item.lower(): item for item in courses}
    lowered = clean_course.lower()
    if lowered in lower_mapping:
        return lower_mapping[lowered]
    matched = difflib.get_close_matches(clean_course, courses, n=1, cutoff=0.3)
    if matched:
        return matched[0]
    return clean_course


def get_course_node_names(course: str, limit: int = 5000) -> list[str]:
    global _LAST_ERROR
    clean_course = _normalize(course)
    if not clean_course:
        return []
    try:
        max_rows = int(limit)
    except Exception:
        max_rows = 5000
    if max_rows <= 0:
        max_rows = 5000
    try:
        connection = _get_connection()
        escaped_course = _escape(clean_course)
        result = connection.execute(
            "MATCH (n:Node {course: '%s'}) RETURN DISTINCT n.nodeName LIMIT %d;"
            % (escaped_course, max_rows)
        )
        node_names: list[str] = []
        for row in _rows(result):
            if not row:
                continue
            node_name = _normalize(str(row[0]))
            if not node_name:
                continue
            node_names.append(node_name)
        _LAST_ERROR = ""
        return sorted(set(node_names))
    except Exception as error:
        _LAST_ERROR = str(error)
        return []


def _ensure_node(connection, course: str, node_name: str) -> None:
    node_id = _escape(_node_id(course, node_name))
    clean_course = _escape(course)
    clean_node_name = _escape(node_name)
    exists = connection.execute(
        "MATCH (n:Node {id: '%s'}) RETURN COUNT(n);"
        % node_id
    )
    if _first_int(exists, 0) > 0:
        return
    connection.execute(
        "CREATE (n:Node {id: '%s', course: '%s', nodeName: '%s'});"
        % (node_id, clean_course, clean_node_name)
    )


def relation_exists(node1: str, node2: str, relation: str, course: str) -> bool:
    global _LAST_ERROR
    clean_node1 = _normalize(node1)
    clean_node2 = _normalize(node2)
    clean_relation = _normalize(relation)
    clean_course = _normalize(course)
    if not clean_node1 or not clean_node2 or not clean_relation or not clean_course:
        return False
    try:
        connection = _get_connection()
        escaped_course = _escape(clean_course)
        escaped_relation = _escape(clean_relation)
        node1_id = _escape(_node_id(clean_course, clean_node1))
        node2_id = _escape(_node_id(clean_course, clean_node2))
        exists = connection.execute(
            "MATCH (a:Node {id: '%s'})-[r:RELATES {course: '%s', relation: '%s'}]->(b:Node {id: '%s'}) RETURN COUNT(r);"
            % (node1_id, escaped_course, escaped_relation, node2_id)
        )
        _LAST_ERROR = ""
        return _first_int(exists, 0) > 0
    except Exception as error:
        _LAST_ERROR = str(error)
        return False


def import_relation(node1: str, node2: str, relation: str, course: str) -> bool:
    global _LAST_ERROR
    clean_node1 = _normalize(node1)
    clean_node2 = _normalize(node2)
    clean_relation = _normalize(relation)
    clean_course = _normalize(course)
    if not clean_node1 or not clean_node2 or not clean_relation or not clean_course:
        return False
    try:
        connection = _get_connection()
        _ensure_node(connection, clean_course, clean_node1)
        _ensure_node(connection, clean_course, clean_node2)
        if relation_exists(clean_node1, clean_node2, clean_relation, clean_course):
            return True
        escaped_course = _escape(clean_course)
        escaped_relation = _escape(clean_relation)
        node1_id = _escape(_node_id(clean_course, clean_node1))
        node2_id = _escape(_node_id(clean_course, clean_node2))
        connection.execute(
            "MATCH (a:Node {id: '%s'}), (b:Node {id: '%s'}) CREATE (a)-[:RELATES {course: '%s', relation: '%s'}]->(b);"
            % (node1_id, node2_id, escaped_course, escaped_relation)
        )
        _LAST_ERROR = ""
        return True
    except Exception as error:
        _LAST_ERROR = str(error)
        return False


def _get_one_hop_edges(connection, center: str, course: str) -> list[tuple[str, str, str, str]]:
    escaped_center = _escape(center)
    escaped_course = _escape(course)
    outgoing = connection.execute(
        "MATCH (a:Node {course: '%s', nodeName: '%s'})-[r:RELATES {course: '%s'}]->(b:Node {course: '%s'}) "
        "RETURN a.nodeName, b.nodeName, r.relation, r.course;"
        % (escaped_course, escaped_center, escaped_course, escaped_course)
    )
    incoming = connection.execute(
        "MATCH (a:Node {course: '%s'})-[r:RELATES {course: '%s'}]->(b:Node {course: '%s', nodeName: '%s'}) "
        "RETURN a.nodeName, b.nodeName, r.relation, r.course;"
        % (escaped_course, escaped_course, escaped_course, escaped_center)
    )
    edges: list[tuple[str, str, str, str]] = []
    for row in _rows(outgoing) + _rows(incoming):
        if len(row) < 4:
            continue
        n1 = _normalize(str(row[0]))
        n2 = _normalize(str(row[1]))
        rel = _normalize(str(row[2]))
        rel_course = _normalize(str(row[3])) or course
        if not n1 or not n2 or not rel:
            continue
        edges.append((n1, n2, rel, rel_course))
    return edges


def get_relation(nodeName: str, course: str, k: int) -> list[GraphNode]:
    global _LAST_ERROR
    center = _normalize(nodeName)
    clean_course = _normalize(course)
    try:
        hops = int(k)
    except Exception:
        hops = 0
    if not center or not clean_course or hops <= 0:
        return []
    try:
        connection = _get_connection()
    except Exception as error:
        _LAST_ERROR = str(error)
        return []

    visited_nodes: set[str] = {center}
    frontier: set[str] = {center}
    relation_set: set[tuple[str, str, str, str]] = set()
    for _ in range(hops):
        if not frontier:
            break
        next_frontier: set[str] = set()
        for current in frontier:
            for edge in _get_one_hop_edges(connection, current, clean_course):
                relation_set.add(edge)
                n1, n2, _, _ = edge
                if n1 not in visited_nodes:
                    next_frontier.add(n1)
                if n2 not in visited_nodes:
                    next_frontier.add(n2)
        visited_nodes.update(next_frontier)
        frontier = next_frontier

    result: list[GraphNode] = []
    for node1_value, node2_value, relation_value, course_value in sorted(relation_set):
        result.append(
            _to_graph_node(
                course=course_value or clean_course,
                node1=node1_value,
                node2=node2_value,
                relation=relation_value,
            )
        )
    _LAST_ERROR = ""
    return result
