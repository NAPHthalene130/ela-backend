import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.app_factory import create_app
from repositories.course_repository import ensure_course_exists
from repositories.questions_set_repository import (
    add_choice_question,
    add_fill_question,
    add_subjective_question,
)
from util.getLlmResponse import getLlmRes


UNCOMPLETED_DIR = Path(__file__).resolve().parent / "uncompleted"
COMPLETED_DIR = Path(__file__).resolve().parent / "completed"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
FORMAT_PROMPT_FILE = PROMPTS_DIR / "format_lite.txt"
BRIEF_PROMPT_FILE = PROMPTS_DIR / "brief_flash.txt"
SOLVE_PROMPT_FILE = PROMPTS_DIR / "solve_pro.txt"
MAX_WORKERS = 16


def normalize_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def parse_question_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def extract_json_object(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
            raw = "\n".join(lines[1:-1]).strip()
    if raw.startswith("json"):
        raw = raw[4:].strip()
    try:
        loaded = json.loads(raw)
        return loaded if isinstance(loaded, dict) else None
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            loaded = json.loads(raw[start : end + 1])
            return loaded if isinstance(loaded, dict) else None
        except Exception:
            return None
    return None


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def render_prompt(template: str, msg: str) -> str:
    return template.replace("{{msg}}", msg)


def clamp_text(value: Any, limit: int) -> str:
    text = normalize_text(value)
    if len(text) <= limit:
        return text
    return text[:limit]


def normalize_question_item(item: dict[str, Any]) -> dict[str, Any]:
    question_type = normalize_text(item.get("type")).lower()
    normalized = {
        "type": question_type,
        "course": clamp_text(item.get("course"), 1024),
        "content": clamp_text(item.get("content"), 1024),
        "optionA": clamp_text(item.get("optionA"), 1024),
        "optionB": clamp_text(item.get("optionB"), 1024),
        "optionC": clamp_text(item.get("optionC"), 1024),
        "optionD": clamp_text(item.get("optionD"), 1024),
        "answer": clamp_text(item.get("answer"), 1024),
        "brief": clamp_text(item.get("brief"), 1024),
        "explanation": clamp_text(item.get("explanation"), 4096),
    }
    if question_type == "choice":
        normalized["answer"] = clamp_text(item.get("answer"), 16)
    return normalized


def format_question_with_lite(
    item: dict[str, Any], format_prompt_template: str
) -> dict[str, Any]:
    fallback = normalize_question_item(item)
    input_msg = json.dumps(item, ensure_ascii=False)
    prompt = render_prompt(format_prompt_template, input_msg)
    try:
        llm_text = getLlmRes(msg="", prompt=prompt, model_tier="lite")
        parsed = extract_json_object(llm_text)
        if not parsed:
            return fallback
        merged = {**item, **parsed}
        return normalize_question_item(merged)
    except Exception:
        return fallback


def enrich_brief_with_flash(
    item: dict[str, Any], brief_prompt_template: str
) -> dict[str, Any]:
    prompt = render_prompt(brief_prompt_template, json.dumps(item, ensure_ascii=False))
    try:
        llm_text = getLlmRes(msg="", prompt=prompt, model_tier="flash")
        parsed = extract_json_object(llm_text)
        if parsed:
            brief = clamp_text(parsed.get("brief"), 1024)
        else:
            brief = clamp_text(llm_text, 1024)
        if brief:
            item["brief"] = brief
    except Exception:
        pass
    return item


def solve_with_pro(item: dict[str, Any], solve_prompt_template: str) -> dict[str, Any]:
    prompt = render_prompt(solve_prompt_template, json.dumps(item, ensure_ascii=False))
    try:
        llm_text = getLlmRes(msg="", prompt=prompt, model_tier="pro")
        parsed = extract_json_object(llm_text)
        if parsed:
            if normalize_text(parsed.get("answer")):
                if normalize_text(item.get("type")) == "choice":
                    item["answer"] = clamp_text(parsed.get("answer"), 16)
                else:
                    item["answer"] = clamp_text(parsed.get("answer"), 1024)
            if normalize_text(parsed.get("explanation")):
                item["explanation"] = clamp_text(parsed.get("explanation"), 4096)
        elif llm_text.strip():
            item["explanation"] = clamp_text(llm_text, 4096)
    except Exception:
        pass
    return item


def process_question_pipeline(
    item: dict[str, Any],
    format_prompt_template: str,
    brief_prompt_template: str,
    solve_prompt_template: str,
) -> dict[str, Any]:
    formatted = format_question_with_lite(item, format_prompt_template)
    with_brief = enrich_brief_with_flash(formatted, brief_prompt_template)
    solved = solve_with_pro(with_brief, solve_prompt_template)
    return normalize_question_item(solved)


def import_question_item(item: dict[str, Any]) -> bool:
    question_type = normalize_text(item.get("type")).lower()
    course = clamp_text(item.get("course"), 1024)
    content = clamp_text(item.get("content"), 1024)
    answer = clamp_text(item.get("answer"), 16 if question_type == "choice" else 1024)
    brief = clamp_text(item.get("brief"), 1024)
    explanation = clamp_text(item.get("explanation"), 4096)

    if not question_type or not content:
        return False

    if course:
        ensure_course_exists(course)

    if question_type == "choice":
        question_id = add_choice_question(
            course=course,
            content=content,
            optionA=clamp_text(item.get("optionA"), 1024),
            optionB=clamp_text(item.get("optionB"), 1024),
            optionC=clamp_text(item.get("optionC"), 1024),
            optionD=clamp_text(item.get("optionD"), 1024),
            answer=answer,
            brief=brief,
            explanation=explanation,
        )
        return question_id is not None

    if question_type == "fill":
        question_id = add_fill_question(
            course=course,
            content=content,
            answer=answer,
            brief=brief,
            explanation=explanation,
        )
        return question_id is not None

    if question_type == "subjective":
        question_id = add_subjective_question(
            course=course,
            content=content,
            answer=answer,
            brief=brief,
            explanation=explanation,
        )
        return question_id is not None

    return False


def available_destination(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def move_to_completed(file_path: Path) -> None:
    relative_path = file_path.relative_to(UNCOMPLETED_DIR)
    target_path = COMPLETED_DIR / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    final_target_path = available_destination(target_path)
    shutil.move(str(file_path), str(final_target_path))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_completed_items(
    source_file: Path,
    completed_items: list[dict[str, Any]],
) -> None:
    if not completed_items:
        return
    relative_path = source_file.relative_to(UNCOMPLETED_DIR)
    target_path = COMPLETED_DIR / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    final_target_path = available_destination(target_path)
    write_json(final_target_path, completed_items)


def remove_empty_directories(root: Path) -> None:
    if not root.exists():
        return
    for directory in sorted(
        (item for item in root.rglob("*") if item.is_dir()),
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        if not any(directory.iterdir()):
            directory.rmdir()


def import_file(
    json_file: Path,
) -> tuple[Any, list[dict[str, Any]], bool]:
    try:
        payload = json.loads(json_file.read_text(encoding="utf-8"))
    except Exception:
        return None, [], False
    items = parse_question_items(payload)
    return payload, items, isinstance(payload, list)


def run_import() -> dict[str, int]:
    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
    if not UNCOMPLETED_DIR.exists():
        return {
            "files_total": 0,
            "files_success": 0,
            "questions_success": 0,
            "questions_total": 0,
        }
    for required_file in (FORMAT_PROMPT_FILE, BRIEF_PROMPT_FILE, SOLVE_PROMPT_FILE):
        if not required_file.exists():
            return {
                "files_total": 0,
                "files_success": 0,
                "questions_success": 0,
                "questions_total": 0,
            }

    format_prompt_template = load_prompt(FORMAT_PROMPT_FILE)
    brief_prompt_template = load_prompt(BRIEF_PROMPT_FILE)
    solve_prompt_template = load_prompt(SOLVE_PROMPT_FILE)

    json_files = sorted(path for path in UNCOMPLETED_DIR.rglob("*.json") if path.is_file())
    file_items_map: dict[Path, tuple[Any, list[dict[str, Any]], bool]] = {
        json_file: import_file(json_file) for json_file in json_files
    }
    processed_file_items_map: dict[Path, list[dict[str, Any] | None]] = {
        json_file: [None] * len(file_data[1]) for json_file, file_data in file_items_map.items()
    }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {}
        for json_file, (_, items, _) in file_items_map.items():
            for index, item in enumerate(items):
                future = executor.submit(
                    process_question_pipeline,
                    item,
                    format_prompt_template,
                    brief_prompt_template,
                    solve_prompt_template,
                )
                future_map[future] = (json_file, index, item)
        for future in as_completed(future_map):
            json_file, index, raw_item = future_map[future]
            try:
                processed_file_items_map[json_file][index] = future.result()
                print(
                    f"[线程完成] {json_file.name} 第{index + 1}题 LLM处理成功",
                    flush=True,
                )
            except Exception:
                processed_file_items_map[json_file][index] = normalize_question_item(raw_item)
                print(
                    f"[线程完成] {json_file.name} 第{index + 1}题 LLM处理失败，已使用回退数据",
                    flush=True,
                )

    files_success = 0
    questions_success = 0
    questions_total = 0

    for json_file in json_files:
        _, source_items, source_is_list = file_items_map.get(json_file, (None, [], False))
        processed_items = processed_file_items_map.get(json_file, [])
        imported_count = 0
        completed_items: list[dict[str, Any]] = []
        failed_items: list[dict[str, Any]] = []
        for item in processed_items:
            if not isinstance(item, dict):
                continue
            if import_question_item(item):
                imported_count += 1
                completed_items.append(item)
            else:
                failed_items.append(item)
        total_count = len(processed_items)
        file_success = total_count > 0 and imported_count > 0 and not failed_items
        if source_is_list:
            if completed_items:
                save_completed_items(json_file, completed_items)
            if failed_items:
                write_json(json_file, failed_items)
            elif json_file.exists():
                json_file.unlink()
        elif file_success and total_count == 1 and len(source_items) == 1:
            move_to_completed(json_file)
        questions_success += imported_count
        questions_total += total_count
        if file_success:
            files_success += 1

    remove_empty_directories(UNCOMPLETED_DIR)

    return {
        "files_total": len(json_files),
        "files_success": files_success,
        "questions_success": questions_success,
        "questions_total": questions_total,
    }


def main() -> None:
    app = create_app()
    with app.app_context():
        result = run_import()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
