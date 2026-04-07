from pathlib import Path

from openai import OpenAI


PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load_llm_config():
    try:
        from project_config import API_KEY, BASE_URL, Pro_Model

        return API_KEY, BASE_URL, Pro_Model
    except ImportError:
        import os

        api_key = os.getenv("ELA_LLM_API_KEY")
        base_url = os.getenv("ELA_LLM_BASE_URL")
        pro_model = os.getenv("ELA_LLM_PRO_MODEL") or os.getenv("ELA_LLM_MODEL")
        if api_key and base_url and pro_model:
            return api_key, base_url, pro_model
        raise RuntimeError("缺少大模型配置，请提供 project_config.py 或环境变量。")


def _read_prompt_template(template_name: str) -> str:
    template_path = PROMPTS_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def render_prompt(template_name: str, variables: dict[str, str]) -> str:
    template = _read_prompt_template(template_name)
    rendered_text = template
    for key, value in (variables or {}).items():
        rendered_text = rendered_text.replace(f"{{{{{key}}}}}", value or "")
    return rendered_text


def get_finally_response(
    msg: str, user_id: str = "", chat_window_id: str = "", course: str = ""
):
    api_key, base_url, pro_model = _load_llm_config()
    client = OpenAI(base_url=base_url, api_key=api_key)
    prompt_text = render_prompt(
        "final_response_prompt.txt",
        {
            "msg": msg or "",
            "user_id": user_id or "",
            "chat_window_id": chat_window_id or "",
            "course": course or "",
        },
    )
    stream = client.chat.completions.create(
        model=pro_model,
        messages=[{"role": "user", "content": prompt_text}],
        stream=True,
    )
    for chunk in stream:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        piece = getattr(delta, "content", "") if delta else ""
        if piece:
            yield piece
