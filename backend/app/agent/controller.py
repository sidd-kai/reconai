from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .tools import (
    get_audit_record_count,
    get_batch_summary,
    get_high_value_exceptions,
    investigate_exception,
)


@dataclass(frozen=True)
class ControllerReport:
    """
    Final structured output produced by the Finance Controller.

    The controller does not create reconciliation decisions.
    It interprets and prioritizes decisions produced by the
    deterministic reconciliation engine.
    """

    records_processed: int
    matched: int
    exceptions: int

    match_rate: float
    exception_rate: float

    audit_records: int
    audit_chain_status: str

    exception_breakdown: dict[str, int]

    high_priority_exceptions: tuple[
        dict[str, Any],
        ...

    ]

    recommendations: tuple[str, ...]


class FinanceController:
    """
    Deterministic orchestration layer for ReconAI.

    Responsibilities:

    1. Inspect the latest reconciliation batch.
    2. Summarize outcomes.
    3. Prioritize financially significant exceptions.
    4. Investigate selected transactions.
    5. Produce an auditable controller report.

    The controller never overrides the reconciliation engine.
    """

    def run(
        self,
        *,
        priority_limit: int = 5,
    ) -> ControllerReport:

        summary = get_batch_summary()

        audit_records = (
            get_audit_record_count()
        )

        high_value = (
            get_high_value_exceptions(
                limit=priority_limit
            )
        )

        investigations: list[
            dict[str, Any]
        ] = []

        seen_transactions: set[str] = set()

        for exception in high_value:

            transaction_id = exception.get(
                "transaction_id"
            )

            if transaction_id is None:
                continue

            transaction_id = str(
                transaction_id
            )

            if transaction_id in seen_transactions:
                continue

            seen_transactions.add(
                transaction_id
            )

            investigation = (
                investigate_exception(
                    transaction_id
                )
            )

            investigations.append(
                {
                    "transaction_id":
                        investigation.transaction_id,
                    "status":
                        investigation.status,
                    "reason":
                        investigation.reason,
                    "confidence":
                        investigation.confidence,
                    "payment_id":
                        investigation.payment_id,
                    "ledger_id":
                        investigation.ledger_id,
                    "settlement_id":
                        investigation.settlement_id,
                    "amount_difference":
                        investigation.amount_difference,
                    "candidate_count":
                        investigation.candidate_count,
                    "evidence":
                        investigation.evidence,
                }
            )

        recommendations = (
            self._build_recommendations(
                summary=summary,
                investigations=investigations,
            )
        )

        return ControllerReport(
            records_processed=(
                summary.records_processed
            ),
            matched=summary.matched,
            exceptions=summary.exceptions,
            match_rate=summary.match_rate,
            exception_rate=summary.exception_rate,
            audit_records=audit_records,
            audit_chain_status="VERIFY_WITH_AUDIT_TOOL",
            exception_breakdown={
                item.status: item.count
                for item
                in summary.exception_breakdown
            },
            high_priority_exceptions=tuple(
                investigations
            ),
            recommendations=tuple(
                recommendations
            ),
        )

    @staticmethod
    def _build_recommendations(
        *,
        summary: Any,
        investigations: list[
            dict[str, Any]
        ],
    ) -> list[str]:

        recommendations: list[str] = []

        if summary.exceptions > 0:
            recommendations.append(
                "Route unresolved reconciliation "
                "exceptions for finance review."
            )

        if (
            summary.exception_breakdown
        ):
            recommendations.append(
                "Prioritize exceptions by financial "
                "impact before manual investigation."
            )

        for investigation in investigations:

            status = investigation[
                "status"
            ]

            transaction_id = investigation[
                "transaction_id"
            ]

            amount_difference = abs(
                float(
                    investigation[
                        "amount_difference"
                    ]
                )
            )

            if status == "AMOUNT_MISMATCH":
                recommendations.append(
                    f"Investigate {transaction_id}: "
                    f"amount discrepancy of "
                    f"{amount_difference:.2f}."
                )

            elif status == "AMBIGUOUS":
                recommendations.append(
                    f"Investigate {transaction_id}: "
                    "multiple ledger candidates prevent "
                    "safe automatic matching."
                )

            elif status == "DUPLICATE":
                recommendations.append(
                    f"Investigate {transaction_id}: "
                    "duplicate financial evidence detected."
                )

            elif status == "SETTLEMENT_MISMATCH":
                recommendations.append(
                    f"Investigate {transaction_id}: "
                    "settlement evidence conflicts with "
                    "payment/ledger evidence."
                )

            elif status == "MISSING_PAYMENT":
                recommendations.append(
                    f"Investigate {transaction_id}: "
                    "ledger/settlement evidence exists "
                    "without a corresponding payment."
                )

        return recommendations