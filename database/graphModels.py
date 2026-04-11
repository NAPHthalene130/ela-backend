from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Node:
    id: str
    course: str
    nodeName: str


@dataclass(slots=True, frozen=True)
class Relation:
    course: str
    node1: str
    node2: str
    relation: str


class KuzuNodeSchema:
    table_name = "Node"
    primary_key = "id"
    columns = ("id", "course", "nodeName")


class KuzuRelationSchema:
    table_name = "RELATES"
    from_table = "Node"
    to_table = "Node"
    columns = ("course", "relation")
