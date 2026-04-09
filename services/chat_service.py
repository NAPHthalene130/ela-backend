import json

from agent import run_agent_stream
from repositories.chat_repository import (
    create_chat_window,
    delete_user_chat_window,
    get_chat_history,
    get_window_history,
    is_window_owned_by_user,
    save_chat_message,
)
from repositories.course_repository import get_course_list as fetch_course_list


def _encode_stream_event(event_type: str, data: str) -> str:
    if event_type == "done":
        return "data: [DONE]\n\n"
    payload = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _parse_sse_payload(raw_block: str) -> dict:
    if not raw_block:
        return {}
    data_lines = []
    for line in raw_block.splitlines():
        if line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if not data_lines:
        return {}
    raw_data = "\n".join(data_lines)
    if raw_data == "[DONE]":
        return {"type": "done", "content": ""}
    try:
        return json.loads(raw_data)
    except Exception:
        return {}


def _extract_assistant_text(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    if payload.get("type") == "text":
        return str(payload.get("content", "") or "").strip()
    if payload.get("type") != "json":
        return ""
    result = payload.get("result") or {}
    if not isinstance(result, dict):
        return ""
    ui_type = str(result.get("ui_type", "") or "").strip()
    body = result.get("payload") or {}
    if not isinstance(body, dict):
        return ""
    if ui_type in (
        "exercise_recommendation_card",
        "knowledge_graph_card",
        "learning_review_card",
    ):
        return str(body.get("brief_text", "") or "").strip()
    return ""


def get_course_list() -> list[str]:
    return fetch_course_list()


def get_windows_by_user(user_id: str) -> list[dict]:
    return get_window_history(user_id)


def get_history_by_window(window_id: str) -> list[dict]:
    return get_chat_history(window_id)


def create_window_for_user(user_id: str) -> str | None:
    return create_chat_window(user_id)


def save_message(window_id: str, content: str, is_user_send: bool) -> bool:
    return save_chat_message(window_id, content, is_user_send)


def delete_window_for_user(user_id: str, window_id: str):
    """删除用户会话前先校验归属关系。"""
    if not is_window_owned_by_user(user_id, window_id):
        return False, 404, "Window not found"
    success = delete_user_chat_window(window_id)
    if not success:
        return False, 500, "Failed to delete window"
    return True, 200, "Window deleted"


def stream_chat_response(user_id: str, chat_window_id: str, message: str, course: str = ""):
    """执行流式聊天并在流结束后落库完整回复。"""
    save_chat_message(chat_window_id, message, True)

    def generate():
        full_content_parts = []
        try:
            for event in run_agent_stream(
                msg=message,
                user_id=user_id,
                chat_window_id=chat_window_id,
                course=course or "",
            ):
                if isinstance(event, str):
                    parsed_payload = _parse_sse_payload(event)
                    assistant_text = _extract_assistant_text(parsed_payload)
                    if assistant_text:
                        full_content_parts.append(assistant_text)
                    yield event
                    continue

                event_type = event.get("type", "content")
                event_data = event.get("data", "")
                if event_type == "content" and event_data:
                    full_content_parts.append(event_data)
                yield _encode_stream_event(event_type, event_data)

            full_content = "".join(full_content_parts).strip()
            if not full_content:
                full_content = "我已经收到你的问题，但暂时没有生成有效回复，请稍后重试。"
            save_chat_message(chat_window_id, full_content, False)
        except Exception as exc:
            error_text = f"[System Error: {exc}]"
            yield _encode_stream_event("error", error_text)

    return generate()
