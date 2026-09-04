from __future__ import annotations

from pathlib import Path

from backend.app.integrations.razorpay.adapter import (
    razorpay_payments_to_reconai,
    select_reconcilable_payments,
)
from backend.app.integrations.razorpay.client import (
    RazorpayClient,
)
from backend.app.integrations.razorpay.config import (
    RazorpaySettings,
)
from backend.app.integrations.razorpay.normalizer import (
    normalize_payment,
)
from backend.app.reconciliation.engine import (
    ReconciliationEngine,
)
from backend.app.reconciliation.models import (
    LedgerEntry,
    MatchResult,
    MatchStatus,
    Payment,
    Settlement,
)


ROOT = Path(__file__).resolve().parents[1]

DEMO_RESULTS_DIR = (
    ROOT
    / "data"
    / "results"
    / "razorpay_demo"
)

DEMO_AUDIT_FILE = (
    DEMO_RESULTS_DIR
    / "audit.jsonl"
)

DEMO_EXCEPTION_FILE = (
    DEMO_RESULTS_DIR
    / "exceptions.jsonl"
)


def reset_demo_files() -> None:
    """
    Reset isolated Razorpay demo artifacts.

    Main benchmark audit/results remain untouched.
    """

    DEMO_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in (
        DEMO_AUDIT_FILE,
        DEMO_EXCEPTION_FILE,
    ):
        if path.exists():
            path.unlink()


def build_exact_ledger(
    payment: Payment,
) -> LedgerEntry:
    """
    Exact merchant-ledger match.
    """

    return LedgerEntry(
        transaction_id=payment.transaction_id,
        ledger_id=(
            f"demo_ledger_{payment.payment_id}"
        ),
        order_ref=payment.order_id,
        amount=payment.amount,
        currency=payment.currency,
        status="POSTED",
        recorded_at=payment.created_at,
    )


def build_amount_mismatch_ledger(
    payment: Payment,
) -> LedgerEntry:
    """
    Deliberately introduce a financial amount mismatch.
    """

    return LedgerEntry(
        transaction_id=payment.transaction_id,
        ledger_id=(
            f"demo_ledger_{payment.payment_id}_mismatch"
        ),
        order_ref=payment.order_id,
        amount=round(
            payment.amount + 1.00,
            2,
        ),
        currency=payment.currency,
        status="POSTED",
        recorded_at=payment.created_at,
    )


def build_ambiguous_ledger_pair(
    payment: Payment,
) -> list[LedgerEntry]:
    """
    Create exact evidence plus conflicting source evidence.

    Expected engine behavior:
        AMBIGUOUS

    The engine must not silently choose the exact candidate.
    """

    exact = LedgerEntry(
        transaction_id=payment.transaction_id,
        ledger_id=(
            f"demo_ledger_{payment.payment_id}_exact"
        ),
        order_ref=payment.order_id,
        amount=payment.amount,
        currency=payment.currency,
        status="POSTED",
        recorded_at=payment.created_at,
    )

    conflicting = LedgerEntry(
        transaction_id=payment.transaction_id,
        ledger_id=(
            f"demo_ledger_{payment.payment_id}_alt"
        ),
        order_ref=(
            f"{payment.order_id}_ALT"
        ),
        amount=payment.amount,
        currency=payment.currency,
        status="POSTED",
        recorded_at=payment.created_at,
    )

    return [
        exact,
        conflicting,
    ]


def build_demo_settlement(
    payment: Payment,
) -> Settlement:
    """
    Build isolated settlement evidence for the integration demo.

    IMPORTANT:
        This settlement is synthetic.

        It is NOT fetched from Razorpay because the current
        Test Mode account has no settlement records yet.
    """

    fee = 0.0
    tax = 0.0

    return Settlement(
        transaction_id=payment.transaction_id,
        settlement_id=(
            f"demo_settlement_{payment.payment_id}"
        ),
        payment_id=payment.payment_id,
        gross_amount=payment.amount,
        fee=fee,
        tax=tax,
        net_amount=round(
            payment.amount
            - fee
            - tax,
            2,
        ),
        currency=payment.currency,
        settlement_date=(
            payment.created_at
            .date()
            .isoformat()
        ),
    )


