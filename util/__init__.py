def getChatResponse(userId: str, chatWindowID: str, message: str, course: str = ""):
    from util.chat import getChatResponse as _get_chat_response

    return _get_chat_response(userId, chatWindowID, message, course)


def getLlmRes(msg: str, prompt: str):
    from util.getLlmResponse import getLlmRes as _get_llm_res

    return _get_llm_res(msg, prompt)


__all__ = ["getChatResponse", "getLlmRes"]
