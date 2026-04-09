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
        return None