def fetch_razorpay_payments() -> tuple[
    list[Payment],
    list[Payment],
]:
    """
    Fetch Razorpay Test Mode payments and split them into:

        captured / reconcilable
        excluded / non-financial attempts
    """

    settings = (
        RazorpaySettings.from_env()
    )

    with RazorpayClient(
        settings
    ) as client:
        response = client.fetch_payments(
            count=100,
        )

    normalized = [
        normalize_payment(
            record
        )
        for record in response.items
    ]

    (
        adapted,
        quarantined,
    ) = razorpay_payments_to_reconai(
        normalized
    )

    if quarantined:
        print()
        print(
            "QUARANTINED RAZORPAY PAYMENTS"
        )
        print(
            "-" * 72
        )

        for record in quarantined:
            print(
                record
            )

    (
        captured,
        excluded,
    ) = select_reconcilable_payments(
        adapted
    )

    return (
        captured,
        excluded,
    )


def choose_demo_payments(
    captured: list[Payment],
) -> list[Payment]:
    """
    Select four captured payments deterministically.

    Sorting prevents API ordering from changing scenario assignment.
    """

    if len(
        captured
    ) < 4:
        raise RuntimeError(
            "At least four captured Razorpay Test Mode "
            "payments are required. "
            f"Found {len(captured)}."
        )

    return sorted(
        captured,
        key=lambda payment: (
            payment.payment_id
        ),
    )[:4]


def build_demo_sources(
    payments: list[Payment],
) -> tuple[
    list[LedgerEntry],
    list[Settlement],
    dict[str, MatchStatus],
]:
    """
    Create four deterministic reconciliation scenarios.

    Scenario 1:
        MATCHED

    Scenario 2:
        AMOUNT_MISMATCH

    Scenario 3:
        MISSING_LEDGER

    Scenario 4:
        AMBIGUOUS
    """

    exact_payment = (
        payments[0]
    )

    mismatch_payment = (
        payments[1]
    )

    missing_ledger_payment = (
        payments[2]
    )

    ambiguous_payment = (
        payments[3]
    )

    ledger: list[
        LedgerEntry
    ] = []

    settlements: list[
        Settlement
    ] = []

    # ------------------------------------------------------------------
    # 1. Exact match
    # ------------------------------------------------------------------

    ledger.append(
        build_exact_ledger(
            exact_payment
        )
    )

    settlements.append(
        build_demo_settlement(
            exact_payment
        )
    )

    # ------------------------------------------------------------------
    # 2. Amount mismatch
    # ------------------------------------------------------------------

    ledger.append(
        build_amount_mismatch_ledger(
            mismatch_payment
        )
    )

    settlements.append(
        build_demo_settlement(
            mismatch_payment
        )
    )

    # ------------------------------------------------------------------
    # 3. Missing ledger
    # ------------------------------------------------------------------

    settlements.append(
        build_demo_settlement(
            missing_ledger_payment
        )
    )

    # No ledger row intentionally.

    # ------------------------------------------------------------------
    # 4. Ambiguous ledger evidence
    # ------------------------------------------------------------------

    ledger.extend(
        build_ambiguous_ledger_pair(
            ambiguous_payment
        )
    )

    settlements.append(
        build_demo_settlement(
            ambiguous_payment
        )
    )

    expected = {
        exact_payment.transaction_id: (
            MatchStatus.MATCHED
        ),
        mismatch_payment.transaction_id: (
            MatchStatus.AMOUNT_MISMATCH
        ),
        missing_ledger_payment.transaction_id: (
            MatchStatus.MISSING_LEDGER
        ),
        ambiguous_payment.transaction_id: (
            MatchStatus.AMBIGUOUS
        ),
    }

    return (
        ledger,
        settlements,
        expected,
    )


