from __future__ import annotations

from typing import Any

from backend.app.agent.provider import (
    LLMProvider,
    LLMProviderError,
    ModelResponse,
)
from backend.app.agent.runtime import FinanceAgentRuntime


class QuotaFailureProvider(LLMProvider):
    """
    Deterministic provider used to test runtime handling
    of an LLM quota failure.

    No external API call is made.
    """

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        raise LLMProviderError(
            "Gemini API quota has been exceeded.",
            code="GEMINI_QUOTA_EXCEEDED",
        )


def main() -> None:
    runtime = FinanceAgentRuntime(
        provider=QuotaFailureProvider()
    )

    response = runtime.run(
        "What is the current reconciliation match rate?"
    )

    print("PROVIDER ERROR HANDLING TEST")
    print("=" * 60)
    print(response.content)
    print()
    print(
        f"Tool calls executed: "
        f"{response.tool_calls_executed}"
    )

    assert (
        "AI reasoning is temporarily unavailable."
        in response.content
    )

    assert (
        "GEMINI_QUOTA_EXCEEDED"
        in response.content
    )

    assert (
        "No financial conclusion was generated."
        in response.content
    )

    assert response.tool_calls_executed == 0

    print()
    print("PROVIDER ERROR HANDLING: PASS")


if __name__ == "__main__":
    main()