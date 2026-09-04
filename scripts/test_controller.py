from __future__ import annotations

from backend.app.agent.controller import (
    FinanceController,
)


def main() -> None:

    print("=" * 72)
    print("ReconAI FINANCE CONTROLLER")
    print("=" * 72)

    controller = FinanceController()

    report = controller.run(
        priority_limit=5
    )

    print()
    print("BATCH")
    print("-" * 72)

    print(
        f"Records processed : "
        f"{report.records_processed}"
    )

    print(
        f"Matched           : "
        f"{report.matched}"
    )

    print(
        f"Exceptions        : "
        f"{report.exceptions}"
    )

    print(
        f"Match rate        : "
        f"{report.match_rate:.2f}%"
    )

    print(
        f"Exception rate    : "
        f"{report.exception_rate:.2f}%"
    )

    print()
    print("EXCEPTION BREAKDOWN")
    print("-" * 72)

    for status, count in (
        report.exception_breakdown.items()
    ):
        print(
            f"{status:24} {count}"
        )

    print()
    print("HIGH PRIORITY EXCEPTIONS")
    print("-" * 72)

    for item in (
        report.high_priority_exceptions
    ):
        print(
            f"{item['transaction_id']} | "
            f"{item['status']} | "
            f"amount_difference="
            f"{item['amount_difference']:.2f}"
        )

        print(
            f"  reason: "
            f"{item['reason']}"
        )

        print(
            f"  confidence: "
            f"{item['confidence']}"
        )

    print()
    print("RECOMMENDATIONS")
    print("-" * 72)

    for recommendation in (
        report.recommendations
    ):
        print(
            f"- {recommendation}"
        )

    print()
    print("AUDIT")
    print("-" * 72)

    print(
        f"Audit records      : "
        f"{report.audit_records}"
    )

    print(
        f"Audit verification : "
        f"{report.audit_chain_status}"
    )

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()