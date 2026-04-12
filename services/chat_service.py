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
from repositories.answer_repository import add_answer_history
from repositories.card_repository import get_card_list
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
    if result.get("type") == "questions":
        return "已为你推荐5道习题，请在右侧功能卡片查看并作答。"
    if result.get("type") == "graph":
        return str(result.get("brief_text", "") or result.get("summary", "") or "已为你生成知识图谱功能卡片。").strip()
    ui_type = str(result.get("ui_type", "") or "").strip()
    if ui_type:
        body = result.get("payload") or {}
        if isinstance(body, dict):
            return str(body.get("brief_text", "") or "").strip()
    return ""


def get_course_list() -> list[str]:
    return fetch_course_list()


def get_windows_by_user(user_id: str) -> list[dict]:
    return get_window_history(user_id)


def _parse_card_json(raw_json: str):
    text = str(raw_json or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    if isinstance(parsed, list):
        return {
            "type": "questions",
            "title": "习题推荐",
            "summary": "点击开始作答",
            "content": parsed,
        }
    if isinstance(parsed, dict):
        return parsed
    return {}


def get_history_by_window(window_id: str) -> dict:
    cards = get_card_list(window_id)
    feature_cards = []
    for card in cards:
        parsed = _parse_card_json(card.json)
        card_type = str(parsed.get("type", "") or "").strip() if isinstance(parsed, dict) else ""
        card_title = str(parsed.get("title", "") or "").strip() if isinstance(parsed, dict) else ""
        card_summary = str(parsed.get("summary", "") or "").strip() if isinstance(parsed, dict) else ""
        card_content = parsed.get("content") if isinstance(parsed, dict) else []
        if not card_type:
            card_type = "questions"
        if not card_title:
            card_title = "习题推荐" if card_type == "questions" else "知识图谱"
        if not card_summary:
            card_summary = "点击查看详情"
        feature_cards.append(
            {
                "id": card.id,
                "title": card_title,
                "type": card_type,
                "content": card_content if isinstance(card_content, list) else [],
                "summary": card_summary,
                "focus_node": str(parsed.get("focus_node", "") or "").strip() if isinstance(parsed, dict) else "",
                "query_text": str(parsed.get("query_text", "") or "").strip() if isinstance(parsed, dict) else "",
                "no": card.no,
            }
        )
    return {
        "messages": get_chat_history(window_id),
        "featureCards": feature_cards,
    }


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


def add_answer_history_for_user(user_id: str, question_id: int, is_correct: bool):
    return add_answer_history(user_id, question_id, is_correct)


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
            yield (
                "data: "
                + json.dumps({"type": "error", "content": error_text}, ensure_ascii=False)
                + "\n\n"
            )

    return generate()
