from __future__ import annotations

from backend.app.agent.ai_controller import AIController
from backend.app.agent.gemini_provider import GeminiProvider
from backend.app.agent.tool_registry import ToolRegistry


def main() -> None:
    print("=" * 72)
    print("ReconAI AI FINANCE CONTROLLER TEST")
    print("=" * 72)

    provider = GeminiProvider()

    registry = ToolRegistry()

    controller = AIController(
        provider=provider,
        tool_registry=registry,
    )

    question = (
        "What is the current reconciliation match rate "
        "and how many exceptions are there?"
    )

    print()
    print("USER")
    print("-" * 72)
    print(question)

    response = controller.ask(
        question
    )

    print()
    print("RECONAI")
    print("-" * 72)
    print(response.answer)

    print()
    print("TOOL EXECUTIONS")
    print("-" * 72)

    for execution in response.tool_executions:
        print(
            f"{execution.tool_name}"
            f"({execution.arguments})"
        )

    print()
    print("=" * 72)
    print("AI CONTROLLER TEST COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()