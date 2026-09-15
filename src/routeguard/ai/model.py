from langchain_groq import ChatGroq

from routeguard.config import Settings


def create_chat_model(settings: Settings) -> ChatGroq:
    if settings.groq_api_key is None:
        raise RuntimeError("GROQ_API_KEY is not configured")

    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
        max_tokens=settings.groq_max_tokens,
        max_retries=2,
    )
