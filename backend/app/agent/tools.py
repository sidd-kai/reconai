from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from scripts.verify_audit_chain import verify_audit_chain

from backend.app.agent.schemas import (
    BatchSummary,
    ExceptionSummary,
    FinanceOpsException,
    FinanceOpsSummary,
    InvestigationResult,
)


RESULTS_FILE = Path(
    "data/results/reconciliation_results.json"
)

EXCEPTIONS_FILE = Path(
    "data/results/exceptions.jsonl"
)

AUDIT_FILE = Path(
    "data/results/audit.jsonl"
)


# ======================================================================
# LOADING
# ======================================================================


def _load_reconciliation_results() -> list[dict[str, Any]]:
    """
    Load deterministic reconciliation results.
    """

    if not RESULTS_FILE.exists():
        raise FileNotFoundError(
            f"Reconciliation results not found: "
            f"{RESULTS_FILE}"
        )

    with RESULTS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(
        payload,
        list,
    ):
        raise ValueError(
            "Reconciliation results must contain "
            "a JSON array."
        )

    results: list[
        dict[str, Any]
    ] = []

    for index, record in enumerate(
        payload,
        start=1,
    ):
        if not isinstance(
            record,
            dict,
        ):
            raise ValueError(
                f"Invalid reconciliation result at "
                f"index {index}: expected object."
            )

        results.append(
            record
        )

    return results


def _load_exception_events() -> list[dict[str, Any]]:
    """
    Load append-only exception events.
    """

    if not EXCEPTIONS_FILE.exists():
        return []

    events: list[
        dict[str, Any]
    ] = []

    with EXCEPTIONS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            if not line.strip():
                continue

            try:
                record = json.loads(
                    line
                )
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid exception JSON at "
                    f"line {line_number}: {exc}"
                ) from exc

            if not isinstance(
                record,
                dict,
            ):
                raise ValueError(
                    f"Invalid exception record at "
                    f"line {line_number}: expected object."
                )

            events.append(
                record
            )

    return events


