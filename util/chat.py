from database.extensions import db
from database.models import WindowChatNode
from datetime import datetime, timezone
from util.getLlmResponse import getLlmRes_stream


def getChatResponse(userId: str, chatWindowID: str, message: str, course: str = ""):
    # 1. Save User Message to Database
    user_msg = WindowChatNode(
        windowID=chatWindowID,
        content=message,
        isUserSend=True,
        sendTime=datetime.now(timezone.utc).isoformat()
    )
    try:
        db.session.add(user_msg)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error saving user message: {e}")
        # Continue to generation even if save fails? Or return error?
        # Assuming we continue or at least try.

    prompt = f"请返回以下内容:userId={userId}\nchatWindowID={chatWindowID}\ncourse={course or ''}"
    
    # 2. Generator for Streaming Response
    def generate():
        full_response = []
        try:
            # Yield chunks from LLM
            for chunk in getLlmRes_stream(message, prompt):
                full_response.append(chunk)
                yield chunk
            
            # 3. Save Complete Bot Response to Database
            full_content = "".join(full_response)
            bot_msg = WindowChatNode(
                windowID=chatWindowID,
                content=full_content,
                isUserSend=False,
                sendTime=datetime.now(timezone.utc).isoformat()
            )
            # Use a new session or ensure the existing one is valid
            # In Flask stream_with_context, the request context is active, so db.session should work.
            db.session.add(bot_msg)
            db.session.commit()
            
        except Exception as e:
            print(f"Error during streaming or saving bot response: {e}")
            db.session.rollback()
            yield f"\n[System Error: {str(e)}]"

    return generate()
