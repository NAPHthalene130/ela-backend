# 文件：d:\front\ela-backend\repositories\student_exam_repository.py
from core.extensions import db
from database.models import (
    ChoiceQuestionNode,
    CustomQuestionNode,
    FillQuestionNode,
    QuestionNode,
    QuestionSet,
    QuestionSetAssignment,
    QuestionSetQuestion,
    StudentAnswer,
    StudentGroup,
    StudentGroupMember,
    SubjectiveQuestionNode,
)


def get_assignments_for_student(student_id: str) -> list[dict]:
    try:
        rows = (
            db.session.query(QuestionSetAssignment, QuestionSet, StudentGroup)
            .join(
                StudentGroupMember,
                StudentGroupMember.group_id == QuestionSetAssignment.group_id,
            )
            .outerjoin(QuestionSet, QuestionSet.id == QuestionSetAssignment.set_id)
            .outerjoin(StudentGroup, StudentGroup.id == QuestionSetAssignment.group_id)
            .filter(StudentGroupMember.student_id == student_id)
            .order_by(QuestionSetAssignment.id.asc())
            .all()
        )
        result = []
        for assignment, question_set, group in rows:
            result.append(
                {
                    "assignmentID": assignment.id,
                    "assignmentName": assignment.assignment_name or f"任务 {assignment.id}",
                    "setID": assignment.set_id,
                    "setName": question_set.name if question_set else "",
                    "groupID": assignment.group_id,
                    "groupName": group.name if group else "",
                    "beginTime": assignment.begin_time,
                    "endTime": assignment.end_time,
                }
            )
        return result
    except Exception:
        return []


def is_student_in_assignment_group(student_id: str, assignment_id: int) -> bool:
    try:
        exists = (
            db.session.query(QuestionSetAssignment.id)
            .join(
                StudentGroupMember,
                StudentGroupMember.group_id == QuestionSetAssignment.group_id,
            )
            .filter(
                QuestionSetAssignment.id == assignment_id,
                StudentGroupMember.student_id == student_id,
            )
            .first()
        )
        return exists is not None
    except Exception:
        return False


def get_exam_paper_details(assignment_id: int) -> dict | None:
    try:
        assignment_row = (
            db.session.query(QuestionSetAssignment, QuestionSet, StudentGroup)
            .outerjoin(QuestionSet, QuestionSet.id == QuestionSetAssignment.set_id)
            .outerjoin(StudentGroup, StudentGroup.id == QuestionSetAssignment.group_id)
            .filter(QuestionSetAssignment.id == assignment_id)
            .first()
        )
        if not assignment_row:
            return None

        assignment, question_set, group = assignment_row
        relation_rows = (
            QuestionSetQuestion.query.filter_by(set_id=assignment.set_id)
            .order_by(
                QuestionSetQuestion.order_num.asc(),
                QuestionSetQuestion.question_id.asc(),
            )
            .all()
        )

        questions = []
        for relation in relation_rows:
            question_node = QuestionNode.query.filter_by(id=relation.question_id).first()
            if not question_node:
                continue

            question_type = (question_node.type or "").lower()
            question_item = {
                "questionID": question_node.id,
                "type": question_type,
                "course": question_node.course or "",
                "brief": "",
                "content": "",
                "imageURL": "",
                "options": [],
                "score": None,
            }

            if question_type == "choice":
                detail = ChoiceQuestionNode.query.filter_by(id=question_node.id).first()
                if not detail:
                    continue
                question_item["brief"] = detail.brief or ""
                question_item["content"] = detail.content or ""
                question_item["options"] = [
                    {"key": "A", "text": detail.optionA or ""},
                    {"key": "B", "text": detail.optionB or ""},
                    {"key": "C", "text": detail.optionC or ""},
                    {"key": "D", "text": detail.optionD or ""},
                ]
            elif question_type == "fill":
                detail = FillQuestionNode.query.filter_by(id=question_node.id).first()
                if not detail:
                    continue
                question_item["brief"] = detail.brief or ""
                question_item["content"] = detail.content or ""
            elif question_type == "subjective":
                detail = SubjectiveQuestionNode.query.filter_by(id=question_node.id).first()
                if not detail:
                    continue
                question_item["brief"] = detail.brief or ""
                question_item["content"] = detail.content or ""
            elif question_type == "custom":
                detail = CustomQuestionNode.query.filter_by(id=question_node.id).first()
                if not detail:
                    continue
                question_item["brief"] = detail.brief or ""
                question_item["imageURL"] = detail.imageURL or ""
            else:
                continue

            questions.append(question_item)

        return {
            "assignment": {
                "assignmentID": assignment.id,
                "assignmentName": assignment.assignment_name or f"任务 {assignment.id}",
                "setID": assignment.set_id,
                "setName": question_set.name if question_set else "",
                "groupID": assignment.group_id,
                "groupName": group.name if group else "",
                "beginTime": assignment.begin_time,
                "endTime": assignment.end_time,
            },
            "questions": questions,
        }
    except Exception:
        return None


