from __future__ import annotations

from backend.app.agent.mock_provider import (
    MockFinanceProvider,
)
from backend.app.agent.runtime import (
    FinanceAgentRuntime,
)


def main() -> None:
    provider = MockFinanceProvider()

    runtime = FinanceAgentRuntime(
        provider=provider,
    )

    response = runtime.run(
        "Verify whether the immutable audit trail is intact."
    )

    print("AGENT RESPONSE")
    print("=" * 60)
    print(response.content)

    print()
    print(
        "Tool calls executed:",
        response.tool_calls_executed,
    )

    assert response.tool_calls_executed == 1
    assert "verified" in response.content.lower()
    assert "audit" in response.content.lower()

    print()
    print("AGENT RUNTIME: PASS")


if __name__ == "__main__":
    main()