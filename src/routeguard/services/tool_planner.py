from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

SYSTEM_PROMPT = """
You are RouteGuard, an assistant for route-planning operations.

Use the available tools whenever the user asks about live operational data.

Rules:

- To inspect a tour, use get_tour.
- To inspect a shipment, use get_shipment.
- To check whether a shipment can be moved between tours, use simulate_move.
- Never claim that a route change has been applied.
- You currently have no tool that modifies operational state.
- Never invent IDs or operational data.
- If required information is missing, ask the user for it instead of guessing.
""".strip()


class ToolPlannerService:
    def __init__(
        self,
        model: BaseChatModel,
        tools: list[BaseTool],
    ) -> None:
        self.model = model.bind_tools(tools)

    async def plan(self, message: str):
        return await self.model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=message),
            ]
        )
