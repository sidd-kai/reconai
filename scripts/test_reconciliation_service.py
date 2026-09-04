from __future__ import annotations

import tempfile
from pathlib import Path

from backend.app.reconciliation.models import (
    LedgerEntry,
    MatchStatus,
    Payment,
    Settlement,
)
from backend.app.services.reconciliation_service import (
    ReconciliationService,
)


def build_payment() -> Payment:
    return Payment(
        transaction_id=(
            "rzp_pay_service_test"
        ),
        payment_id=(
            "pay_service_test"
        ),
        order_id=(
            "order_service_test"
        ),
        amount=120.0,
        currency="INR",
        status="captured",
        created_at=(
            __import__(
                "datetime"
            )
            .datetime
            .fromisoformat(
                "2026-09-03T08:50:24+00:00"
            )
        ),
    )


def build_ledger(
    payment: Payment,
) -> LedgerEntry:
    return LedgerEntry(
        transaction_id=(
            payment.transaction_id
        ),
        ledger_id=(
            "ledger_service_test"
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


def build_settlement(
    payment: Payment,
) -> Settlement:
    return Settlement(
        transaction_id=(
            payment.transaction_id
        ),
        settlement_id=(
            "settlement_service_test"
        ),
        payment_id=(
            payment.payment_id
        ),
        gross_amount=(
            payment.amount
        ),
        fee=0.0,
        tax=0.0,
        net_amount=(
            payment.amount
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


def run_test() -> None:
    print(
        "=" * 72
    )
    print(
        "RECONAI RECONCILIATION SERVICE TEST"
    )
    print(
        "=" * 72
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(
            temp_dir
        )

        audit_path = (
            temp_path
            / "audit.jsonl"
        )

        exception_path = (
            temp_path
            / "exceptions.jsonl"
        )

        service = (
            ReconciliationService(
                audit_path=audit_path,
                exception_path=(
                    exception_path
                ),
            )
        )

        payment = (
            build_payment()
        )

        ledger = [
            build_ledger(
                payment
            ),
        ]

        settlements = [
            build_settlement(
                payment
            ),
        ]

        result = (
            service.reconcile_payment(
                payment=payment,
                ledger=ledger,
                settlements=settlements,
            )
        )

        assert (
            result.payment_count
            == 1
        )

        assert (
            result.ledger_count
            == 1
        )

        assert (
            result.settlement_count
            == 1
        )

        assert (
            len(
                result.results
            )
            == 1
        )

        decision = (
            result.results[
                0
            ]
        )

        assert (
            decision.status
            == MatchStatus.MATCHED
        )

        assert (
            decision.payment_id
            == payment.payment_id
        )

        assert (
            decision.ledger_id
            == "ledger_service_test"
        )

        assert (
            decision.settlement_id
            == "settlement_service_test"
        )

        assert (
            audit_path.exists()
        )

        assert (
            audit_path.read_text(
                encoding="utf-8"
            ).strip()
        )

        assert (
            not exception_path.exists()
            or not exception_path.read_text(
                encoding="utf-8"
            ).strip()
        )

        print()
        print(
            "Service invocation          : PASS"
        )

        print(
            "Deterministic MATCHED       : PASS"
        )

        print(
            "Audit artifact written      : PASS"
        )

        print(
            "Exception artifact clean    : PASS"
        )

    print()
    print(
        "=" * 72
    )

    print(
        "RECONCILIATION SERVICE: PASS"
    )

    print(
        "=" * 72
    )


if __name__ == "__main__":
    run_test()