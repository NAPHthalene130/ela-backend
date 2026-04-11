import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.app_factory import create_app
from services.practice_service import recommend_practice_questions

def test_recommend():
    app = create_app()
    with app.app_context():
        result, status_code, msg = recommend_practice_questions(
            course="数据结构",
            question_type="choice",
            requirement="关于队列的题",
            limit=5
        )
        print(f"Status: {status_code}, Msg: {msg}")
        if result:
            print(f"User Brief: {result.get('userBrief')}")
            for q in result.get('questions', []):
                print(f"Q: {q.get('brief')}")

if __name__ == "__main__":
    test_recommend()
