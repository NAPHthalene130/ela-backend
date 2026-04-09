import json


def normalize_stream_event(payload) -> dict:
    if isinstance(payload, dict):
        return payload
    return {"type": "text", "content": str(payload or "")}


def _serialize_sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def extract_chunk_text(chunk) -> str:
    if chunk is None:
        return ""
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            text = getattr(item, "text", None)
            if text:
                parts.append(str(text))
                continue
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
        return "".join(parts)
    return str(content or "")


def generate_text_stream(chain, payload: dict):
    try:
        for chunk in chain.stream(payload):
            text = extract_chunk_text(chunk)
            if text:
                yield _serialize_sse_event({"type": "text", "content": text})
    except Exception as exc:
        yield _serialize_sse_event({"type": "error", "content": str(exc)})
    yield "data: [DONE]\n\n"


def generate_json_packet(mode: str, result: dict):
    yield _serialize_sse_event(
        {
            "type": "json",
            "mode": mode,
            "result": result,
        }
    )
    yield "data: [DONE]\n\n"
