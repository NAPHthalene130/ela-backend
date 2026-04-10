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


def extract_chunk_reasoning(chunk) -> str:
    if chunk is None:
        return ""
    reasoning_parts = []
    content = getattr(chunk, "content", None)
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") in ("reasoning", "thinking"):
                    reasoning_parts.append(str(item.get("text", "") or item.get("content", "")))
                if item.get("reasoning_content"):
                    reasoning_parts.append(str(item.get("reasoning_content", "")))
            else:
                text = getattr(item, "reasoning_content", None)
                if text:
                    reasoning_parts.append(str(text))
    additional_kwargs = getattr(chunk, "additional_kwargs", None)
    if isinstance(additional_kwargs, dict):
        if additional_kwargs.get("reasoning_content"):
            reasoning_parts.append(str(additional_kwargs.get("reasoning_content", "")))
        delta = additional_kwargs.get("delta")
        if isinstance(delta, dict) and delta.get("reasoning_content"):
            reasoning_parts.append(str(delta.get("reasoning_content", "")))
    response_metadata = getattr(chunk, "response_metadata", None)
    if isinstance(response_metadata, dict):
        if response_metadata.get("reasoning_content"):
            reasoning_parts.append(str(response_metadata.get("reasoning_content", "")))
    return "".join(reasoning_parts)


def generate_text_stream(chain, payload: dict, emit_done: bool = True):
    try:
        for chunk in chain.stream(payload):
            reasoning = extract_chunk_reasoning(chunk)
            if reasoning:
                yield _serialize_sse_event({"type": "reasoning", "data": reasoning})
            text = extract_chunk_text(chunk)
            if text:
                yield _serialize_sse_event({"type": "text", "content": text})
    except Exception as exc:
        yield _serialize_sse_event({"type": "error", "content": str(exc)})
    if emit_done:
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
