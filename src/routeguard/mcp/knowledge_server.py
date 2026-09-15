from typing import Any

from mcp.server.mcpserver import MCPServer

from routeguard.knowledge.store import KnowledgeStore

POLICY_MIN_SCORE = 0.35

store = KnowledgeStore()

mcp = MCPServer(
    "routeguard-knowledge",
    instructions=(
        "Provides read-only retrieval over company policy "
        "and procedure documents. "
        "Use this capability for questions about company rules, "
        "policies, procedures, requirements, and operational guidance."
    ),
)


@mcp.tool()
def search_policy_documents(
    query: str,
    limit: int = 3,
) -> dict[str, Any]:
    """Search company policy and procedure documents.

    Returns a structured response.

    If no sufficiently relevant policy evidence is found,
    found will be false and results will be empty.
    """

    safe_limit = max(
        1,
        min(limit, 5),
    )

    results = store.search(
        query,
        limit=safe_limit,
        min_score=POLICY_MIN_SCORE,
    )

    if not results:
        return {
            "found": False,
            "query": query,
            "message": (
                "No sufficiently relevant policy evidence was found in the available documents."
            ),
            "results": [],
        }

    return {
        "found": True,
        "query": query,
        "message": (f"Found {len(results)} relevant policy document chunk(s)."),
        "results": [
            {
                "text": result.text,
                "source": result.source,
                "document_id": result.document_id,
                "chunk_index": result.chunk_index,
                "score": round(
                    result.score,
                    4,
                ),
            }
            for result in results
        ],
    }


if __name__ == "__main__":
    mcp.run()
