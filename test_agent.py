import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.chat_service import stream_chat_response, create_window_for_user

def test_intent(msg: str, user_id: str, window_id: str):
    print(f"\n{'='*60}")
    print(f"User Input: {msg}")
    print(f"{'='*60}")
    
    with app.app_context():
        # Using stream_chat_response directly, which returns a generator
        generator = stream_chat_response(
            user_id=user_id, 
            chat_window_id=window_id, 
            message=msg, 
            course="大学物理"
        )
        
        print("Agent Response Stream:")
        for chunk in generator:
            # We flush so it prints out nicely on the console as it streams
            sys.stdout.write(chunk)
            sys.stdout.flush()
        print("\n" + "-"*60 + "\n")

if __name__ == "__main__":
    with app.app_context():
        # Ensure we have a valid test window
        user_id = "test_user_001"
        window_id = create_window_for_user(user_id)
        if not window_id:
            print("Warning: Failed to create window, using dummy string.")
            window_id = "dummy_window_123"
        else:
            print(f"Created Test Window ID: {window_id}")

    test_intent("什么是牛顿第一定律？", user_id, window_id)
    test_intent("给我出一道关于动量守恒的例题", user_id, window_id)
    test_intent("显示牛顿定律的知识图谱", user_id, window_id)
    test_intent("带我去考试页面", user_id, window_id)
