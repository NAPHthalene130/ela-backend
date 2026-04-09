import os


def _load_neo4j_config() -> dict:
    uri = os.getenv("ELA_NEO4J_URI", "")
    username = os.getenv("ELA_NEO4J_USERNAME", "")
    password = os.getenv("ELA_NEO4J_PASSWORD", "")
    database = os.getenv("ELA_NEO4J_DATABASE", "")

    try:
        from project_config import (
            NEO4J_DATABASE,
            NEO4J_PASSWORD,
            NEO4J_URI,
            NEO4J_USERNAME,
        )

        uri = NEO4J_URI or uri
        username = NEO4J_USERNAME or username
        password = NEO4J_PASSWORD or password
        database = NEO4J_DATABASE or database
    except ImportError:
        pass
    except Exception:
        pass

    return {
        "uri": uri,
        "username": username,
        "password": password,
        "database": database,
    }


def query_knowledge_graph(query_text: str, course: str = "", limit: int = 20) -> dict:
    try:
        from langchain_neo4j import Neo4jGraph
    except Exception:
        return {
            "ok": False,
            "reason": "missing_dependency",
            "nodes": [],
            "edges": [],
            "source": "neo4j",
        }

    config = _load_neo4j_config()
    if not config["uri"] or not config["username"] or not config["password"]:
        return {
            "ok": False,
            "reason": "missing_config",
            "nodes": [],
            "edges": [],
            "source": "neo4j",
        }

    keyword = (query_text or "").strip()
    safe_limit = max(1, min(int(limit or 20), 50))
    edge_limit = safe_limit * 2
    try:
        graph = Neo4jGraph(
            url=config["uri"],
            username=config["username"],
            password=config["password"],
            database=config["database"] or None,
        )
        node_rows = graph.query(
            """
            MATCH (n)
            WHERE (
                $keyword = ''
                OR toLower(coalesce(n.name, '')) CONTAINS toLower($keyword)
                OR toLower(coalesce(n.title, '')) CONTAINS toLower($keyword)
                OR toLower(coalesce(n.keyword, '')) CONTAINS toLower($keyword)
            )
            AND (
                $course = ''
                OR toLower(coalesce(n.course, '')) = toLower($course)
                OR toLower(coalesce(n.subject, '')) = toLower($course)
            )
            RETURN
                elementId(n) AS node_id,
                coalesce(n.name, n.title, n.keyword, toString(id(n))) AS label,
                labels(n) AS labels
            LIMIT $node_limit
            """,
            params={
                "keyword": keyword,
                "course": (course or "").strip(),
                "node_limit": safe_limit,
            },
        )

        nodes = []
        node_ids = []
        for row in node_rows or []:
            node_id = str(row.get("node_id", "")).strip()
            if not node_id:
                continue
            node_ids.append(node_id)
            labels = row.get("labels") or []
            nodes.append(
                {
                    "id": node_id,
                    "label": str(row.get("label", node_id)),
                    "type": labels[0] if labels else "Node",
                }
            )

        edges = []
        if node_ids:
            edge_rows = graph.query(
                """
                MATCH (n)-[r]-(m)
                WHERE elementId(n) IN $node_ids AND elementId(m) IN $node_ids
                RETURN
                    elementId(n) AS source,
                    type(r) AS rel,
                    elementId(m) AS target
                LIMIT $edge_limit
                """,
                params={
                    "node_ids": node_ids,
                    "edge_limit": edge_limit,
                },
            )
            edges = [
                {
                    "source": str(row.get("source", "")),
                    "target": str(row.get("target", "")),
                    "label": str(row.get("rel", "关联")),
                }
                for row in (edge_rows or [])
                if row.get("source") and row.get("target")
            ]

        return {
            "ok": True,
            "reason": "",
            "nodes": nodes,
            "edges": edges,
            "source": "neo4j",
        }
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"query_error:{exc}",
            "nodes": [],
            "edges": [],
            "source": "neo4j",
        }
