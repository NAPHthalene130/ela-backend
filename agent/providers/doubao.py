import os
from pathlib import Path

from openai import OpenAI

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _load_runtime_config():
    try:
        from project_config import API_KEY, BASE_URL
        try:
            from project_config import Lite_Model, Pro_Model
        except ImportError:
            try:
                from project_config import MODEL
                Lite_Model = MODEL
                Pro_Model = MODEL
            except ImportError:
                Lite_Model = None
                Pro_Model = None
        return {
            "api_key": API_KEY,
            "base_url": BASE_URL,
            "lite_model": Lite_Model,
            "pro_model": Pro_Model,
        }
    except ImportError:
        api_key = os.getenv("ELA_LLM_API_KEY")
        base_url = os.getenv("ELA_LLM_BASE_URL")
        lite_model = os.getenv("ELA_LLM_LITE_MODEL") or os.getenv("ELA_LLM_MODEL")
        pro_model = os.getenv("ELA_LLM_PRO_MODEL") or os.getenv("ELA_LLM_MODEL")
        if not api_key or not base_url or not (lite_model or pro_model):
            return None
        return {
            "api_key": api_key,
            "base_url": base_url,
            "lite_model": lite_model or pro_model,
            "pro_model": pro_model or lite_model,
        }


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


def call_chat_once(
    messages: list[dict],
    model_level: str = "lite",
    temperature: float = 0,
    max_tokens: int = 512,
) -> str:
    config = _load_runtime_config()
    if not config:
        return ""
    model = config["lite_model"] if model_level == "lite" else config["pro_model"]
    if not model:
        return ""
    try:
        client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        return (getattr(message, "content", "") or "").strip()
    except Exception:
        return ""


def create_langchain_chat_model(
    model_level: str = "pro",
    streaming: bool = True,
    temperature: float = 0,
    enable_reasoning: bool = False,
):
    config = _load_runtime_config()
    if not config:
        raise RuntimeError("缺少大模型配置，请提供 project_config.py 或环境变量。")
    model = config["lite_model"] if model_level == "lite" else config["pro_model"]
    if not model:
        raise RuntimeError("未找到可用模型配置。")
    try:
        from langchain_openai import ChatOpenAI
    except Exception:
        try:
            from langchain_community.chat_models import ChatOpenAI
        except Exception as exc:
            raise RuntimeError("缺少 LangChain ChatOpenAI 依赖。") from exc
    base_kwargs = {
        "temperature": temperature,
        "streaming": streaming,
    }
    reasoning_kwargs = {}
    if enable_reasoning:
        reasoning_kwargs = {
            "extra_body": {
                "thinking": {"type": "enabled"},
            }
        }
    constructor_candidates = [
        {
            **base_kwargs,
            **reasoning_kwargs,
            "model": model,
            "api_key": config["api_key"],
            "base_url": config["base_url"],
        },
        {
            **base_kwargs,
            **reasoning_kwargs,
            "model_name": model,
            "openai_api_key": config["api_key"],
            "openai_api_base": config["base_url"],
        },
        {
            **base_kwargs,
            "model": model,
            "api_key": config["api_key"],
            "base_url": config["base_url"],
        },
        {
            **base_kwargs,
            "model_name": model,
            "openai_api_key": config["api_key"],
            "openai_api_base": config["base_url"],
        },
    ]
    last_error = None
    for kwargs in constructor_candidates:
        try:
            return ChatOpenAI(**kwargs)
        except TypeError as exc:
            last_error = exc
            continue
    raise RuntimeError("ChatOpenAI 初始化失败。") from last_error


def auth_gate(msg: str) -> bool:
    content = (msg or "").strip()
    if not content:
        return False
    config = _load_runtime_config()
    if not config or not config.get("lite_model"):
        return False
    client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])
    policy_prompt = render_prompt("auth_gate_prompt.txt", {"msg": content})
    try:
        resp = client.chat.completions.create(
            model=config["lite_model"],
            messages=[
                {"role": "system", "content": policy_prompt},
                {"role": "user", "content": content},
            ],
            temperature=0,
            max_tokens=8,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
        text = ""
        choices = getattr(resp, "choices", None) or []
        if choices:
            message = getattr(choices[0], "message", None)
            text = (getattr(message, "content", "") or "").strip().upper()
        return text.startswith("PASS")
    except Exception:
        return False
