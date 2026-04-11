import json
import re
from pathlib import Path

from agent.providers import call_chat_once
from repositories.practice_repository import (
    add_question_to_practice_set,
    create_practice_set,
    delete_practice_set,
    get_practice_set_by_id,
    get_practice_set_questions,
    get_practice_sets_by_student,
    get_public_choice_question_by_id,
    get_public_course_list,
    get_public_custom_question_by_id,
    get_public_fill_question_by_id,
    get_public_question_node_by_id,
    get_public_question_pool_by_course_and_type,
    get_public_question_search_candidates,
    get_public_subjective_question_by_id,
    is_question_in_practice_set,
    normalize_question_type,
    remove_question_from_practice_set,
    update_practice_set_name,
)
from repositories.vectorDB_repository import filter_existing_question_ids, search_question_topK

QUESTION_TYPE_LABELS = {
    "choice": "选择题",
    "fill": "填空题",
    "subjective": "主观题",
    "custom": "自定义题",
}

PROMPT_DIR = Path(__file__).resolve().parents[1] / "localApp" / "questionImport" / "prompts"
PRACTICE_RECOMMEND_PROMPT = PROMPT_DIR / "practice_recommend_lite.txt"


def _normalize_text(value: str) -> str:
    return str(value or "").strip()


def _load_prompt_text(prompt_path: Path) -> str:
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _render_prompt(template: str, payload: dict) -> str:
    if not template:
        return json.dumps(payload, ensure_ascii=False)
    return template.replace("{{msg}}", json.dumps(payload, ensure_ascii=False, indent=2))


def _build_default_brief(course: str, question_type: str, requirement: str) -> str:
    type_label = QUESTION_TYPE_LABELS.get(normalize_question_type(question_type), "习题")
    parts = [item for item in [_normalize_text(course), type_label, _normalize_text(requirement)] if item]
    return " ".join(parts)[:60]


def _extract_json_payload(raw_text: str) -> dict:
    text = _normalize_text(raw_text)
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


def _unique_list(values: list[str], limit: int = 8) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if len(result) >= limit:
            break
    return result


def _serialize_practice_set(practice_set) -> dict:
    question_rows = get_practice_set_questions(practice_set.id)
    return {
        "id": practice_set.id,
        "name": practice_set.name or f"练习题单{practice_set.id}",
        "questionCount": len(question_rows),
    }


def get_practice_courses() -> list[str]:
    return get_public_course_list()


def get_practice_question_pool(course: str, question_type: str) -> list[dict]:
    rows = get_public_question_pool_by_course_and_type(question_type, course)
    return [{"id": question_id, "brief": brief} for question_id, brief in rows]


def get_practice_question_detail(question_id: int, include_answer: bool = False) -> dict | None:
    question_node = get_public_question_node_by_id(question_id)
    if not question_node:
        return None
    question_type = normalize_question_type(question_node.type)
    if not question_type:
        return None
    base_payload = {
        "id": question_node.id,
        "type": question_type,
        "course": question_node.course or "",
        "brief": "",
    }
    if question_type == "choice":
        detail = get_public_choice_question_by_id(question_id)
        if not detail:
            return None
        base_payload.update(
            {
                "brief": detail.brief or "",
                "content": detail.content or "",
                "optionA": detail.optionA or "",
                "optionB": detail.optionB or "",
                "optionC": detail.optionC or "",
                "optionD": detail.optionD or "",
            }
        )
        if include_answer:
            base_payload.update(
                {
                    "answer": detail.answer or "",
                    "explanation": detail.explanation or "",
                }
            )
        return base_payload
    if question_type == "fill":
        detail = get_public_fill_question_by_id(question_id)
        if not detail:
            return None
        base_payload.update(
            {
                "brief": detail.brief or "",
                "content": detail.content or "",
            }
        )
        if include_answer:
            base_payload.update(
                {
                    "answer": detail.answer or "",
                    "explanation": detail.explanation or "",
                }
            )
        return base_payload
    if question_type == "subjective":
        detail = get_public_subjective_question_by_id(question_id)
        if not detail:
            return None
        base_payload.update(
            {
                "brief": detail.brief or "",
                "content": detail.content or "",
            }
        )
        if include_answer:
            base_payload.update(
                {
                    "answer": detail.answer or "",
                    "explanation": detail.explanation or "",
                }
            )
        return base_payload
    if question_type == "custom":
        detail = get_public_custom_question_by_id(question_id)
        if not detail:
            return None
        base_payload.update(
            {
                "brief": detail.brief or "",
                "imageURL": detail.imageURL or "",
            }
        )
        return base_payload
    return None


