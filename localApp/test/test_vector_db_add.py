import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from repositories.vectorDB_repository import add_question, delete_question, search_question_topK


def run_test(test_id: int = 29990002, cleanup: bool = False) -> None:
    brief = "这是一个向量数据库添加测试题目"
    course = "测试课程"
    qtype = "subjective"

    add_ok = add_question(test_id, brief, course, qtype)
    if not add_ok:
        raise RuntimeError("add_question 返回 False，请查看仓库层打印的错误堆栈")

    ids = search_question_topK(brief, course, qtype, 5)
    if test_id not in ids:
        raise RuntimeError(f"search_question_topK 未命中 test_id={test_id}，结果={ids}")

    delete_ok = None
    ids_after_delete = None
    if cleanup:
        delete_ok = delete_question(test_id)
        if not delete_ok:
            raise RuntimeError("delete_question 返回 False，请查看仓库层打印的错误堆栈")
        ids_after_delete = search_question_topK(brief, course, qtype, 5)
        if test_id in ids_after_delete:
            raise RuntimeError(f"delete 后仍能检索到 test_id={test_id}，结果={ids_after_delete}")

    result = {
        "test_id": test_id,
        "add_ok": add_ok,
        "search_ids": ids,
        "cleanup": cleanup,
        "delete_ok": delete_ok,
        "search_ids_after_delete": ids_after_delete,
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    # run_test()
    ids = search_question_topK("循环", "C语言", "choice", 5)
    print(ids)
