from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExceptionSummary:
    status: str
    count: int


@dataclass(frozen=True)
class BatchSummary:
    """
    Canonical reconciliation batch summary.

    records_processed counts unique canonical transactions.

    raw_result_rows includes both canonical decisions and
    supplemental source-level events.
    """

    batch_id: str

    records_processed: int
    matched: int
    exceptions: int

    match_rate: float
    exception_rate: float

    exception_breakdown: tuple[
        ExceptionSummary,
        ...,
    ]

    audit_chain_verified: bool

    raw_result_rows: int
    supplemental_source_events: int


@dataclass(frozen=True)
class InvestigationResult:
    transaction_id: str
    status: str
    reason: str
    confidence: float

    payment_id: str | None
    ledger_id: str | None
    settlement_id: str | None

    amount_difference: float
    candidate_count: int

    evidence: dict[str, Any]


@dataclass(frozen=True)
class FinanceOpsException:
    """
    Canonical finance exception requiring attention.
    """

    transaction_id: str
    status: str

    amount_difference: float
    confidence: float

    reason: str

    payment_id: str | None
    ledger_id: str | None
    settlement_id: str | None


@dataclass(frozen=True)
class FinanceOpsSummary:
    """
    Deterministic transaction-level finance operations summary.

    Canonical metrics are calculated from one primary reconciliation
    decision per transaction.

    Supplemental source events are reported separately and never
    included in the automatic match-rate denominator.
    """

    records_processed: int
    matched: int
    exceptions: int

    match_rate: float
    exception_rate: float

    highest_financial_impact: float

    top_exceptions: tuple[
        FinanceOpsException,
        ...,
    ]

    exception_breakdown: tuple[
        ExceptionSummary,
        ...,
    ]

    audit_verified: bool

    raw_result_rows: int
    supplemental_source_events: int