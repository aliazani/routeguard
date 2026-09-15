from routeguard.ai.model import create_chat_model
from routeguard.config import get_settings
from routeguard.services.chat import ChatService
from routeguard.services.intent import IntentService


def get_chat_service() -> ChatService:
    settings = get_settings()
    model = create_chat_model(settings)

    return ChatService(model)


def get_intent_service() -> IntentService:
    settings = get_settings()
    model = create_chat_model(settings)

    return IntentService(model)
