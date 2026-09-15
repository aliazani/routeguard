from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from routeguard.schemas.intent import RouteIntent

SYSTEM_PROMPT = """
You classify user requests for a route-planning application.

Available intents:

- move_shipment:
  User wants to move a shipment between tours.

- get_tour:
  User asks to inspect or retrieve information about a tour.

- ask_policy:
  User asks about company rules, procedures, or operational policies.

- general:
  Anything else.

Field extraction rules:

- shipment_id:
  Extract the shipment identifier only if explicitly mentioned.

- tour_id:
  For get_tour, this is the requested tour.
  For move_shipment, this is the source tour if explicitly mentioned.

- target_tour_id:
  For move_shipment, this is the destination tour.

- question:
  Preserve the user's question for policy or general informational requests.

Never invent IDs.
If an ID is not explicitly provided, return null.
""".strip()


class IntentService:
    def __init__(self, model: BaseChatModel) -> None:
        self.model = model.with_structured_output(RouteIntent)

    async def classify(self, message: str) -> RouteIntent:
        result = await self.model.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=message),
            ]
        )

        if not isinstance(result, RouteIntent):
            raise RuntimeError("Unexpected structured output")

        return result