# ======================================================================
# NORMALIZATION
# ======================================================================


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Safely normalize arbitrary numeric input.
    """

    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return default


def _normalize_transaction_id(
    record: dict[str, Any],
) -> str | None:
    """
    Extract a valid transaction ID.
    """

    value = record.get(
        "transaction_id"
    )

    if value is None:
        return None

    transaction_id = str(
        value
    ).strip()

    if not transaction_id:
        return None

    return transaction_id


# ======================================================================
# CANONICAL / SUPPLEMENTAL PARTITION
# ======================================================================


def _partition_reconciliation_results(
    results: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """
    Partition reconciliation rows into:

        canonical decisions
        supplemental source-level events

    Engine contract:

        The first emitted result for transaction_id is the canonical
        transaction decision.

        Later rows using the same transaction_id represent additional
        source-level evidence/events.

    Example:

        txn_00180 -> AMBIGUOUS
        txn_00180 -> MISSING_PAYMENT ledger_00180_ALT

    Canonical transaction metrics must use ONLY the first decision.
    Supplemental rows remain visible but do not alter the match-rate
    denominator.
    """

    seen_transaction_ids: set[
        str
    ] = set()

    canonical: list[
        dict[str, Any]
    ] = []

    supplemental: list[
        dict[str, Any]
    ] = []

    for record in results:
        transaction_id = (
            _normalize_transaction_id(
                record
            )
        )

        if transaction_id is None:
            raise ValueError(
                "Reconciliation result missing "
                "transaction_id."
            )

        if (
            transaction_id
            in seen_transaction_ids
        ):
            supplemental.append(
                record
            )

            continue

        seen_transaction_ids.add(
            transaction_id
        )

        canonical.append(
            record
        )

    return (
        canonical,
        supplemental,
    )


def _load_canonical_results() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """
    Convenience loader returning canonical + supplemental rows.
    """

    results = (
        _load_reconciliation_results()
    )

    return (
        _partition_reconciliation_results(
            results
        )
    )


# ======================================================================
# BATCH RECONCILIATION SUMMARY
# ======================================================================


def reconcile_batch() -> dict[str, Any]:
    """
    Inspect the current reconciliation batch.

    Financial KPIs are transaction-level metrics.

    Supplemental source-level events are explicitly reported but
    excluded from records_processed and match-rate calculations.
    """

    raw_results = (
        _load_reconciliation_results()
    )

    (
        canonical_results,
        supplemental_results,
    ) = _partition_reconciliation_results(
        raw_results
    )

    status_counts = Counter(
        str(
            result.get(
                "status",
                "UNKNOWN",
            )
        )
        for result
        in canonical_results
    )

    matched = (
        status_counts.get(
            "MATCHED",
            0,
        )
        + status_counts.get(
            "FUZZY_MATCHED",
            0,
        )
    )

    records_processed = len(
        canonical_results
    )

    exceptions = (
        records_processed
        - matched
    )

    return {
        "records_processed": (
            records_processed
        ),
        "matched": (
            matched
        ),
        "exceptions": (
            exceptions
        ),
        "raw_result_rows": len(
            raw_results
        ),
        "supplemental_source_events": len(
            supplemental_results
        ),
        "status_breakdown": dict(
            sorted(
                status_counts.items()
            )
        ),
    }


def get_batch_summary() -> BatchSummary:
    """
    Build deterministic canonical transaction-level batch metrics.
    """

    results = (
        reconcile_batch()
    )

    records_processed = int(
        results[
            "records_processed"
        ]
    )

    matched = int(
        results[
            "matched"
        ]
    )

    exceptions = int(
        results[
            "exceptions"
        ]
    )

    raw_result_rows = int(
        results[
            "raw_result_rows"
        ]
    )

    supplemental_source_events = int(
        results[
            "supplemental_source_events"
        ]
    )

    match_rate = (
        matched
        / records_processed
        if records_processed
        else 0.0
    )

    exception_rate = (
        exceptions
        / records_processed
        if records_processed
        else 0.0
    )

    breakdown = tuple(
        ExceptionSummary(
            status=status,
            count=int(
                count
            ),
        )
        for (
            status,
            count,
        ) in sorted(
            results[
                "status_breakdown"
            ].items()
        )
        if status
        not in {
            "MATCHED",
            "FUZZY_MATCHED",
        }
    )

    audit_result = (
        verify_audit_chain(
            AUDIT_FILE
        )
    )

    return BatchSummary(
        batch_id=(
            "reconciliation-current"
        ),
        records_processed=(
            records_processed
        ),
        matched=(
            matched
        ),
        exceptions=(
            exceptions
        ),
        match_rate=(
            match_rate
        ),
        exception_rate=(
            exception_rate
        ),
        exception_breakdown=(
            breakdown
        ),
        audit_chain_verified=(
            audit_result.verified
        ),
        raw_result_rows=(
            raw_result_rows
        ),
        supplemental_source_events=(
            supplemental_source_events
        ),
    )


# ======================================================================
# EXCEPTION MANIFEST
# ======================================================================


def get_exception_manifest() -> list[dict[str, Any]]:
    """
    Return latest append-only exception state per transaction ID.

    This tool exposes manifest state and therefore may represent
    supplemental source-level evidence.

    For canonical finance metrics and ranking, use the canonical
    reconciliation results instead.
    """

    events = (
        _load_exception_events()
    )

    latest_by_transaction: dict[
        str,
        dict[str, Any],
    ] = {}

    for event in events:
        transaction_id = (
            _normalize_transaction_id(
                event
            )
        )

        if transaction_id is None:
            continue

        latest_by_transaction[
            transaction_id
        ] = event

    return list(
        latest_by_transaction.values()
    )


# ======================================================================
# INVESTIGATION
# ======================================================================


def investigate_exception(
    transaction_id: str,
) -> InvestigationResult:
    """
    Investigate the canonical decision for one transaction.

    Supplemental source events remain available through the
    exception manifest but do not replace the canonical decision.
    """

    (
        canonical_results,
        _,
    ) = _load_canonical_results()

    matching_results = [
        result
        for result
        in canonical_results
        if str(
            result.get(
                "transaction_id"
            )
        )
        == transaction_id
    ]

    if not matching_results:
        raise ValueError(
            f"Transaction not found: "
            f"{transaction_id}"
        )

    result = (
        matching_results[0]
    )

    evidence = {
        key: value
        for (
            key,
            value,
        ) in result.items()
        if key
        not in {
            "transaction_id",
            "status",
            "reason",
            "confidence",
            "payment_id",
            "ledger_id",
            "settlement_id",
            "amount_difference",
        }
    }

    return InvestigationResult(
        transaction_id=(
            transaction_id
        ),
        status=str(
            result.get(
                "status",
                "UNKNOWN",
            )
        ),
        reason=str(
            result.get(
                "reason",
                "No reason provided.",
            )
        ),
        confidence=_safe_float(
            result.get(
                "confidence",
                0.0,
            )
        ),
        payment_id=(
            result.get(
                "payment_id"
            )
        ),
        ledger_id=(
            result.get(
                "ledger_id"
            )
        ),
        settlement_id=(
            result.get(
                "settlement_id"
            )
        ),
        amount_difference=_safe_float(
            result.get(
                "amount_difference",
                0.0,
            )
        ),
        candidate_count=int(
            result.get(
                "candidate_count",
                0,
            )
        ),
        evidence=(
            evidence
        ),
    )


# ======================================================================
# HIGH-VALUE CANONICAL EXCEPTIONS
# ======================================================================


def get_high_value_exceptions(
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Return canonical unresolved transactions ordered by
    absolute financial amount difference.

    Supplemental source events are intentionally excluded.
    """

    if limit <= 0:
        return []

    (
        canonical_results,
        _,
    ) = _load_canonical_results()

    exceptions = [
        result
        for result
        in canonical_results
        if str(
            result.get(
                "status",
                "",
            )
        )
        not in {
            "MATCHED",
            "FUZZY_MATCHED",
        }
    ]

    sorted_exceptions = sorted(
        exceptions,
        key=lambda record: abs(
            _safe_float(
                record.get(
                    "amount_difference",
                    0.0,
                )
            )
        ),
        reverse=True,
    )

    return (
        sorted_exceptions[
            :limit
        ]
    )