def get_primary_results(
    results: list[MatchResult],
) -> dict[str, MatchResult]:
    """
    Keep first canonical decision per transaction.

    Supplemental source events remain in the raw result list.
    """

    primary: dict[
        str,
        MatchResult,
    ] = {}

    for result in results:
        if (
            result.transaction_id
            not in primary
        ):
            primary[
                result.transaction_id
            ] = result

    return primary


def print_ingestion_summary(
    *,
    captured: list[Payment],
    excluded: list[Payment],
) -> None:
    """
    Print Razorpay ingestion/eligibility metrics.
    """

    print()
    print(
        "RAZORPAY INGESTION"
    )
    print(
        "-" * 72
    )

    print(
        f"Captured / reconcilable : "
        f"{len(captured)}"
    )

    print(
        f"Excluded payment attempts: "
        f"{len(excluded)}"
    )

    if excluded:
        print()

        print(
            "EXCLUDED PAYMENT ATTEMPTS"
        )
        print(
            "-" * 72
        )

        for payment in excluded:
            print(
                f"{payment.payment_id} | "
                f"{payment.status} | "
                f"{payment.order_id}"
            )


def print_demo_scenarios(
    *,
    payments: list[Payment],
    expected: dict[
        str,
        MatchStatus,
    ],
) -> None:
    """
    Display the four live Razorpay payments used in the demo.
    """

    print()
    print(
        "CAPTURED PAYMENTS USED FOR RECONCILIATION"
    )
    print(
        "-" * 72
    )

    for index, payment in enumerate(
        payments,
        start=1,
    ):
        expected_status = (
            expected[
                payment.transaction_id
            ]
        )

        print(
            f"{index}. "
            f"{payment.payment_id}"
        )

        print(
            f"   transaction_id : "
            f"{payment.transaction_id}"
        )

        print(
            f"   order_id       : "
            f"{payment.order_id}"
        )

        print(
            f"   amount         : "
            f"{payment.amount} "
            f"{payment.currency}"
        )

        print(
            f"   status         : "
            f"{payment.status}"
        )

        print(
            f"   scenario       : "
            f"{expected_status.value}"
        )


def print_results(
    results: list[MatchResult],
) -> None:
    """
    Print every deterministic engine result.
    """

    print()
    print(
        "RECONCILIATION RESULTS"
    )
    print(
        "-" * 72
    )

    for index, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"{index}. "
            f"{result.transaction_id} | "
            f"{result.status.value} | "
            f"{result.method.value}"
        )

        print(
            f"   payment_id        : "
            f"{result.payment_id}"
        )

        print(
            f"   ledger_id         : "
            f"{result.ledger_id}"
        )

        print(
            f"   settlement_id     : "
            f"{result.settlement_id}"
        )

        print(
            f"   confidence        : "
            f"{result.confidence:.4f}"
        )

        print(
            f"   amount_difference : "
            f"{result.amount_difference}"
        )

        print(
            f"   reason            : "
            f"{result.reason}"
        )


def validate_results(
    *,
    results: list[MatchResult],
    expected: dict[
        str,
        MatchStatus,
    ],
) -> None:
    """
    Validate deterministic engine behavior.
    """

    primary = (
        get_primary_results(
            results
        )
    )

    # ------------------------------------------------------------------
    # Expected scenario correctness
    # ------------------------------------------------------------------

    for (
        transaction_id,
        expected_status,
    ) in expected.items():

        actual = primary.get(
            transaction_id
        )

        if actual is None:
            raise AssertionError(
                f"Missing reconciliation result "
                f"for {transaction_id}."
            )

        if (
            actual.status
            != expected_status
        ):
            raise AssertionError(
                f"{transaction_id}: expected "
                f"{expected_status.value}, got "
                f"{actual.status.value}."
            )

    # ------------------------------------------------------------------
    # Zero unsafe duplicate resolutions
    # ------------------------------------------------------------------

    resolved_statuses = {
        MatchStatus.MATCHED,
        MatchStatus.FUZZY_MATCHED,
    }

    resolved_counts: dict[
        str,
        int,
    ] = {}

    for result in results:
        if (
            result.status
            not in resolved_statuses
        ):
            continue

        resolved_counts[
            result.transaction_id
        ] = (
            resolved_counts.get(
                result.transaction_id,
                0,
            )
            + 1
        )

    unsafe_duplicates = {
        transaction_id: count
        for (
            transaction_id,
            count,
        ) in resolved_counts.items()
        if count > 1
    }

    if unsafe_duplicates:
        raise AssertionError(
            "Unsafe duplicate automatic reconciliation "
            f"detected: {unsafe_duplicates}"
        )


