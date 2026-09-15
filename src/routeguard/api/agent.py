from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from pydantic import BaseModel, Field

from routeguard.services.agent_chat import (
    AgentChatService,
)

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


class AgentChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000,
    )


class AgentChatResponse(BaseModel):
    answer: str


def get_agent_chat_service() -> AgentChatService:
    return AgentChatService()


@router.post(
    "/chat",
    response_model=AgentChatResponse,
)
async def agent_chat(
    request: AgentChatRequest,
    service: Annotated[
        AgentChatService,
        Depends(get_agent_chat_service),
    ],
) -> AgentChatResponse:
    try:
        answer = await service.reply(request.message)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=("The agent could not complete the request."),
        ) from exc

    return AgentChatResponse(answer=answer)
