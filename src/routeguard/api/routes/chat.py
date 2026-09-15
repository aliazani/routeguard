from typing import Annotated

from fastapi import APIRouter, Depends

from routeguard.dependencies import get_chat_service
from routeguard.schemas.chat import ChatRequest, ChatResponse
from routeguard.services.chat import ChatService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[
        ChatService,
        Depends(get_chat_service),
    ],
) -> ChatResponse:
    answer = await service.answer(request.message)

    return ChatResponse(answer=answer)
