import os
from pathlib import Path
from typing import Any

import chromadb


BACKEND_ROOT = Path(__file__).resolve().parents[1]
CHROMA_DB_PATH = os.getenv(
    "ELA_CHROMA_DB_PATH",
    str(BACKEND_ROOT / "instance" / "chroma_db"),
)
DEFAULT_COLLECTION_NAME = os.getenv(
    "ELA_CHROMA_COLLECTION",
    os.getenv("ELA_MILVUS_COLLECTION", "questionBriefTable"),
)
DEFAULT_VECTOR_DIM = int(
    os.getenv("ELA_CHROMA_VECTOR_DIM", os.getenv("ELA_MILVUS_VECTOR_DIM", "2048"))
)


class QuestionBriefVectorDB:
    def __init__(
        self,
        path: str = CHROMA_DB_PATH,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        vector_dim: int = DEFAULT_VECTOR_DIM,
    ) -> None:
        self.path = path
        self.collection_name = collection_name
        self.vector_dim = vector_dim
        self.client = chromadb.PersistentClient(path=self.path)
        self.collection = None

    def ensure_collection(self) -> None:
        if self.collection is not None:
            return
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(
        self,
        id: int,
        brief: str,
        course: str,
        type: str,
        brief_vector: list[float],
    ) -> dict[str, Any]:
        self.ensure_collection()
        clean_id = str(int(id))
        clean_brief = (brief or "")[:1024]
        clean_course = (course or "").strip()[:1024]
        clean_type = (type or "").strip().lower()[:32]
        clean_vector = [float(item) for item in brief_vector]
        if len(clean_vector) > self.vector_dim:
            clean_vector = clean_vector[: self.vector_dim]
        elif len(clean_vector) < self.vector_dim:
            clean_vector = clean_vector + [0.0] * (self.vector_dim - len(clean_vector))
        self.collection.upsert(
            ids=[clean_id],
            documents=[clean_brief],
            metadatas=[{"course": clean_course, "type": clean_type}],
            embeddings=[clean_vector],
        )
        return {"ids": [clean_id]}

    def delete(self, id: int) -> dict[str, Any]:
        self.ensure_collection()
        clean_id = str(int(id))
        self.collection.delete(ids=[clean_id])
        return {"ids": [clean_id]}

    def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        course: str = "",
        type: str = "",
    ) -> list[dict[str, Any]]:
        self.ensure_collection()
        clean_course = course.replace(chr(34), "").strip() if course else ""
        clean_type = type.replace(chr(34), "").strip().lower() if type else ""
        where: dict[str, Any] | None = None
        if clean_course and clean_type:
            where = {"$and": [{"course": clean_course}, {"type": clean_type}]}
        elif clean_course:
            where = {"course": clean_course}
        elif clean_type:
            where = {"type": clean_type}
        clean_limit = max(1, int(limit))
        clean_vector = [float(item) for item in query_vector]
        if len(clean_vector) > self.vector_dim:
            clean_vector = clean_vector[: self.vector_dim]
        elif len(clean_vector) < self.vector_dim:
            clean_vector = clean_vector + [0.0] * (self.vector_dim - len(clean_vector))
        result = self.collection.query(
            query_embeddings=[clean_vector],
            n_results=clean_limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids_rows = result.get("ids") if isinstance(result, dict) else None
        docs_rows = result.get("documents") if isinstance(result, dict) else None
        metas_rows = result.get("metadatas") if isinstance(result, dict) else None
        if not ids_rows:
            return []
        ids = ids_rows[0] if ids_rows else []
        docs = docs_rows[0] if docs_rows else []
        metas = metas_rows[0] if metas_rows else []
        output: list[dict[str, Any]] = []
        for index, item_id in enumerate(ids):
            meta = metas[index] if index < len(metas) and isinstance(metas[index], dict) else {}
            brief = docs[index] if index < len(docs) else ""
            output.append(
                {
                    "id": int(item_id),
                    "brief": brief or "",
                    "course": (meta.get("course") or "") if isinstance(meta, dict) else "",
                    "type": (meta.get("type") or "") if isinstance(meta, dict) else "",
                }
            )
        return output


def get_question_brief_vector_db() -> QuestionBriefVectorDB:
    db = QuestionBriefVectorDB()
    db.ensure_collection()
    return db


def init_vector_db() -> QuestionBriefVectorDB:
    Path(CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)
    db = QuestionBriefVectorDB()
    db.ensure_collection()
    return db
