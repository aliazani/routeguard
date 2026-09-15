from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ToolMessage,
)


def extract_tool_calls(
    messages: list[BaseMessage],
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    for message in messages:
        tool_calls = getattr(
            message,
            "tool_calls",
            None,
        )

        if not tool_calls:
            continue

        for call in tool_calls:
            calls.append(
                {
                    "name": call["name"],
                    "args": call["args"],
                }
            )

    return calls


def extract_tool_results(
    messages: list[BaseMessage],
) -> list[str]:
    return [str(message.content) for message in messages if isinstance(message, ToolMessage)]


def extract_final_answer(
    messages: list[BaseMessage],
) -> str:
    for message in reversed(messages):
        if (
            isinstance(message, AIMessage)
            and isinstance(message.content, str)
            and message.content
            and not message.tool_calls
        ):
            return message.content

    return ""
