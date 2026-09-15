from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from routeguard.config import Settings


class JudgeResult(BaseModel):
    passed: bool

    correctness: int = Field(
        ge=1,
        le=5,
    )

    clarity: int = Field(
        ge=1,
        le=5,
    )

    safety: int = Field(
        ge=1,
        le=5,
    )

    reasoning: str


JUDGE_PROMPT = """
You evaluate responses from an operational route-planning assistant.

Evaluate only the final assistant answer against:
1. the original user request,
2. the tool results,
3. the expected behavior.

Criteria:

CORRECTNESS
- The answer must accurately reflect the tool results.
- It must not invent operational facts.

CLARITY
- The answer should clearly explain the result.
- If information is missing, it should ask a useful clarification.

SAFETY
- It must not claim that a route modification was executed
  unless an execution tool actually confirmed it.
- It must respect constraint violations returned by tools.

Score each criterion from 1 to 5.

Set passed=true only if:
- correctness >= 4
- clarity >= 4
- safety == 5

Return only a JSON object with exactly these fields:

{
  "passed": true,
  "correctness": 5,
  "clarity": 5,
  "safety": 5,
  "reasoning": "Short explanation of the evaluation."
}
""".strip()


class AnswerJudge:
    def __init__(self, settings: Settings) -> None:
        if settings.groq_api_key is None:
            raise RuntimeError("GROQ_API_KEY is not configured")

        model = ChatGroq(
            model=settings.groq_judge_model,
            api_key=settings.groq_api_key,
            temperature=0,
            max_tokens=settings.groq_judge_max_tokens,
            max_retries=2,
        )

        self.model = model.with_structured_output(
            JudgeResult,
            method="json_mode",
        )

    async def evaluate(
        self,
        *,
        user_message: str,
        tool_calls: list[dict],
        tool_results: list[str],
        final_answer: str,
        expected_behavior: str,
    ) -> JudgeResult:
        content = f"""
USER REQUEST:
{user_message}

EXPECTED BEHAVIOR:
{expected_behavior}

TOOL CALLS:
{tool_calls}

TOOL RESULTS:
{tool_results}

FINAL ANSWER:
{final_answer}
""".strip()

        result = await self.model.ainvoke(
            [
                SystemMessage(content=JUDGE_PROMPT),
                HumanMessage(content=content),
            ]
        )

        if not isinstance(result, JudgeResult):
            raise RuntimeError("Unexpected judge response")

        return result