def _build_recommendation_query(course: str, question_type: str, requirement: str) -> dict:
    normalized_course = _normalize_text(course)
    normalized_type = normalize_question_type(question_type)
    normalized_requirement = _normalize_text(requirement)
    type_label = QUESTION_TYPE_LABELS.get(normalized_type, "习题")
    fallback_brief = _build_default_brief(normalized_course, normalized_type, normalized_requirement)
    prompt = _load_prompt_text(PRACTICE_RECOMMEND_PROMPT)
    prompt_content = _render_prompt(
        prompt,
        {
            "course": normalized_course,
            "question_type": type_label,
            "requirement": normalized_requirement,
        },
    )
    llm_result = call_chat_once(
        messages=[
            {
                "role": "system",
                "content": "你是题库检索摘要助手，请严格按给定模板输出。",
            },
            {"role": "user", "content": prompt_content},
        ],
        model_level="lite",
        temperature=0,
        max_tokens=200,
    )
    payload = _extract_json_payload(llm_result)
    brief = _normalize_text(payload.get("brief")) or fallback_brief
    keywords = payload.get("keywords") if isinstance(payload.get("keywords"), list) else []
    keywords = _unique_list([str(item) for item in keywords], limit=6)
    if not keywords:
        keywords = _unique_list(re.split(r"[，,、；;\s]+", normalized_requirement), limit=6)
    query_parts = _unique_list([brief, normalized_requirement, *keywords], limit=8)
    return {
        "userBrief": brief[:80],
        "keywords": keywords,
        "queryText": " ".join(query_parts)[:240],
    }


def _extract_tokens(text: str) -> list[str]:
    normalized_text = _normalize_text(text).lower()
    if not normalized_text:
        return []
    chunks = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", normalized_text)
    if chunks:
        return chunks
    return re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", normalized_text)


def _score_candidate(query_text: str, keywords: list[str], brief: str, content: str) -> int:
    query_tokens = _extract_tokens(query_text)
    if not query_tokens:
        return 0
    brief_text = _normalize_text(brief).lower()
    content_text = _normalize_text(content).lower()
    joined_text = f"{brief_text} {content_text}".strip()
    candidate_tokens = set(_extract_tokens(joined_text))
    score = 0
    for keyword in keywords:
        normalized_keyword = _normalize_text(keyword).lower()
        if not normalized_keyword:
            continue
        if normalized_keyword in brief_text:
            score += 18
        elif normalized_keyword in joined_text:
            score += 10
    for token in query_tokens:
        if token in candidate_tokens:
            score += 5 if token in brief_text else 2
    if joined_text and _normalize_text(query_text).lower() in joined_text:
        score += 12
    return score


def _rank_indexed_candidate_ids(
    query_text: str,
    keywords: list[str],
    candidates: list[dict],
    limit: int,
    excluded_ids: set[int] | None = None,
    indexed_only: bool = True,
) -> list[int]:
    excluded = excluded_ids or set()
    indexed_ids = set(filter_existing_question_ids([item.get("id") for item in candidates]))
    if indexed_only and not indexed_ids:
        return []
    scored_rows: list[tuple[int, int]] = []
    for item in candidates:
        try:
            question_id = int(item.get("id"))
        except Exception:
            continue
        if question_id in excluded:
            continue
        if indexed_only and question_id not in indexed_ids:
            continue
        score = _score_candidate(
            query_text=query_text,
            keywords=keywords,
            brief=item.get("brief", ""),
            content=item.get("content", ""),
        )
        if score > 0:
            scored_rows.append((score, question_id))
    scored_rows.sort(key=lambda row: (-row[0], row[1]))
    return [question_id for _, question_id in scored_rows[: max(1, int(limit))]]


def get_practice_sets(student_id: str) -> list[dict]:
    return [_serialize_practice_set(item) for item in get_practice_sets_by_student(student_id)]


def create_student_practice_set(student_id: str, name: str) -> tuple[dict | None, int, str]:
    normalized_name = _normalize_text(name)
    practice_set = create_practice_set(student_id, normalized_name or "练习题单")
    if not practice_set:
        return None, 500, "Create practice set failed"
    if not normalized_name:
        updated_set = update_practice_set_name(practice_set.id, f"练习题单{practice_set.id}")
        if updated_set:
            practice_set = updated_set
    return _serialize_practice_set(practice_set), 200, "Practice set created"


def delete_student_practice_set(student_id: str, set_id: int) -> tuple[bool, int, str]:
    practice_set = get_practice_set_by_id(set_id)
    if not practice_set or practice_set.student_id != student_id:
        return False, 404, "Practice set not found"
    if not delete_practice_set(set_id):
        return False, 500, "Delete practice set failed"
    return True, 200, "Practice set deleted"


