from langchain_core.tools import BaseTool

ALLOWED_AGENT_TOOLS = {
    "routing_get_tour",
    "routing_get_shipment",
    "routing_simulate_move",
    "knowledge_search_policy_documents",
}


class UnsafeToolError(RuntimeError):
    pass


def validate_tools(
    tools: list[BaseTool],
) -> list[BaseTool]:
    discovered_names = {tool.name for tool in tools}

    unexpected = discovered_names - ALLOWED_AGENT_TOOLS

    if unexpected:
        raise UnsafeToolError("Unexpected MCP tools discovered: " + ", ".join(sorted(unexpected)))

    return tools
