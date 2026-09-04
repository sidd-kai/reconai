from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

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


ROOT = Path(__file__).resolve().parents[3]

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


@dataclass(frozen=True)
class RazorpayDemoSourceLabels:
    payment_source: str = (
        "Razorpay Test Mode"
    )

    ledger_source: str = (
        "Controlled merchant fixture"
    )

    settlement_source: str = (
        "Controlled synthetic fixture"
    )


@dataclass(frozen=True)
class RazorpayDemoPaymentResult:
    transaction_id: str

    payment_id: str
    order_id: str | None

    payment_amount: float
    currency: str
    payment_status: str

    expected_status: str
    actual_status: str

    method: str
    confidence: float

    ledger_id: str | None
    settlement_id: str | None

    amount_difference: float

    reason: str


@dataclass(frozen=True)
class RazorpayDemoSummary:
    razorpay_payments_ingested: int

    captured_eligible: int
    excluded_payment_attempts: int

    demo_transactions: int

    automatically_resolved: int
    canonical_exceptions: int

    supplemental_source_events: int

    unsafe_duplicate_resolutions: int

    passed: bool


@dataclass(frozen=True)
class RazorpayDemoResult:
    success: bool

    mode: str

    sources: RazorpayDemoSourceLabels

    summary: RazorpayDemoSummary

    transactions: tuple[
        RazorpayDemoPaymentResult,
        ...
    ]

    supplemental_results: tuple[
        dict[str, Any],
        ...
    ]

    excluded_payment_attempts: tuple[
        dict[str, Any],
        ...
    ]

    quarantined_payment_count: int

    audit_artifact: str
    exception_artifact: str

    financial_state_mutated: bool = False


class RazorpayDemoError(
    RuntimeError
):
    """Raised when the live Razorpay demo cannot execute safely."""


