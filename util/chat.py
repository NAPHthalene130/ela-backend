from services.chat_service import stream_chat_response


def getChatResponse(userId: str, chatWindowID: str, message: str, course: str = ""):
    return stream_chat_response(userId, chatWindowID, message, course)
