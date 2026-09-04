from __future__ import annotations

from backend.app.agent.intent_router import (
    FinanceIntentRouter,
)


def main() -> None:
    router = FinanceIntentRouter()

    cases = [
        (
            "What is the current reconciliation match rate?",
            "get_batch_summary",
            {},
        ),
        (
            "How many exceptions do we have?",
            "get_batch_summary",
            {},
        ),
        (
            "Show me the three highest-value reconciliation exceptions.",
            "get_high_value_exceptions",
            {"limit": 3},
        ),
        (
            "Investigate transaction txn_00685 and explain what happened.",
            "investigate_exception",
            {"transaction_id": "txn_00685"},
        ),
        (
            "Verify whether the immutable audit chain is valid.",
            "verify_audit_chain",
            {},
        ),
        (
            "Why are so many transactions failing reconciliation?",
            None,
            None,
        ),
    ]

    print("=" * 72)
    print("RECONAI DETERMINISTIC INTENT ROUTER TEST")
    print("=" * 72)

    for question, expected_tool, expected_arguments in cases:
        result = router.route(question)

        actual_tool = (
            result.tool_name
            if result is not None
            else None
        )

        actual_arguments = (
            result.arguments
            if result is not None
            else None
        )

        passed = (
            actual_tool == expected_tool
            and actual_arguments == expected_arguments
        )

        print()
        print(f"QUESTION: {question}")
        print(f"EXPECTED: {expected_tool} {expected_arguments}")
        print(f"ACTUAL:   {actual_tool} {actual_arguments}")
        print(
            "STATUS:   "
            + ("PASS" if passed else "FAIL")
        )

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()