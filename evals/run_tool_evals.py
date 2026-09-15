import asyncio

from groq import RateLimitError
from langchain_core.messages import HumanMessage

from evals.cases import EVAL_CASES
from routeguard.agent.evaluation import (
    extract_final_answer,
    extract_tool_calls,
    extract_tool_results,
)
from routeguard.agent.evaluators import evaluate_tool_behavior
from routeguard.agent.graph import build_agent_graph
from routeguard.agent.judge import AnswerJudge
from routeguard.agent.mcp_client import get_mcp_tools
from routeguard.ai.model import create_chat_model
from routeguard.config import get_settings


async def invoke_with_retry(
    graph,
    payload: dict,
    config: dict,
):
    delays = [10, 20, 40]

    for attempt, delay in enumerate(
        delays,
        start=1,
    ):
        try:
            return await graph.ainvoke(
                payload,
                config=config,
            )

        except RateLimitError:
            if attempt == len(delays):
                raise

            print(f"\nGroq rate limit reached. Waiting {delay}s...")

            await asyncio.sleep(delay)

    raise RuntimeError("Unexpected retry state")


async def main() -> None:
    settings = get_settings()

    model = create_chat_model(settings)
    judge = AnswerJudge(settings)

    passed = 0
    total = len(EVAL_CASES)

    deterministic_passed = 0
    judged_cases = 0
    judge_passed = 0

    async with get_mcp_tools() as tools:
        graph = build_agent_graph(
            model=model,
            tools=tools,
        )

        for case in EVAL_CASES:
            result = await invoke_with_retry(
                graph,
                {"messages": [HumanMessage(content=case.user_message)]},
                {
                    "recursion_limit": 8,
                    "tags": [
                        "evaluation",
                        "tool-routing",
                    ],
                    "metadata": {
                        "eval_case": case.name,
                    },
                },
            )

            actual_calls = extract_tool_calls(result["messages"])

            tool_results = extract_tool_results(result["messages"])

            final_answer = extract_final_answer(result["messages"])

            evaluation = evaluate_tool_behavior(
                case=case,
                actual_calls=actual_calls,
            )

            errors = list(evaluation.errors)

            if evaluation.passed:
                deterministic_passed += 1

            judge_result = None

            if case.use_llm_judge:
                judged_cases += 1

                judge_result = await judge.evaluate(
                    user_message=case.user_message,
                    tool_calls=actual_calls,
                    tool_results=tool_results,
                    final_answer=final_answer,
                    expected_behavior=case.expected_behavior,
                )

                if judge_result.passed:
                    judge_passed += 1
                else:
                    errors.append("LLM judge rejected the final response.")

            success = not errors

            if success:
                passed += 1

            status = "PASS" if success else "FAIL"

            required_calls = [
                {
                    "name": call.name,
                    "args": call.args,
                }
                for call in case.required_calls
            ]

            print(f"\n[{status}] {case.name}")
            print(f"Input: {case.user_message}")
            print(f"Required calls: {required_calls}")
            print(f"Forbidden tools: {sorted(case.forbidden_tools)}")
            print(f"Actual calls: {actual_calls}")
            print(f"Tool results: {tool_results}")
            print(f"Final answer: {final_answer}")

            if judge_result is not None:
                print("LLM judge:")
                print(f"  correctness: {judge_result.correctness}/5")
                print(f"  clarity: {judge_result.clarity}/5")
                print(f"  safety: {judge_result.safety}/5")
                print(f"  reasoning: {judge_result.reasoning}")

            if errors:
                print("Errors:")

                for error in errors:
                    print(f"  - {error}")

    overall_accuracy = passed / total if total else 0

    deterministic_accuracy = deterministic_passed / total if total else 0

    print("\n==============================")
    print("Evaluation summary")
    print("==============================")

    print(f"Overall: {passed}/{total} ({overall_accuracy:.1%})")

    print(f"Deterministic: {deterministic_passed}/{total} ({deterministic_accuracy:.1%})")

    if judged_cases:
        judge_accuracy = judge_passed / judged_cases

        print(f"LLM judge: {judge_passed}/{judged_cases} ({judge_accuracy:.1%})")


if __name__ == "__main__":
    asyncio.run(main())
