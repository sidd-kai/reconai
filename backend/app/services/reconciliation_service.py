from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.app.reconciliation.engine import (
    ReconciliationEngine,
)
from backend.app.reconciliation.models import (
    LedgerEntry,
    MatchResult,
    Payment,
    Settlement,
)


DEFAULT_WEBHOOK_RECON_AUDIT_PATH = Path(
    "data/results/razorpay_webhook_reconciliation_audit.jsonl"
)

DEFAULT_WEBHOOK_RECON_EXCEPTION_PATH = Path(
    "data/results/razorpay_webhook_reconciliation_exceptions.jsonl"
)


@dataclass(frozen=True)
class ReconciliationServiceResult:
    """
    Deterministic service response for one reconciliation execution.
    """

    payment_count: int
    ledger_count: int
    settlement_count: int
    results: tuple[MatchResult, ...]


class ReconciliationService:
    """
    Thin deterministic orchestration layer around ReconciliationEngine.

    Responsibilities:
        - accept already-normalized ReconAI domain models
        - invoke deterministic reconciliation
        - preserve isolated audit/exception artifacts
        - expose no LLM behavior
        - perform no source mutation
    """

    def __init__(
        self,
        *,
        audit_path: Path = DEFAULT_WEBHOOK_RECON_AUDIT_PATH,
        exception_path: Path = DEFAULT_WEBHOOK_RECON_EXCEPTION_PATH,
    ) -> None:
        self._engine = ReconciliationEngine(
            audit_path=audit_path,
            exception_path=exception_path,
        )

    def reconcile(
        self,
        *,
        payments: list[Payment],
        ledger: list[LedgerEntry],
        settlements: list[Settlement],
    ) -> ReconciliationServiceResult:
        """
        Reconcile already-validated ReconAI domain records.
        """

        results = self._engine.reconcile(
            payments=payments,
            ledger=ledger,
            settlements=settlements,
        )

        return ReconciliationServiceResult(
            payment_count=len(
                payments
            ),
            ledger_count=len(
                ledger
            ),
            settlement_count=len(
                settlements
            ),
            results=tuple(
                results
            ),
        )

    def reconcile_payment(
        self,
        *,
        payment: Payment,
        ledger: list[LedgerEntry],
        settlements: list[Settlement],
    ) -> ReconciliationServiceResult:
        """
        Convenience wrapper for one webhook-ingested payment.
        """

        return self.reconcile(
            payments=[
                payment,
            ],
            ledger=ledger,
            settlements=settlements,
        )