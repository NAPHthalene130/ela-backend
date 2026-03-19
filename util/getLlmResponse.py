from openai import OpenAI

from project_config import API_KEY, BASE_URL, MODEL


def _extract_text_from_response(response) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    output = getattr(response, "output", None)
    if not output:
        return str(response)

    chunks = []
    for item in output:
        content_list = getattr(item, "content", None)
        if not content_list:
            continue
        for content in content_list:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)

    if chunks:
        return "".join(chunks)
    return str(response)


def getLlmRes_NoStream(msg: str, prompt: str) -> str:
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
    )

    response = client.responses.create(
        model=MODEL,
        input=f"{prompt}\n{msg}",
        extra_body={},
    )
    return _extract_text_from_response(response)


def getLlmRes_stream(msg: str, prompt: str):
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
    )

    stream = client.responses.create(
        model=MODEL,
        input=f"{prompt}\n{msg}",
        extra_body={},
        stream=True,
    )

    for event in stream:
        event_type = getattr(event, "type", "")
        if event_type == "response.output_text.delta":
            delta = getattr(event, "delta", "")
            if delta:
                yield delta
            continue

        text = getattr(event, "text", None)
        if text:
            yield text