def add_question_into_student_practice_set(
    student_id: str,
    set_id: int,
    question_id: int,
) -> tuple[dict | None, int, str]:
    practice_set = get_practice_set_by_id(set_id)
    if not practice_set or practice_set.student_id != student_id:
        return None, 404, "Practice set not found"
    question_detail = get_practice_question_detail(question_id)
    if not question_detail:
        return None, 404, "Question not found"
    if is_question_in_practice_set(set_id, question_id):
        return _serialize_practice_set(practice_set), 200, "Question already exists in practice set"
    if not add_question_to_practice_set(set_id, question_id):
        return None, 500, "Add question to practice set failed"
    refreshed_set = get_practice_set_by_id(set_id)
    return _serialize_practice_set(refreshed_set), 200, "Question added to practice set"


def remove_question_from_student_practice_set(
    student_id: str,
    set_id: int,
    question_id: int,
) -> tuple[dict | None, int, str]:
    practice_set = get_practice_set_by_id(set_id)
    if not practice_set or practice_set.student_id != student_id:
        return None, 404, "Practice set not found"
    if not remove_question_from_practice_set(set_id, question_id):
        return None, 404, "Question not found in practice set"
    refreshed_set = get_practice_set_by_id(set_id)
    return _serialize_practice_set(refreshed_set), 200, "Question removed from practice set"


def get_student_practice_session(student_id: str, set_id: int) -> tuple[dict | None, int, str]:
    practice_set = get_practice_set_by_id(set_id)
    if not practice_set or practice_set.student_id != student_id:
        return None, 404, "Practice set not found"
    question_rows = get_practice_set_questions(set_id)
    questions: list[dict] = []
    for row in question_rows:
        detail = get_practice_question_detail(row.question_id, include_answer=True)
        if not detail:
            continue
        detail["orderNum"] = row.order_num
        questions.append(detail)
    return (
        {
            "set": _serialize_practice_set(practice_set),
            "questions": questions,
        },
        200,
        "Practice session fetched",
    )


def recommend_practice_questions(
    course: str,
    question_type: str,
    requirement: str,
    limit: int = 10,
) -> tuple[dict | None, int, str]:
    normalized_course = _normalize_text(course)
    normalized_type = normalize_question_type(question_type)
    normalized_requirement = _normalize_text(requirement)
    if not normalized_course:
        return None, 400, "Missing course"
    if not normalized_type:
        return None, 400, "Invalid type"
    if not normalized_requirement:
        return None, 400, "Missing requirement"
    safe_limit = max(1, min(int(limit or 10), 10))
    recommendation_query = _build_recommendation_query(
        course=normalized_course,
        question_type=normalized_type,
        requirement=normalized_requirement,
    )
    user_brief = recommendation_query["userBrief"]
    query_text = recommendation_query["queryText"]
    keywords = recommendation_query["keywords"]
    recommended_questions: list[dict] = []
    seen_ids: set[int] = set()
    for question_id in search_question_topK(query_text, normalized_course, normalized_type, safe_limit):
        if question_id in seen_ids:
            continue
        question_detail = get_practice_question_detail(question_id)
        if not question_detail:
            continue
        recommended_questions.append(question_detail)
        seen_ids.add(question_id)
    if len(recommended_questions) < safe_limit:
        candidate_rows = get_public_question_search_candidates(normalized_type, normalized_course)
        fallback_ids = _rank_indexed_candidate_ids(
            query_text=query_text,
            keywords=keywords,
            candidates=candidate_rows,
            limit=safe_limit,
            excluded_ids=seen_ids,
        )
        for question_id in fallback_ids:
            if question_id in seen_ids:
                continue
            question_detail = get_practice_question_detail(question_id)
            if not question_detail:
                continue
            recommended_questions.append(question_detail)
            seen_ids.add(question_id)
            if len(recommended_questions) >= safe_limit:
                break
    if len(recommended_questions) < safe_limit:
        candidate_rows = get_public_question_search_candidates(normalized_type, normalized_course)
        fallback_ids = _rank_indexed_candidate_ids(
            query_text=query_text,
            keywords=keywords,
            candidates=candidate_rows,
            limit=safe_limit,
            excluded_ids=seen_ids,
            indexed_only=False,
        )
        for question_id in fallback_ids:
            if question_id in seen_ids:
                continue
            question_detail = get_practice_question_detail(question_id)
            if not question_detail:
                continue
            recommended_questions.append(question_detail)
            seen_ids.add(question_id)
            if len(recommended_questions) >= safe_limit:
                break
    return (
        {
            "course": normalized_course,
            "type": normalized_type,
            "requirement": normalized_requirement,
            "userBrief": user_brief,
            "keywords": keywords,
            "questions": recommended_questions[:safe_limit],
        },
        200,
        "Practice recommendation fetched",
    )
