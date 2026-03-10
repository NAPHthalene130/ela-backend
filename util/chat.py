from util.getLlmResponse import getLlmRes_NoStream


def getChatResponse(userId: str, chatWindowID: str, message: str) -> str:
    prompt = f"请返回以下内容:userId={userId}\nchatWindowID={chatWindowID}"
    return getLlmRes_NoStream(message, prompt)
