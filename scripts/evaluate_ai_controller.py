from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Any

from backend.app.agent.agent import FinanceAgent
from backend.app.agent.gemini_provider import GeminiProvider
from backend.app.agent.provider import (
    LLMProvider,
    LLMProviderError,
    ModelResponse,
    ToolCall,
)
from backend.app.agent.runtime import (
    SYSTEM_PROMPT,
    FinanceAgentRuntime,
)


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    question: str
    expected_tools: tuple[str, ...]
    expected_arguments: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class EvaluationResult:
    name: str
    passed: bool
    provider_status: str
    expected_tools: tuple[str, ...]
    actual_tools: tuple[str, ...]
    expected_arguments: tuple[dict[str, Any], ...]
    actual_arguments: tuple[dict[str, Any], ...]
    tool_calls: int
    latency_ms: float
    reason: str


EVALUATION_CASES: tuple[EvaluationCase, ...] = (
    EvaluationCase(
        name="batch_summary",
        question=(
            "What is the current reconciliation match rate, "
            "how many exceptions do we have, and what are "
            "the largest exception categories?"
        ),
        expected_tools=(
            "get_batch_summary",
        ),
    ),
    EvaluationCase(
        name="high_value_exceptions",
        question=(
            "Show me the three highest-value reconciliation "
            "exceptions and their amount differences."
        ),
        expected_tools=(
            "get_high_value_exceptions",
        ),
        expected_arguments=(
            {
                "limit": 3,
            },
        ),
    ),
    EvaluationCase(
        name="exception_investigation",
        question=(
            "Investigate transaction txn_00685 and explain "
            "what happened."
        ),
        expected_tools=(
            "investigate_exception",
        ),
        expected_arguments=(
            {
                "transaction_id": "txn_00685",
            },
        ),
    ),
    EvaluationCase(
        name="audit_verification",
        question=(
            "Verify whether the immutable audit chain is valid."
        ),
        expected_tools=(
            "verify_audit_chain",
        ),
    ),
)


class EvaluationMockProvider(LLMProvider):
    """
    Case-aware deterministic provider used only by the
    AI controller evaluation suite.

    This provider does NOT replace or modify the production
    MockFinanceProvider.

    Its purpose is to validate the evaluation pipeline,
    deterministic tool execution, argument handling, and
    controller metrics without consuming Gemini quota.
    """

    def __init__(
        self,
        case: EvaluationCase,
    ) -> None:
        self.case = case
        self.called = False

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        """
        Return the expected tool call for this evaluation case.

        Exactly one model response is generated.
        """

        if self.called:
            return ModelResponse(
                content=None,
                tool_calls=(),
            )

        self.called = True

        tool_calls = tuple(
            ToolCall(
                tool_name=tool_name,
                arguments=(
                    self.case.expected_arguments[index]
                    if index < len(
                        self.case.expected_arguments
                    )
                    else {}
                ),
            )
            for index, tool_name in enumerate(
                self.case.expected_tools
            )
        )

        return ModelResponse(
            content=None,
            tool_calls=tool_calls,
        )


def build_provider(
    provider_name: str,
    case: EvaluationCase,
) -> LLMProvider:
    """
    Construct the requested provider.

    Mock mode is deterministic and does not contact Gemini.
    Gemini mode performs a real provider request.
    """

    if provider_name == "mock":
        return EvaluationMockProvider(case)

    if provider_name == "gemini":
        return GeminiProvider()

    raise ValueError(
        f"Unsupported provider: {provider_name}"
    )


def build_messages(
    question: str,
) -> list[dict[str, Any]]:
    """
    Build the minimal single-turn controller prompt.
    """

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": question,
        },
    ]


