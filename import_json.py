import json
import os
import sys
from pathlib import Path
import time

# Ensure we can import from backend root
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.app_factory import create_app
from repositories.course_repository import ensure_course_exists
from repositories.questions_set_repository import add_choice_question
from repositories.vectorDB_repository import add_question as add_vector_question

from database.models import ChoiceQuestionNode

def process_json_file(app, filepath: Path, course_name: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loading {len(data)} questions from {filepath.name}...")
    
    with app.app_context():
        ensure_course_exists(course_name)
        
        for item in data:
            question_text = item.get('question', '').strip()
            options = item.get('options', [])
            answer = item.get('answer', '').strip()
            
            if not question_text:
                continue
                
            # Check for duplicate
            existing = ChoiceQuestionNode.query.filter_by(content=question_text).first()
            if existing:
                question_id = existing.id
                print(f"Already in DB: ID {question_id}")
            else:
                # Parse options
                optA = optB = optC = optD = ""
                for opt in options:
                    opt_str = str(opt).strip()
                    if opt_str.startswith('A.') or opt_str.startswith('A、'):
                        optA = opt_str[2:].strip()
                    elif opt_str.startswith('B.') or opt_str.startswith('B、'):
                        optB = opt_str[2:].strip()
                    elif opt_str.startswith('C.') or opt_str.startswith('C、'):
                        optC = opt_str[2:].strip()
                    elif opt_str.startswith('D.') or opt_str.startswith('D、'):
                        optD = opt_str[2:].strip()

                # Add to DB
                question_id = add_choice_question(
                    course=course_name,
                    content=question_text,
                    optionA=optA,
                    optionB=optB,
                    optionC=optC,
                    optionD=optD,
                    answer=answer,
                    brief=question_text,  # using question as brief
                    belong_id="$PUBLIC$"
                )
                if question_id:
                    print(f"Successfully added to DB: ID {question_id}")
                else:
                    print(f"Failed to add to DB: {question_text[:30]}...")
            
            if question_id:
                # Add to VectorDB
                # We should add retry or error handling
                for attempt in range(3):
                    try:
                        success = add_vector_question(
                            id=question_id,
                            brief=question_text,
                            course=course_name,
                            type="choice"
                        )
                        if success:
                            print(f"Successfully added to VectorDB: ID {question_id}")
                            break
                        else:
                            print(f"Failed to add to VectorDB: ID {question_id}, attempt {attempt+1}")
                            time.sleep(1)
                    except Exception as e:
                        print(f"Error adding to VectorDB: ID {question_id}, {e}")
                        time.sleep(1)

if __name__ == '__main__':
    app = create_app()
    files_to_import = [
        (BACKEND_ROOT / "基础概念.json", "数据结构"),
        (BACKEND_ROOT / "栈与队列.json", "数据结构"),
        (BACKEND_ROOT / "LLM_数据结构题库.json", "数据结构"),
    ]
    
    for filepath, course in files_to_import:
        if filepath.exists():
            print(f"Processing {filepath}...")
            process_json_file(app, filepath, course)
        else:
            print(f"File not found: {filepath}")
    
    print("Import completed.")
