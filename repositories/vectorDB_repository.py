import os
import json
import time
import traceback
import urllib.error
import urllib.request
from typing import Any

from database.vectorDB import DEFAULT_VECTOR_DIM, get_question_brief_vector_db


def _load_embedding_config() -> tuple[str, str, str]:
    try:
        from project_config import API_KEY, EMBEDDING_URL, Embedding_Model

        return API_KEY, EMBEDDING_URL, Embedding_Model
    except ImportError:
        api_key = os.getenv("ELA_LLM_API_KEY")
        base_url = os.getenv("ELA_LLM_BASE_URL")
        embedding_model = os.getenv("ELA_LLM_EMBEDDING_MODEL")
        if api_key and base_url and embedding_model:
            return api_key, base_url, embedding_model
        raise RuntimeError("缺少Embedding模型配置，请提供 project_config.py 或环境变量。")


def _normalize_base_url(url: str) -> str:
    clean_url = (url or "").strip().rstrip("/")
    for suffix in ("/embeddings/multimodal", "/embeddings"):
        if clean_url.endswith(suffix):
            return clean_url[: -len(suffix)]
    return clean_url


def _resolve_embedding_base_urls(primary_url: str) -> list[str]:
    candidates: list[str] = []
    primary = (primary_url or "").strip().rstrip("/")
    if primary:
        if primary.endswith("/embeddings/multimodal"):
            candidates.append(primary)
        else:
            candidates.append(f"{_normalize_base_url(primary)}/embeddings/multimodal")
    try:
        from project_config import BASE_URL

        normalized_llm = _normalize_base_url(BASE_URL)
        if normalized_llm:
            candidates.append(f"{normalized_llm}/embeddings/multimodal")
    except ImportError:
        pass
    env_base_url = _normalize_base_url(os.getenv("ELA_LLM_BASE_URL", ""))
    if env_base_url:
        candidates.append(f"{env_base_url}/embeddings/multimodal")
    env_embedding_url = (os.getenv("ELA_LLM_EMBEDDING_URL", "") or "").strip().rstrip("/")
    if env_embedding_url:
        if env_embedding_url.endswith("/embeddings/multimodal"):
            candidates.append(env_embedding_url)
        else:
            candidates.append(f"{_normalize_base_url(env_embedding_url)}/embeddings/multimodal")
    seen: set[str] = set()
    output: list[str] = []
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _normalize_vector_dim(vector: list[float], dim: int) -> list[float]:
    if len(vector) == dim:
        return vector
    if len(vector) > dim:
        return vector[:dim]
    return vector + [0.0] * (dim - len(vector))


def _normalize_course(value: str) -> str:
    return (value or "").strip()


def _normalize_type(value: str) -> str:
    return (value or "").strip().lower()


def _get_embedding_vector(text: str) -> list[float]:
    api_key, embedding_url, model = _load_embedding_config()
    candidate_urls = _resolve_embedding_base_urls(embedding_url)
    if not candidate_urls:
        candidate_urls = [embedding_url]
    last_error: Exception | None = None
    payload = {
        "model": model,
        "instructions": "Target_modality: text and video.\nInstruction:Compress the text/video into one word.\nQuery:",
        "dimensions": 2048,
        "multi_embedding": {"type": "enabled"},
        "sparse_embedding": {"type": "enabled"},
        "encoding_format": "float",
        "input": [{"type": "text", "text": text or ""}],
    }
    request_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    for current_url in candidate_urls:
        sleep_seconds = 0.5
        for _ in range(3):
            try:
                request = urllib.request.Request(
                    url=current_url,
                    data=request_body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    response_text = response.read().decode("utf-8")
                response_json = json.loads(response_text)
                data = response_json.get("data")
                vector: list[float] | None = None
                if isinstance(data, dict):
                    embedded = data.get("embedding")
                    if isinstance(embedded, list):
                        vector = [float(item) for item in embedded]
                elif isinstance(data, list) and data:
                    first = data[0]
                    if isinstance(first, dict) and isinstance(first.get("embedding"), list):
                        vector = [float(item) for item in first["embedding"]]
                if vector is None:
                    raise RuntimeError("Embedding响应中未找到embedding字段")
                return _normalize_vector_dim([float(item) for item in vector], DEFAULT_VECTOR_DIM)
            except Exception as error:
                last_error = error
                time.sleep(sleep_seconds)
                sleep_seconds *= 2
    if last_error is not None:
        raise last_error
    raise RuntimeError("Embedding调用失败")


def add_question(id: int, brief: str, course: str, type: str) -> bool:
    try:
        clean_course = _normalize_course(course)
        clean_type = _normalize_type(type)
        try:
            print(f"尝试添加:ID: {id} BREIF: {brief} COURSE: {course} TYPE: {type}".encode('utf-8', 'ignore').decode('utf-8', 'ignore'))
        except Exception:
            pass
        vector_db = get_question_brief_vector_db()
        embedding = _get_embedding_vector(brief or "")
        vector_db.upsert(
            id=id,
            brief=brief or "",
            course=clean_course,
            type=clean_type,
            brief_vector=embedding,
        )

        try:
            print(
                "UPSERTED: id: {}, course: {}, brief: {}, type: {}".format(
                    id,
                    clean_course,
                    brief,
                    clean_type,
                ).encode('utf-8', 'ignore').decode('utf-8', 'ignore')
            )
        except Exception:
            pass
        return True
    except Exception:
        print(traceback.format_exc())
        return False


def delete_question(id: int) -> bool:
    try:
        vector_db = get_question_brief_vector_db()
        vector_db.delete(id=id)
        return True
    except Exception:
        return False


def filter_existing_question_ids(question_ids: list[int]) -> list[int]:
    unique_ids: list[int] = []
    seen: set[int] = set()
    for item in question_ids or []:
        try:
            question_id = int(item)
        except Exception:
            continue
        if question_id <= 0 or question_id in seen:
            continue
        seen.add(question_id)
        unique_ids.append(question_id)
    if not unique_ids:
        return []
    try:
        vector_db = get_question_brief_vector_db()
        result = vector_db.collection.get(ids=[str(item) for item in unique_ids], include=[])
        rows = result.get("ids") if isinstance(result, dict) else []
        existing_ids = {int(item) for item in rows or []}
        return [item for item in unique_ids if item in existing_ids]
    except Exception:
        return []


def _extract_hit_id(hit: Any) -> int | None:
    if isinstance(hit, dict):
        if "id" in hit:
            try:
                return int(hit["id"])
            except Exception:
                return None
        entity = hit.get("entity")
        if isinstance(entity, dict) and "id" in entity:
            try:
                return int(entity["id"])
            except Exception:
                return None
    return None


def search_question_topK(myBrief: str, course: str, type: str, k: int) -> list[int]:
    try:
        limit = max(1, int(k))
    except Exception:
        limit = 1
    try:
        print(f"[SEARCH] myBrief: {myBrief}, course: {course}, type: {type}, limit: {limit}")
        vector_db = get_question_brief_vector_db()
        embedding = _get_embedding_vector(myBrief or "")
        clean_course = _normalize_course(course)
        clean_type = _normalize_type(type)
        hits = vector_db.search(
            query_vector=embedding,
            limit=limit,
            course=clean_course,
            type=clean_type,
        )
        print(f"[SEARCH] hits: {hits}")
        ids: list[int] = []
        for hit in hits:
            item_id = _extract_hit_id(hit)
            if item_id is not None:
                ids.append(item_id)
        return ids
    except Exception as error:
        if "缺少Embedding模型配置" in str(error):
            return []
        print(traceback.format_exc())
        return []
