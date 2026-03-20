from openai import OpenAI


def _build_messages(msg: str, prompt: str) -> list[dict[str, str]]:
    prompt_text = (prompt or "").strip()
    msg_text = (msg or "").strip()
    if prompt_text and msg_text:
        return [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": msg_text},
        ]
    if prompt_text:
        return [{"role": "user", "content": prompt_text}]
    if msg_text:
        return [{"role": "user", "content": msg_text}]
    return [{"role": "user", "content": ""}]


def _extract_text_from_chat_response(response) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""
    message = getattr(choices[0], "message", None)
    if not message:
        return ""
    content = getattr(message, "content", "")
    return content or ""


def _load_llm_config():
    try:
        from project_config import API_KEY, BASE_URL, MODEL

        return API_KEY, BASE_URL, MODEL
    except ImportError:
        import os

        api_key = os.getenv("ELA_LLM_API_KEY")
        base_url = os.getenv("ELA_LLM_BASE_URL")
        model = os.getenv("ELA_LLM_MODEL")
        if api_key and base_url and model:
            return api_key, base_url, model
        raise RuntimeError("缺少大模型配置，请提供 project_config.py 或环境变量。")


def getLlmRes(msg: str, prompt: str) -> str:
    api_key, base_url, model = _load_llm_config()
    client = OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=_build_messages(msg, prompt),
    )
    return _extract_text_from_chat_response(response)