def main() -> None:
    print(
        "=" * 72
    )
    print(
        "RECONAI RAZORPAY END-TO-END RECONCILIATION"
    )
    print(
        "=" * 72
    )

    reset_demo_files()

    # ------------------------------------------------------------------
    # Live Razorpay ingestion
    # ------------------------------------------------------------------

    (
        captured,
        excluded,
    ) = fetch_razorpay_payments()

    print_ingestion_summary(
        captured=captured,
        excluded=excluded,
    )

    demo_payments = (
        choose_demo_payments(
            captured
        )
    )

    # ------------------------------------------------------------------
    # Controlled merchant finance evidence
    # ------------------------------------------------------------------

    (
        ledger,
        settlements,
        expected,
    ) = build_demo_sources(
        demo_payments
    )

    print_demo_scenarios(
        payments=demo_payments,
        expected=expected,
    )

    print()
    print(
        "MERCHANT FINANCE FIXTURE"
    )
    print(
        "-" * 72
    )

    print(
        f"Ledger rows             : "
        f"{len(ledger)}"
    )

    print(
        f"Synthetic settlements   : "
        f"{len(settlements)}"
    )

    # ------------------------------------------------------------------
    # Existing deterministic engine
    # ------------------------------------------------------------------

    engine = ReconciliationEngine(
        audit_path=(
            DEMO_AUDIT_FILE
        ),
        exception_path=(
            DEMO_EXCEPTION_FILE
        ),
    )

    results = engine.reconcile(
        payments=demo_payments,
        ledger=ledger,
        settlements=settlements,
    )

    print_results(
        results
    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    validate_results(
        results=results,
        expected=expected,
    )

    primary = (
        get_primary_results(
            results
        )
    )

    canonical_count = len(
        primary
    )

    resolved_count = sum(
        1
        for result
        in primary.values()
        if result.status
        in {
            MatchStatus.MATCHED,
            MatchStatus.FUZZY_MATCHED,
        }
    )

    exception_count = (
        canonical_count
        - resolved_count
    )

    supplemental_count = (
        len(results)
        - canonical_count
    )

    print()
    print(
        "END-TO-END SUMMARY"
    )
    print(
        "-" * 72
    )

    print(
        f"Razorpay payments ingested: "
        f"{len(captured) + len(excluded)}"
    )

    print(
        f"Captured / eligible      : "
        f"{len(captured)}"
    )

    print(
        f"Excluded failed attempts : "
        f"{len(excluded)}"
    )

    print(
        f"Demo transactions        : "
        f"{canonical_count}"
    )

    print(
        f"Automatically resolved   : "
        f"{resolved_count}"
    )

    print(
        f"Canonical exceptions     : "
        f"{exception_count}"
    )

    print(
        f"Supplemental source events: "
        f"{supplemental_count}"
    )

    print(
        f"Audit artifact           : "
        f"{DEMO_AUDIT_FILE}"
    )

    print(
        f"Exception artifact       : "
        f"{DEMO_EXCEPTION_FILE}"
    )

    print()
    print(
        "=" * 72
    )

    print(
        "RAZORPAY END-TO-END RECONCILIATION: PASS"
    )

    print(
        "=" * 72
    )


if __name__ == "__main__":
    main()