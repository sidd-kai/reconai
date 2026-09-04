from __future__ import annotations

from dataclasses import asdict

from backend.app.agent.tools import (
    get_finance_ops_summary,
)


def main() -> None:
    print("=" * 72)
    print(
        "RECONAI FINANCE-OPS SUMMARY TEST"
    )
    print("=" * 72)

    summary = (
        get_finance_ops_summary(
            limit=5,
        )
    )

    payload = (
        asdict(
            summary
        )
    )

    print()
    print(
        "FINANCE-OPS SUMMARY"
    )
    print("-" * 72)

    print(
        f"Canonical transactions : "
        f"{summary.records_processed}"
    )

    print(
        f"Matched                : "
        f"{summary.matched}"
    )

    print(
        f"Exceptions             : "
        f"{summary.exceptions}"
    )

    print(
        f"Automatic match rate   : "
        f"{summary.match_rate:.2%}"
    )

    print(
        f"Exception rate         : "
        f"{summary.exception_rate:.2%}"
    )

    print(
        f"Raw result rows        : "
        f"{summary.raw_result_rows}"
    )

    print(
        f"Supplemental events    : "
        f"{summary.supplemental_source_events}"
    )

    print(
        f"Highest impact         : "
        f"{summary.highest_financial_impact}"
    )

    print(
        f"Audit verified         : "
        f"{summary.audit_verified}"
    )

    print()
    print(
        "TOP CANONICAL EXCEPTIONS"
    )
    print("-" * 72)

    for (
        index,
        exception,
    ) in enumerate(
        summary.top_exceptions,
        start=1,
    ):
        print(
            f"{index}. "
            f"{exception.transaction_id} | "
            f"{exception.status} | "
            f"difference="
            f"{exception.amount_difference}"
        )

    # ------------------------------------------------------------------
    # Structural validation
    # ------------------------------------------------------------------

    if (
        summary.records_processed
        <= 0
    ):
        raise AssertionError(
            "records_processed must be positive."
        )

    if summary.matched < 0:
        raise AssertionError(
            "matched cannot be negative."
        )

    if summary.exceptions < 0:
        raise AssertionError(
            "exceptions cannot be negative."
        )

    if (
        summary.matched
        + summary.exceptions
        != summary.records_processed
    ):
        raise AssertionError(
            "matched + exceptions must equal "
            "canonical records_processed."
        )

    if (
        summary.raw_result_rows
        < summary.records_processed
    ):
        raise AssertionError(
            "raw_result_rows cannot be smaller "
            "than canonical transaction count."
        )

    expected_supplemental = (
        summary.raw_result_rows
        - summary.records_processed
    )

    if (
        summary.supplemental_source_events
        != expected_supplemental
    ):
        raise AssertionError(
            "supplemental_source_events must equal "
            "raw_result_rows - records_processed."
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise AssertionError(
            "FinanceOpsSummary must serialize "
            "to a dictionary."
        )

    # ------------------------------------------------------------------
    # Rate validation
    # ------------------------------------------------------------------

    expected_match_rate = (
        summary.matched
        / summary.records_processed
    )

    expected_exception_rate = (
        summary.exceptions
        / summary.records_processed
    )

    if abs(
        summary.match_rate
        - expected_match_rate
    ) > 1e-9:
        raise AssertionError(
            "match_rate calculation is incorrect."
        )

    if abs(
        summary.exception_rate
        - expected_exception_rate
    ) > 1e-9:
        raise AssertionError(
            "exception_rate calculation is incorrect."
        )

    # ------------------------------------------------------------------
    # Expected benchmark contract
    # ------------------------------------------------------------------

    if (
        summary.records_processed
        != 1000
    ):
        raise AssertionError(
            "Expected 1000 canonical transactions."
        )

    if summary.matched != 705:
        raise AssertionError(
            "Expected 705 safely reconciled "
            "canonical transactions."
        )

    if summary.exceptions != 295:
        raise AssertionError(
            "Expected 295 canonical exceptions."
        )

    if (
        summary.raw_result_rows
        != 1010
    ):
        raise AssertionError(
            "Expected 1010 total engine result rows."
        )

    if (
        summary.supplemental_source_events
        != 10
    ):
        raise AssertionError(
            "Expected 10 supplemental source events."
        )

    # ------------------------------------------------------------------
    # Attention queue
    # ------------------------------------------------------------------

    if len(
        summary.top_exceptions
    ) > 5:
        raise AssertionError(
            "Attention queue exceeded "
            "requested limit."
        )

    if summary.top_exceptions:
        impacts = [
            abs(
                exception.amount_difference
            )
            for exception
            in summary.top_exceptions
        ]

        if impacts != sorted(
            impacts,
            reverse=True,
        ):
            raise AssertionError(
                "Top exceptions are not ordered "
                "by financial impact."
            )

        expected_highest = (
            impacts[0]
        )

        if abs(
            summary.highest_financial_impact
            - expected_highest
        ) > 1e-9:
            raise AssertionError(
                "highest_financial_impact does not "
                "match top exception."
            )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    if not isinstance(
        summary.audit_verified,
        bool,
    ):
        raise AssertionError(
            "audit_verified must be boolean."
        )

    print()
    print("=" * 72)
    print(
        "FINANCE-OPS SUMMARY: PASS"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()