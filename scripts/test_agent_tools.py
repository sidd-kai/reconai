from __future__ import annotations

from backend.app.agent.agent import FinanceAgent


def main() -> None:
    agent = FinanceAgent()

    print("REGISTERED TOOLS")
    print("=" * 60)

    for tool in agent.list_tools():
        print(
            f"{tool['name']}: "
            f"{tool['description']}"
        )

    print()
    print("TOOL EXECUTION")
    print("=" * 60)

    summary = agent.execute_tool(
        "get_batch_summary"
    )

    assert summary.success is True

    print(
        f"Batch summary success: "
        f"{summary.success}"
    )

    audit = agent.execute_tool(
        "verify_audit_chain"
    )

    assert audit.success is True
    assert audit.result["verified"] is True

    print(
        f"Audit verification: "
        f"{audit.result['verified']}"
    )

    high_value = agent.execute_tool(
        "get_high_value_exceptions",
        limit=3,
    )

    assert high_value.success is True
    assert len(high_value.result) == 3

    print(
        f"High-value exceptions returned: "
        f"{len(high_value.result)}"
    )

    investigation = agent.execute_tool(
        "investigate_exception",
        transaction_id="txn_00685",
    )

    assert investigation.success is True
    assert (
        investigation.result.transaction_id
        == "txn_00685"
    )

    print(
        "Exception investigation: PASS"
    )

    print()
    print("AGENT TOOL REGISTRY: PASS")


if __name__ == "__main__":
    main()