def arguments_match(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> bool:
    """
    Verify that every expected argument is present
    with the expected value.

    Additional optional model arguments are allowed.
    """

    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            return False

    return True


def evaluate_case(
    provider: LLMProvider,
    finance_agent: FinanceAgent,
    runtime: FinanceAgentRuntime,
    case: EvaluationCase,
) -> EvaluationResult:
    """
    Evaluate exactly one controller decision.

    Evaluation boundary:

        Provider
            ↓
        ToolCall
            ↓
        FinanceAgent.execute_tool()
            ↓
        Deterministic registry

    No second LLM request is made.
    """

    start = time.perf_counter()

    try:
        response = provider.generate(
            messages=build_messages(
                case.question
            ),
            tools=runtime._build_tool_schemas(),
        )

    except LLMProviderError as exc:
        latency_ms = (
            time.perf_counter() - start
        ) * 1000

        return EvaluationResult(
            name=case.name,
            passed=False,
            provider_status=exc.code,
            expected_tools=case.expected_tools,
            actual_tools=(),
            expected_arguments=case.expected_arguments,
            actual_arguments=(),
            tool_calls=0,
            latency_ms=latency_ms,
            reason=str(exc),
        )

    except Exception as exc:
        latency_ms = (
            time.perf_counter() - start
        ) * 1000

        return EvaluationResult(
            name=case.name,
            passed=False,
            provider_status="PROVIDER_ERROR",
            expected_tools=case.expected_tools,
            actual_tools=(),
            expected_arguments=case.expected_arguments,
            actual_arguments=(),
            tool_calls=0,
            latency_ms=latency_ms,
            reason=f"Unexpected provider error: {exc}",
        )

    latency_ms = (
        time.perf_counter() - start
    ) * 1000

    actual_tools = tuple(
        tool_call.tool_name
        for tool_call in response.tool_calls
    )

    actual_arguments = tuple(
        dict(tool_call.arguments)
        for tool_call in response.tool_calls
    )

    if not response.tool_calls:
        return EvaluationResult(
            name=case.name,
            passed=False,
            provider_status="OK",
            expected_tools=case.expected_tools,
            actual_tools=(),
            expected_arguments=case.expected_arguments,
            actual_arguments=(),
            tool_calls=0,
            latency_ms=latency_ms,
            reason="Provider returned no tool call.",
        )

    if actual_tools != case.expected_tools:
        return EvaluationResult(
            name=case.name,
            passed=False,
            provider_status="OK",
            expected_tools=case.expected_tools,
            actual_tools=actual_tools,
            expected_arguments=case.expected_arguments,
            actual_arguments=actual_arguments,
            tool_calls=len(response.tool_calls),
            latency_ms=latency_ms,
            reason=(
                "Incorrect tool selection. "
                f"Expected {case.expected_tools}, "
                f"got {actual_tools}."
            ),
        )

    if len(actual_arguments) != len(
        case.expected_arguments
    ):
        if case.expected_arguments:
            return EvaluationResult(
                name=case.name,
                passed=False,
                provider_status="OK",
                expected_tools=case.expected_tools,
                actual_tools=actual_tools,
                expected_arguments=case.expected_arguments,
                actual_arguments=actual_arguments,
                tool_calls=len(response.tool_calls),
                latency_ms=latency_ms,
                reason=(
                    "Expected tool arguments were not "
                    "returned."
                ),
            )

    for index, expected_arguments in enumerate(
        case.expected_arguments
    ):
        actual_arguments_for_call = (
            actual_arguments[index]
        )

        if not arguments_match(
            expected_arguments,
            actual_arguments_for_call,
        ):
            return EvaluationResult(
                name=case.name,
                passed=False,
                provider_status="OK",
                expected_tools=case.expected_tools,
                actual_tools=actual_tools,
                expected_arguments=case.expected_arguments,
                actual_arguments=actual_arguments,
                tool_calls=len(response.tool_calls),
                latency_ms=latency_ms,
                reason=(
                    "Incorrect tool arguments. "
                    f"Expected {expected_arguments}, "
                    f"got {actual_arguments_for_call}."
                ),
            )

    executions = []

    for tool_call in response.tool_calls:
        execution = finance_agent.execute_tool(
            tool_call.tool_name,
            **tool_call.arguments,
        )

        executions.append(execution)

    failed_executions = tuple(
        execution
        for execution in executions
        if not execution.success
    )

    if failed_executions:
        first_failure = failed_executions[0]

        return EvaluationResult(
            name=case.name,
            passed=False,
            provider_status="OK",
            expected_tools=case.expected_tools,
            actual_tools=actual_tools,
            expected_arguments=case.expected_arguments,
            actual_arguments=actual_arguments,
            tool_calls=len(response.tool_calls),
            latency_ms=latency_ms,
            reason=(
                "Deterministic tool execution failed: "
                f"{first_failure.tool_name}: "
                f"{first_failure.error}"
            ),
        )

    return EvaluationResult(
        name=case.name,
        passed=True,
        provider_status="OK",
        expected_tools=case.expected_tools,
        actual_tools=actual_tools,
        expected_arguments=case.expected_arguments,
        actual_arguments=actual_arguments,
        tool_calls=len(response.tool_calls),
        latency_ms=latency_ms,
        reason=(
            "Correct tool and arguments selected; "
            "deterministic execution succeeded."
        ),
    )


def print_case_result(
    result: EvaluationResult,
) -> None:
    """
    Print one evaluation result.
    """

    print()
    print("-" * 72)
    print(
        f"CASE: {result.name}"
    )
    print("-" * 72)

    print(
        f"EXPECTED TOOL(S): "
        f"{', '.join(result.expected_tools)}"
    )

    print(
        f"ACTUAL TOOL(S): "
        f"{', '.join(result.actual_tools) or 'none'}"
    )

    print(
        f"EXPECTED ARGUMENTS: "
        f"{result.expected_arguments or 'none'}"
    )

    print(
        f"ACTUAL ARGUMENTS: "
        f"{result.actual_arguments or 'none'}"
    )

    print(
        f"TOOL CALLS: "
        f"{result.tool_calls}"
    )

    print(
        f"LATENCY: "
        f"{result.latency_ms:.0f} ms"
    )

    print(
        f"PROVIDER STATUS: "
        f"{result.provider_status}"
    )

    print(
        f"STATUS: "
        f"{'PASS' if result.passed else 'FAIL'}"
    )

    print(
        f"REASON: "
        f"{result.reason}"
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description=(
            "ReconAI AI Controller Evaluation Suite"
        )
    )

    parser.add_argument(
        "--provider",
        choices=(
            "mock",
            "gemini",
        ),
        default="mock",
        help=(
            "Evaluation provider. "
            "Default: mock."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 72)
    print("ReconAI AI CONTROLLER EVALUATION")
    print("=" * 72)

    print()
    print(
        f"PROVIDER: {args.provider.upper()}"
    )

    if args.provider == "mock":
        print(
            "MODE: OFFLINE DETERMINISTIC"
        )
    else:
        print(
            "MODE: LIVE GEMINI"
        )

    print(
        "LLM REQUESTS PER CASE: 1"
    )

    print(
        "FINAL-ANSWER GENERATION: SKIPPED"
    )

    print(
        "FINANCIAL EXECUTION: DETERMINISTIC REGISTRY"
    )

    finance_agent = FinanceAgent()

    results: list[EvaluationResult] = []

    for case in EVALUATION_CASES:
        provider = build_provider(
            args.provider,
            case,
        )

        runtime = FinanceAgentRuntime(
            provider=provider,
            agent=finance_agent,
            max_tool_rounds=1,
        )

        result = evaluate_case(
            provider=provider,
            finance_agent=finance_agent,
            runtime=runtime,
            case=case,
        )

        results.append(result)

        print_case_result(result)

    total = len(results)

    passed = sum(
        result.passed
        for result in results
    )

    controller_accuracy = (
        (passed / total) * 100
        if total
        else 0.0
    )

    provider_failures = sum(
        result.provider_status != "OK"
        for result in results
    )

    quota_failures = sum(
        result.provider_status
        == "GEMINI_QUOTA_EXCEEDED"
        for result in results
    )

    unavailable_failures = sum(
        result.provider_status
        == "GEMINI_SERVICE_UNAVAILABLE"
        for result in results
    )

    total_latency_ms = sum(
        result.latency_ms
        for result in results
    )

    average_latency_ms = (
        total_latency_ms / total
        if total
        else 0.0
    )

    print()
    print("=" * 72)
    print("EVALUATION SUMMARY")
    print("=" * 72)

    print(
        f"Cases evaluated       : {total}"
    )

    print(
        f"Controller passed     : {passed}"
    )

    print(
        f"Controller failed     : "
        f"{total - passed}"
    )

    print(
        f"Controller accuracy   : "
        f"{controller_accuracy:.2f}%"
    )

    print(
        f"Provider failures     : "
        f"{provider_failures}"
    )

    print(
        f"Quota failures        : "
        f"{quota_failures}"
    )

    print(
        f"503 failures          : "
        f"{unavailable_failures}"
    )

    print(
        f"Total LLM latency     : "
        f"{total_latency_ms:.0f} ms"
    )

    print(
        f"Average LLM latency   : "
        f"{average_latency_ms:.0f} ms"
    )

    print()
    print("=" * 72)

    if passed == total:
        print(
            "AI CONTROLLER EVALUATION: PASS"
        )

    elif provider_failures == total:
        print(
            "AI CONTROLLER EVALUATION: "
            "BLOCKED_BY_PROVIDER"
        )

    else:
        print(
            "AI CONTROLLER EVALUATION: FAIL"
        )


if __name__ == "__main__":
    main()