def upsert_student_answers(student_id: str, assignment_id: int, answers_list: list) -> dict | None:
    try:
        assignment = QuestionSetAssignment.query.filter_by(id=assignment_id).first()
        if not assignment:
            return None

        relation_rows = QuestionSetQuestion.query.filter_by(set_id=assignment.set_id).all()
        question_id_set = {item.question_id for item in relation_rows}
        ignored_question_ids = []
        saved_count = 0

        for answer_item in answers_list:
            try:
                question_id = int(answer_item.get("questionID"))
            except Exception:
                continue

            if question_id not in question_id_set:
                ignored_question_ids.append(question_id)
                continue

            content = str(answer_item.get("content", "") or "")
            img_url = str(answer_item.get("imgURL", "") or "")
            target = StudentAnswer.query.filter_by(
                studentID=student_id,
                assignmentID=assignment_id,
                questionID=question_id,
            ).first()
            if target:
                target.content = content
                target.imgURL = img_url
            else:
                db.session.add(
                    StudentAnswer(
                        studentID=student_id,
                        assignmentID=assignment_id,
                        questionID=question_id,
                        content=content,
                        imgURL=img_url,
                    )
                )
            saved_count += 1

        db.session.commit()
        return {
            "savedCount": saved_count,
            "ignoredQuestionIDs": ignored_question_ids,
        }
    except Exception:
        db.session.rollback()
        return None# Student Exam API Contracts

## Authentication

- All endpoints require JWT: `Authorization: Bearer <token>`
- All endpoints return unified payload:
  - success: `{"status":"success","msg":"...","data":...}`
  - fail: `{"status":"fail","msg":"..."}`

## GET `/api/student/assignments`

Get current student assignment list by group membership.

### Query

- `debug_bypass_time` (optional): `true` or `false`
  - When `true`, all assignments are returned as `in_progress`.

### Success `200`

```json
{
  "status": "success",
  "msg": "Assignments fetched",
  "data": {
    "debugBypassTime": false,
    "items": [
      {
        "assignmentID": 101,
        "assignmentName": "第一章小测",
        "setID": 12,
        "setName": "第一章题单",
        "groupID": 5,
        "groupName": "计算机241班A组",
        "beginTime": "2026-04-10T09:00:00",
        "endTime": "2026-04-10T10:00:00",
        "status": "not_started"
      }
    ]
  }
}
```

### Status Rule

- `not_started`: now < beginTime
- `in_progress`: beginTime <= now <= endTime
- `ended`: now > endTime
- fallback:
  - both empty => `in_progress`
  - only beginTime => before begin => `not_started`, otherwise `in_progress`
  - only endTime => before or at end => `in_progress`, otherwise `ended`

## GET `/api/student/exam/{assignment_id}`

Get exam paper details for one assignment.

### Path

- `assignment_id` (int, required)

### Security

- student must belong to assignment group
- answer fields are never returned

### Success `200`

```json
{
  "status": "success",
  "msg": "Exam detail fetched",
  "data": {
    "assignment": {
      "assignmentID": 101,
      "assignmentName": "第一章小测",
      "setID": 12,
      "setName": "第一章题单",
      "groupID": 5,
      "groupName": "计算机241班A组",
      "beginTime": "2026-04-10T09:00:00",
      "endTime": "2026-04-10T10:00:00"
    },
    "questions": [
      {
        "questionID": 2001,
        "type": "choice",
        "course": "高等数学",
        "brief": "函数极限基础题",
        "content": "设 f(x)=..., 下列结论正确的是：",
        "imageURL": "",
        "options": [
          { "key": "A", "text": "..." },
          { "key": "B", "text": "..." },
          { "key": "C", "text": "..." },
          { "key": "D", "text": "..." }
        ],
        "score": null
      },
      {
        "questionID": 2002,
        "type": "fill",
        "course": "高等数学",
        "brief": "导数定义",
        "content": "函数 f(x) 在 x0 处可导的定义是 ____。",
        "imageURL": "",
        "options": [],
        "score": null
      },
      {
        "questionID": 2004,
        "type": "custom",
        "course": "高等数学",
        "brief": "读图分析",
        "content": "",
        "imageURL": "/api/question/assets/abc.png",
        "options": [],
        "score": null
      }
    ]
  }
}
```

## POST `/api/student/exam/submit`

Save progress or submit answers.

### Request Body

```json
{
  "assignmentID": 101,
  "mode": "save",
  "answers": [
    {
      "questionID": 2001,
      "content": "B",
      "imgURL": ""
    },
    {
      "questionID": 2004,
      "content": "",
      "imgURL": "/api/question/assets/student_upload_01.png"
    }
  ]
}
```

### Rules

- `mode` must be `save` or `submit`
- only questions in assignment set are persisted
- out-of-set questions are ignored and returned in `ignoredQuestionIDs`
- upsert target table: `studentAnswerTable`

### Success `200`

```json
{
  "status": "success",
  "msg": "Answers saved",
  "data": {
    "assignmentID": 101,
    "mode": "save",
    "savedCount": 2,
    "ignoredQuestionIDs": []
  }
}
```
