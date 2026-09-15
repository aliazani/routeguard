from dataclasses import dataclass
from typing import Any

from evals.cases import ToolEvalCase


@dataclass(frozen=True)
class EvalResult:
    passed: bool
    errors: list[str]


def evaluate_tool_behavior(
    case: ToolEvalCase,
    actual_calls: list[dict[str, Any]],
) -> EvalResult:
    errors: list[str] = []

    # ---------------------------------------------------------
    # REQUIRED TOOL CALLS
    # ---------------------------------------------------------

    for expected in case.required_calls:
        matching_calls = [call for call in actual_calls if call["name"] == expected.name]

        if not matching_calls:
            errors.append(f"Missing required tool: {expected.name}")
            continue

        # If args=None, we only care that the tool was called.
        if expected.args is None:
            continue

        exact_match = any(call.get("args") == expected.args for call in matching_calls)

        if not exact_match:
            actual_args = [call.get("args") for call in matching_calls]

            errors.append(
                f"Wrong arguments for {expected.name}. "
                f"Expected: {expected.args}. "
                f"Actual: {actual_args}."
            )

    # ---------------------------------------------------------
    # FORBIDDEN TOOL CALLS
    # ---------------------------------------------------------

    actual_tool_names = {call["name"] for call in actual_calls}

    forbidden_used = actual_tool_names & case.forbidden_tools

    if forbidden_used:
        errors.append("Forbidden tools used: " + ", ".join(sorted(forbidden_used)))

    # ---------------------------------------------------------
    # TOOL CALL COUNT
    # ---------------------------------------------------------

    if case.max_tool_calls is not None and len(actual_calls) > case.max_tool_calls:
        errors.append(f"Too many tool calls: {len(actual_calls)} > {case.max_tool_calls}")

    return EvalResult(
        passed=not errors,
        errors=errors,
    )