# ======================================================================
# FINANCE OPS SUMMARY
# ======================================================================


def get_finance_ops_summary(
    limit: int = 5,
) -> FinanceOpsSummary:
    """
    Return deterministic finance operations attention summary.

    Canonical transaction metrics:
        records_processed
        matched
        exceptions
        match_rate
        exception_rate

    Supplemental source events are explicitly reported separately.
    """

    if limit <= 0:
        limit = 1

    batch = (
        get_batch_summary()
    )

    top_records = (
        get_high_value_exceptions(
            limit=limit
        )
    )

    top_exceptions: list[
        FinanceOpsException
    ] = []

    for record in top_records:
        amount_difference = (
            _safe_float(
                record.get(
                    "amount_difference",
                    0.0,
                )
            )
        )

        top_exceptions.append(
            FinanceOpsException(
                transaction_id=str(
                    record.get(
                        "transaction_id",
                        "",
                    )
                ),
                status=str(
                    record.get(
                        "status",
                        "UNKNOWN",
                    )
                ),
                amount_difference=(
                    amount_difference
                ),
                confidence=_safe_float(
                    record.get(
                        "confidence",
                        0.0,
                    )
                ),
                reason=str(
                    record.get(
                        "reason",
                        "No reason provided.",
                    )
                ),
                payment_id=(
                    record.get(
                        "payment_id"
                    )
                ),
                ledger_id=(
                    record.get(
                        "ledger_id"
                    )
                ),
                settlement_id=(
                    record.get(
                        "settlement_id"
                    )
                ),
            )
        )

    highest_financial_impact = (
        abs(
            top_exceptions[
                0
            ].amount_difference
        )
        if top_exceptions
        else 0.0
    )

    return FinanceOpsSummary(
        records_processed=(
            batch.records_processed
        ),
        matched=(
            batch.matched
        ),
        exceptions=(
            batch.exceptions
        ),
        match_rate=(
            batch.match_rate
        ),
        exception_rate=(
            batch.exception_rate
        ),
        highest_financial_impact=(
            highest_financial_impact
        ),
        top_exceptions=tuple(
            top_exceptions
        ),
        exception_breakdown=(
            batch.exception_breakdown
        ),
        audit_verified=(
            batch.audit_chain_verified
        ),
        raw_result_rows=(
            batch.raw_result_rows
        ),
        supplemental_source_events=(
            batch.supplemental_source_events
        ),
    )


# ======================================================================
# AUDIT
# ======================================================================


def get_audit_record_count() -> int:
    """
    Return number of non-empty immutable audit records.
    """

    if not AUDIT_FILE.exists():
        return 0

    count = 0

    with AUDIT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            if line.strip():
                count += 1

    return count


def verify_audit_chain_tool() -> dict[str, Any]:
    """
    Cryptographically verify the immutable audit hash chain.
    """

    result = (
        verify_audit_chain(
            AUDIT_FILE
        )
    )

    return {
        "verified": (
            result.verified
        ),
        "records_verified": (
            result.records_verified
        ),
        "error": (
            result.error
        ),
    }


# ======================================================================
# SERIALIZATION
# ======================================================================


def serialize_dataclass(
    value: Any,
) -> dict[str, Any]:
    """
    Convert an agent dataclass into a JSON-safe dictionary.
    """

    if not hasattr(
        value,
        "__dataclass_fields__",
    ):
        raise TypeError(
            "serialize_dataclass expects "
            "a dataclass instance."
        )

    return asdict(
        value
    )