class RazorpayDemoService:
    """
    Run the isolated ReconAI Razorpay Test Mode demonstration.

    Real source:
        Razorpay Test Mode payments.

    Controlled fixtures:
        merchant ledger
        settlement evidence

    Production benchmark artifacts are never modified.
    """

    @staticmethod
    def _reset_demo_files() -> None:
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

    @staticmethod
    def _build_exact_ledger(
        payment: Payment,
    ) -> LedgerEntry:
        return LedgerEntry(
            transaction_id=(
                payment.transaction_id
            ),
            ledger_id=(
                f"demo_ledger_"
                f"{payment.payment_id}"
            ),
            order_ref=(
                payment.order_id
            ),
            amount=(
                payment.amount
            ),
            currency=(
                payment.currency
            ),
            status="POSTED",
            recorded_at=(
                payment.created_at
            ),
        )

    @staticmethod
    def _build_amount_mismatch_ledger(
        payment: Payment,
    ) -> LedgerEntry:
        return LedgerEntry(
            transaction_id=(
                payment.transaction_id
            ),
            ledger_id=(
                f"demo_ledger_"
                f"{payment.payment_id}"
                "_mismatch"
            ),
            order_ref=(
                payment.order_id
            ),
            amount=round(
                payment.amount
                + 1.00,
                2,
            ),
            currency=(
                payment.currency
            ),
            status="POSTED",
            recorded_at=(
                payment.created_at
            ),
        )

    @staticmethod
    def _build_ambiguous_ledger_pair(
        payment: Payment,
    ) -> list[
        LedgerEntry
    ]:
        exact = LedgerEntry(
            transaction_id=(
                payment.transaction_id
            ),
            ledger_id=(
                f"demo_ledger_"
                f"{payment.payment_id}"
                "_exact"
            ),
            order_ref=(
                payment.order_id
            ),
            amount=(
                payment.amount
            ),
            currency=(
                payment.currency
            ),
            status="POSTED",
            recorded_at=(
                payment.created_at
            ),
        )

        conflicting = LedgerEntry(
            transaction_id=(
                payment.transaction_id
            ),
            ledger_id=(
                f"demo_ledger_"
                f"{payment.payment_id}"
                "_alt"
            ),
            order_ref=(
                f"{payment.order_id}_ALT"
            ),
            amount=(
                payment.amount
            ),
            currency=(
                payment.currency
            ),
            status="POSTED",
            recorded_at=(
                payment.created_at
            ),
        )

        return [
            exact,
            conflicting,
        ]

    @staticmethod
    def _build_demo_settlement(
        payment: Payment,
    ) -> Settlement:
        """
        Synthetic settlement fixture.

        This is intentionally NOT represented as Razorpay-originated
        evidence because the Test Mode account currently has no
        settlement records available for this demo.
        """

        fee = 0.0
        tax = 0.0

        return Settlement(
            transaction_id=(
                payment.transaction_id
            ),
            settlement_id=(
                f"demo_settlement_"
                f"{payment.payment_id}"
            ),
            payment_id=(
                payment.payment_id
            ),
            gross_amount=(
                payment.amount
            ),
            fee=fee,
            tax=tax,
            net_amount=round(
                payment.amount
                - fee
                - tax,
                2,
            ),
            currency=(
                payment.currency
            ),
            settlement_date=(
                payment.created_at
                .date()
                .isoformat()
            ),
        )

    @staticmethod
    def _fetch_payments() -> tuple[
        list[Payment],
        list[Payment],
        int,
    ]:
        settings = (
            RazorpaySettings.from_env()
        )

        with RazorpayClient(
            settings
        ) as client:
            response = (
                client.fetch_payments(
                    count=100,
                )
            )

        normalized = [
            normalize_payment(
                record
            )
            for record
            in response.items
        ]

        (
            adapted,
            quarantined,
        ) = (
            razorpay_payments_to_reconai(
                normalized
            )
        )

        (
            captured,
            excluded,
        ) = (
            select_reconcilable_payments(
                adapted
            )
        )

        return (
            captured,
            excluded,
            len(
                quarantined
            ),
        )

    @staticmethod
    def _choose_demo_payments(
        captured: list[Payment],
    ) -> list[Payment]:
        if len(
            captured
        ) < 4:
            raise RazorpayDemoError(
                "At least four captured Razorpay "
                "Test Mode payments are required. "
                f"Found {len(captured)}."
            )

        return sorted(
            captured,
            key=lambda payment: (
                payment.payment_id
            ),
        )[:4]

    def _build_demo_sources(
        self,
        payments: list[Payment],
    ) -> tuple[
        list[LedgerEntry],
        list[Settlement],
        dict[
            str,
            MatchStatus,
        ],
    ]:
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

        ledger.append(
            self._build_exact_ledger(
                exact_payment
            )
        )

        settlements.append(
            self._build_demo_settlement(
                exact_payment
            )
        )

        ledger.append(
            self._build_amount_mismatch_ledger(
                mismatch_payment
            )
        )

        settlements.append(
            self._build_demo_settlement(
                mismatch_payment
            )
        )

        settlements.append(
            self._build_demo_settlement(
                missing_ledger_payment
            )
        )

        ledger.extend(
            self._build_ambiguous_ledger_pair(
                ambiguous_payment
            )
        )

        settlements.append(
            self._build_demo_settlement(
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

    @staticmethod
    def _primary_results(
        results: list[
            MatchResult
        ],
    ) -> dict[
        str,
        MatchResult,
    ]:
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

    @staticmethod
    def _validate(
        *,
        results: list[
            MatchResult
        ],
        expected: dict[
            str,
            MatchStatus,
        ],
    ) -> int:
        primary = (
            RazorpayDemoService
            ._primary_results(
                results
            )
        )

        for (
            transaction_id,
            expected_status,
        ) in expected.items():
            actual = primary.get(
                transaction_id
            )

            if actual is None:
                raise RazorpayDemoError(
                    "Missing reconciliation result "
                    f"for {transaction_id}."
                )

            if (
                actual.status
                != expected_status
            ):
                raise RazorpayDemoError(
                    f"{transaction_id}: expected "
                    f"{expected_status.value}, got "
                    f"{actual.status.value}."
                )

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

        unsafe_duplicates = sum(
            1
            for count
            in resolved_counts.values()
            if count > 1
        )

        if unsafe_duplicates:
            raise RazorpayDemoError(
                "Unsafe duplicate automatic "
                "reconciliation detected."
            )

        return unsafe_duplicates

    @staticmethod
    def _serialize_supplemental_result(
        result: MatchResult,
    ) -> dict[str, Any]:
        return {
            "transaction_id": (
                result.transaction_id
            ),
            "status": (
                result.status.value
            ),
            "method": (
                result.method.value
            ),
            "payment_id": (
                result.payment_id
            ),
            "ledger_id": (
                result.ledger_id
            ),
            "settlement_id": (
                result.settlement_id
            ),
            "confidence": (
                result.confidence
            ),
            "amount_difference": (
                result.amount_difference
            ),
            "reason": (
                result.reason
            ),
        }

    def run(
        self,
    ) -> RazorpayDemoResult:
        self._reset_demo_files()

        (
            captured,
            excluded,
            quarantined_count,
        ) = self._fetch_payments()

        demo_payments = (
            self._choose_demo_payments(
                captured
            )
        )

        (
            ledger,
            settlements,
            expected,
        ) = self._build_demo_sources(
            demo_payments
        )

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

        unsafe_duplicates = (
            self._validate(
                results=results,
                expected=expected,
            )
        )

        primary = (
            self._primary_results(
                results
            )
        )

        transaction_results: list[
            RazorpayDemoPaymentResult
        ] = []

        payment_by_transaction = {
            payment.transaction_id: payment
            for payment
            in demo_payments
        }

        for payment in demo_payments:
            result = primary[
                payment.transaction_id
            ]

            transaction_results.append(
                RazorpayDemoPaymentResult(
                    transaction_id=(
                        payment.transaction_id
                    ),
                    payment_id=(
                        payment.payment_id
                    ),
                    order_id=(
                        payment.order_id
                    ),
                    payment_amount=float(
                        payment.amount
                    ),
                    currency=(
                        payment.currency
                    ),
                    payment_status=(
                        payment.status
                    ),
                    expected_status=(
                        expected[
                            payment.transaction_id
                        ].value
                    ),
                    actual_status=(
                        result.status.value
                    ),
                    method=(
                        result.method.value
                    ),
                    confidence=float(
                        result.confidence
                    ),
                    ledger_id=(
                        result.ledger_id
                    ),
                    settlement_id=(
                        result.settlement_id
                    ),
                    amount_difference=float(
                        result.amount_difference
                    ),
                    reason=(
                        result.reason
                    ),
                )
            )

        supplemental_results = [
            self._serialize_supplemental_result(
                result
            )
            for result in results
            if (
                result.transaction_id
                not in payment_by_transaction
            )
        ]

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

        excluded_items = tuple(
            {
                "payment_id": (
                    payment.payment_id
                ),
                "transaction_id": (
                    payment.transaction_id
                ),
                "order_id": (
                    payment.order_id
                ),
                "status": (
                    payment.status
                ),
                "amount": float(
                    payment.amount
                ),
                "currency": (
                    payment.currency
                ),
            }
            for payment
            in excluded
        )

        summary = RazorpayDemoSummary(
            razorpay_payments_ingested=(
                len(captured)
                + len(excluded)
            ),
            captured_eligible=(
                len(captured)
            ),
            excluded_payment_attempts=(
                len(excluded)
            ),
            demo_transactions=(
                canonical_count
            ),
            automatically_resolved=(
                resolved_count
            ),
            canonical_exceptions=(
                exception_count
            ),
            supplemental_source_events=(
                len(results)
                - canonical_count
            ),
            unsafe_duplicate_resolutions=(
                unsafe_duplicates
            ),
            passed=True,
        )

        return RazorpayDemoResult(
            success=True,
            mode="TEST",
            sources=(
                RazorpayDemoSourceLabels()
            ),
            summary=summary,
            transactions=tuple(
                transaction_results
            ),
            supplemental_results=tuple(
                supplemental_results
            ),
            excluded_payment_attempts=(
                excluded_items
            ),
            quarantined_payment_count=(
                quarantined_count
            ),
            audit_artifact=str(
                DEMO_AUDIT_FILE
            ),
            exception_artifact=str(
                DEMO_EXCEPTION_FILE
            ),
        )


def serialize_razorpay_demo_result(
    result: RazorpayDemoResult,
) -> dict[str, Any]:
    return asdict(
        result
    )