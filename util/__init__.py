def getChatResponse(userId: str, chatWindowID: str, message: str, course: str = ""):
    from util.chat import getChatResponse as _get_chat_response

    return _get_chat_response(userId, chatWindowID, message, course)


def getLlmRes_NoStream(msg: str, prompt: str):
    from util.getLlmResponse import getLlmRes_NoStream as _get_llm_no_stream

    return _get_llm_no_stream(msg, prompt)


def getLlmRes_stream(msg: str, prompt: str):
    from util.getLlmResponse import getLlmRes_stream as _get_llm_stream

    return _get_llm_stream(msg, prompt)


def iter_stream_text(stream):
    from util.getLlmResponse import iter_stream_text as _iter_stream_text

    return _iter_stream_text(stream)


__all__ = ["getChatResponse", "getLlmRes_NoStream", "getLlmRes_stream", "iter_stream_text"]
