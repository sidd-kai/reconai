from __future__ import annotations

from backend.app.agent.gemini_provider import GeminiProvider
from backend.app.agent.runtime import FinanceAgentRuntime


def main() -> None:
    print("=" * 72)
    print("ReconAI GEMINI FINANCE AGENT TEST")
    print("=" * 72)

    provider = GeminiProvider()

    runtime = FinanceAgentRuntime(
        provider=provider
    )

    question = (
        "What is the current reconciliation match rate, "
        "how many exceptions do we have, and what are the "
        "largest exception categories?"
    )

    print()
    print("USER")
    print("-" * 72)
    print(question)

    response = runtime.run(
        question
    )

    print()
    print("RECONAI")
    print("-" * 72)
    print(response.content)

    print()
    print("TOOL CALLS EXECUTED")
    print("-" * 72)
    print(
        response.tool_calls_executed
    )

    print()
    print("=" * 72)
    print("GEMINI AGENT TEST COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()