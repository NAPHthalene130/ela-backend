from core.extensions import db
from database.models import chatCardNode


def add_card(windowID: str, json_content: str) -> chatCardNode | None:
    normalized_window_id = str(windowID or "").strip()
    if not normalized_window_id:
        return None
    normalized_json = str(json_content or "")
    if len(normalized_json) > 8196:
        normalized_json = normalized_json[:8196]
    try:
        max_no = (
            db.session.query(db.func.max(chatCardNode.no))
            .filter(chatCardNode.windowsID == normalized_window_id)
            .scalar()
        )
        next_no = int(max_no or 0) + 1
        card = chatCardNode(
            windowsID=normalized_window_id,
            no=next_no,
            json=normalized_json,
        )
        db.session.add(card)
        db.session.commit()
        return card
    except Exception:
        db.session.rollback()
        return None


def get_card_list(windowID: str) -> list[chatCardNode]:
    normalized_window_id = str(windowID or "").strip()
    if not normalized_window_id:
        return []
    try:
        return (
            chatCardNode.query.filter_by(windowsID=normalized_window_id)
            .order_by(chatCardNode.no.asc())
            .all()
        )
    except Exception:
        return []


def delete_card(windowID: str) -> bool:
    normalized_window_id = str(windowID or "").strip()
    if not normalized_window_id:
        return False
    try:
        chatCardNode.query.filter_by(windowsID=normalized_window_id).delete()
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False
