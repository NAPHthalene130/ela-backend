import json

from llm.graph.workflow import run_agentic_stream


def run_agent_stream(
    msg: str, user_id: str = "", chat_window_id: str = "", course: str = ""
):
    yield from run_agentic_stream(
        msg=msg,
        user_id=user_id,
        chat_window_id=chat_window_id,
        course=course,
    )


def run_agent(msg: str, user_id: str = "", chat_window_id: str = "", course: str = "") -> str:
    all_parts = []
    for event in run_agent_stream(msg, user_id, chat_window_id, course):
        if isinstance(event, str):
            for line in event.splitlines():
                if not line.startswith("data:"):
                    continue
                raw_data = line[5:].strip()
                if raw_data == "[DONE]":
                    continue
                try:
                    parsed = json.loads(raw_data)
                except Exception:
                    continue
                if parsed.get("type") == "text":
                    all_parts.append(parsed.get("content", ""))
            continue
        if event.get("type") == "content":
            all_parts.append(event.get("data", ""))
    return "".join(all_parts)
