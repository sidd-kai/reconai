from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT / "data" / "results"

EVALUATION_FILE = RESULTS_DIR / "reconciliation_evaluation.json"
BENCHMARK_FILE = RESULTS_DIR / "reconciliation_engine_benchmark.json"
EXCEPTION_FILE = RESULTS_DIR / "exceptions.jsonl"
AUDIT_FILE = RESULTS_DIR / "audit.jsonl"

RAZORPAY_PAYMENT_FILE = (
    RESULTS_DIR / "razorpay_webhook_payments.jsonl"
)

RAZORPAY_EVENT_FILE = (
    RESULTS_DIR / "razorpay_webhook_events.jsonl"
)


TRANSACTION_ID_KEYS = {
    "transaction_id",
    "txn_id",
}


class DashboardDataError(RuntimeError):
    """Raised when deterministic dashboard evidence cannot be loaded."""


class DashboardItemNotFoundError(
    DashboardDataError
):
    """Raised when a requested dashboard entity does not exist."""


def _read_json(
    path: Path,
) -> dict[str, Any]:
    if not path.exists():
        raise DashboardDataError(
            f"Required artifact does not exist: {path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            payload = json.load(
                file
            )
    except json.JSONDecodeError as exc:
        raise DashboardDataError(
            f"Malformed JSON artifact: {path}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise DashboardDataError(
            f"Expected JSON object in: {path}"
        )

    return payload


def _read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[
        dict[str, Any]
    ] = []

    with path.open(
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
                raise DashboardDataError(
                    "Malformed JSONL record "
                    f"in {path} at line "
                    f"{line_number}."
                ) from exc

            if not isinstance(
                record,
                dict,
            ):
                raise DashboardDataError(
                    "Expected JSON object "
                    f"in {path} at line "
                    f"{line_number}."
                )

            records.append(
                record
            )

    return records


def _latest_exception_state(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    latest: dict[
        str,
        dict[str, Any],
    ] = {}

    for record in records:
        transaction_id = str(
            record.get(
                "transaction_id",
                "",
            )
        ).strip()

        if not transaction_id:
            continue

        latest[
            transaction_id
        ] = record

    return list(
        latest.values()
    )


def _extract_amount_difference(
    record: dict[str, Any],
) -> float:
    value = record.get(
        "amount_difference"
    )

    if value is None:
        evidence = record.get(
            "evidence"
        )

        if isinstance(
            evidence,
            dict,
        ):
            value = evidence.get(
                "amount_difference"
            )

    try:
        return float(
            value
            or 0.0
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def _normalize_confidence(
    value: Any,
) -> float:
    try:
        return float(
            value
            or 0.0
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def _record_contains_transaction_id(
    value: Any,
    *,
    transaction_id: str,
) -> bool:
    """
    Find a transaction ID inside nested immutable audit records.

    Audit entries may wrap the reconciliation result inside structures
    such as:
        payload
        data
        result
        evidence
        match_result

    We deliberately only treat values attached to transaction-ID keys
    as a transaction association. We do not search arbitrary prose.
    """

    if isinstance(
        value,
        dict,
    ):
        for key, nested_value in value.items():
            normalized_key = str(
                key
            ).strip().lower()

            if (
                normalized_key
                in TRANSACTION_ID_KEYS
                and str(
                    nested_value
                ).strip()
                == transaction_id
            ):
                return True

            if _record_contains_transaction_id(
                nested_value,
                transaction_id=transaction_id,
            ):
                return True

        return False

    if isinstance(
        value,
        list,
    ):
        return any(
            _record_contains_transaction_id(
                item,
                transaction_id=transaction_id,
            )
            for item in value
        )

    return False


def _recommended_action(
    status: str,
) -> str:
    actions = {
        "AMOUNT_MISMATCH": (
            "Compare payment and ledger amounts and verify whether "
            "the discrepancy represents a fee, adjustment, refund, "
            "or posting error. Do not auto-resolve until the source "
            "amount is confirmed."
        ),
        "MISSING_PAYMENT": (
            "Verify payment-source ingestion and search the payment "
            "provider using available order, ledger, or settlement "
            "references before creating any manual adjustment."
        ),
        "MISSING_LEDGER": (
            "Verify whether the merchant ledger entry was delayed, "
            "rejected, or never posted. Re-run reconciliation after "
            "ledger evidence becomes available."
        ),
        "DUPLICATE": (
            "Review every competing source identifier and timestamp. "
            "Do not silently select one duplicate candidate."
        ),
        "SETTLEMENT_MISMATCH": (
            "Compare gross amount, fee, tax, and net settlement values "
            "against payment and ledger evidence before approval."
        ),
        "AMBIGUOUS": (
            "Inspect every competing candidate record and source ID. "
            "Human review is required because deterministic evidence "
            "does not identify one uniquely safe match."
        ),
        "UNRESOLVED": (
            "Review available source evidence manually and obtain "
            "missing identifiers or financial records before resolution."
        ),
    }

    return actions.get(
        status,
        (
            "Review deterministic source evidence before making "
            "any financial adjustment."
        ),
    )


def _normalize_exception(
    record: dict[str, Any],
) -> dict[str, Any]:
    evidence = record.get(
        "evidence",
        {},
    )

    if not isinstance(
        evidence,
        dict,
    ):
        evidence = {}

    status = str(
        record.get(
            "status",
            "UNKNOWN",
        )
    ).strip().upper()

    return {
        "transaction_id": record.get(
            "transaction_id"
        ),
        "status": status,
        "reason": record.get(
            "reason"
        ),
        "method": record.get(
            "method"
        ),
        "confidence": _normalize_confidence(
            record.get(
                "confidence"
            )
        ),
        "amount_difference": _extract_amount_difference(
            record
        ),
        "evidence": evidence,
    }


class DashboardService:
    """
    Read-only deterministic finance dashboard service.

    This layer exposes persisted evidence only.

    It does not:
        - mutate finance state
        - reconcile transactions
        - invoke an LLM
        - fabricate missing evidence
    """

    def get_summary(
        self,
    ) -> dict[str, Any]:
        evaluation = _read_json(
            EVALUATION_FILE
        )

        return {
            "canonical_transactions": int(
                evaluation.get(
                    "canonical_transactions",
                    0,
                )
            ),
            "raw_decisions": int(
                evaluation.get(
                    "engine_decisions_raw",
                    0,
                )
            ),
            "supplemental_events": int(
                evaluation.get(
                    "supplemental_result_count",
                    0,
                )
            ),
            "resolved": int(
                evaluation.get(
                    "resolved_count",
                    0,
                )
            ),
            "exceptions": int(
                evaluation.get(
                    "exception_count",
                    0,
                )
            ),
            "match_rate": float(
                evaluation.get(
                    "automatic_match_rate",
                    0.0,
                )
            ),
            "exception_rate": float(
                evaluation.get(
                    "exception_rate",
                    0.0,
                )
            ),
            "classification_accuracy": float(
                evaluation.get(
                    "classification_accuracy",
                    0.0,
                )
            ),
            "precision": float(
                evaluation.get(
                    "precision",
                    0.0,
                )
            ),
            "recall": float(
                evaluation.get(
                    "recall",
                    0.0,
                )
            ),
            "f1": float(
                evaluation.get(
                    "f1",
                    0.0,
                )
            ),
            "linkage_precision": float(
                evaluation.get(
                    "linkage_precision",
                    0.0,
                )
            ),
            "linkage_recall": float(
                evaluation.get(
                    "linkage_recall",
                    0.0,
                )
            ),
            "linkage_f1": float(
                evaluation.get(
                    "linkage_f1",
                    0.0,
                )
            ),
            "unsafe_duplicate_resolutions": len(
                evaluation.get(
                    "unsafe_duplicate_decisions",
                    [],
                )
            ),
            "integrity_passed": bool(
                evaluation.get(
                    "integrity_passed",
                    False,
                )
            ),
        }

    def get_benchmark(
        self,
    ) -> dict[str, Any]:
        benchmark = _read_json(
            BENCHMARK_FILE
        )

        results = benchmark.get(
            "results",
            {},
        )

        latency = benchmark.get(
            "latency_seconds",
            {},
        )

        throughput = benchmark.get(
            "throughput",
            {},
        )

        if not isinstance(
            results,
            dict,
        ):
            results = {}

        if not isinstance(
            latency,
            dict,
        ):
            latency = {}

        if not isinstance(
            throughput,
            dict,
        ):
            throughput = {}

        return {
            "canonical_transactions": int(
                results.get(
                    "canonical_transactions",
                    0,
                )
            ),
            "raw_decisions": int(
                results.get(
                    "raw_decisions",
                    0,
                )
            ),
            "resolved": int(
                results.get(
                    "resolved",
                    0,
                )
            ),
            "exceptions": int(
                results.get(
                    "exceptions",
                    0,
                )
            ),
            "match_rate": float(
                results.get(
                    "match_rate",
                    0.0,
                )
            ),
            "median_latency_seconds": float(
                latency.get(
                    "median",
                    0.0,
                )
            ),
            "mean_latency_seconds": float(
                latency.get(
                    "mean",
                    0.0,
                )
            ),
            "median_records_per_second": float(
                throughput.get(
                    "canonical_records_per_second_median",
                    0.0,
                )
            ),
            "mean_records_per_second": float(
                throughput.get(
                    "canonical_records_per_second_mean",
                    0.0,
                )
            ),
            "median_decisions_per_second": float(
                throughput.get(
                    "raw_decisions_per_second_median",
                    0.0,
                )
            ),
            "deterministic_across_runs": bool(
                benchmark.get(
                    "deterministic_across_runs",
                    False,
                )
            ),
            "integrity_passed": bool(
                benchmark.get(
                    "integrity_passed",
                    False,
                )
            ),
        }

    def get_exceptions(
        self,
    ) -> dict[str, Any]:
        historical_records = _read_jsonl(
            EXCEPTION_FILE
        )

        current = _latest_exception_state(
            historical_records
        )

        status_counts = Counter(
            str(
                record.get(
                    "status",
                    "UNKNOWN",
                )
            ).strip().upper()
            for record in current
        )

        normalized = [
            _normalize_exception(
                record
            )
            for record in current
        ]

        normalized.sort(
            key=lambda item: str(
                item.get(
                    "transaction_id",
                    "",
                )
            )
        )

        return {
            "count": len(
                normalized
            ),
            "historical_event_count": len(
                historical_records
            ),
            "status_counts": dict(
                sorted(
                    status_counts.items()
                )
            ),
            "items": normalized,
        }

    def get_high_value_exceptions(
        self,
        *,
        limit: int = 10,
    ) -> dict[str, Any]:
        exceptions = self.get_exceptions()

        items = list(
            exceptions[
                "items"
            ]
        )

        items.sort(
            key=lambda item: abs(
                float(
                    item.get(
                        "amount_difference",
                        0.0,
                    )
                )
            ),
            reverse=True,
        )

        selected = items[
            :limit
        ]

        return {
            "count": len(
                selected
            ),
            "limit": limit,
            "items": selected,
        }

    def get_exception_detail(
        self,
        *,
        transaction_id: str,
    ) -> dict[str, Any]:
        transaction_id = (
            transaction_id.strip()
        )

        if not transaction_id:
            raise DashboardItemNotFoundError(
                "Transaction ID is empty."
            )

        all_exception_records = _read_jsonl(
            EXCEPTION_FILE
        )

        exception_history = [
            record
            for record in all_exception_records
            if str(
                record.get(
                    "transaction_id",
                    "",
                )
            ).strip()
            == transaction_id
        ]

        if not exception_history:
            raise DashboardItemNotFoundError(
                "No current or historical exception "
                f"found for transaction: {transaction_id}"
            )

        current_record = (
            exception_history[-1]
        )

        normalized = _normalize_exception(
            current_record
        )

        all_audit_records = _read_jsonl(
            AUDIT_FILE
        )

        audit_history = [
            record
            for record in all_audit_records
            if _record_contains_transaction_id(
                record,
                transaction_id=transaction_id,
            )
        ]

        status = str(
            normalized.get(
                "status",
                "UNKNOWN",
            )
        ).upper()

        return {
            **normalized,
            "recommended_action": _recommended_action(
                status
            ),
            "exception_history_count": len(
                exception_history
            ),
            "audit_record_count": len(
                audit_history
            ),
            "exception_history": exception_history[
                -10:
            ],
            "audit_history": audit_history[
                -10:
            ],
        }

    def get_audit_status(
        self,
    ) -> dict[str, Any]:
        audit_records = _read_jsonl(
            AUDIT_FILE
        )

        return {
            "audit_file_exists": AUDIT_FILE.exists(),
            "audit_record_count": len(
                audit_records
            ),
            "verification": (
                "AVAILABLE_VIA_AUDIT_VERIFICATION_TOOL"
            ),
        }

    def get_razorpay_status(
        self,
    ) -> dict[str, Any]:
        payments = _read_jsonl(
            RAZORPAY_PAYMENT_FILE
        )

        events = _read_jsonl(
            RAZORPAY_EVENT_FILE
        )

        status_counts: Counter[
            str
        ] = Counter()

        payment_items: list[
            dict[str, Any]
        ] = []

        for record in payments:
            reconai_payment = record.get(
                "reconai_payment",
                {},
            )

            if not isinstance(
                reconai_payment,
                dict,
            ):
                reconai_payment = {}

            payment_status = str(
                reconai_payment.get(
                    "status",
                    "UNKNOWN",
                )
            ).strip().upper()

            status_counts[
                payment_status
            ] += 1

            payment_items.append(
                {
                    "event_id": record.get(
                        "event_id"
                    ),
                    "event": record.get(
                        "event"
                    ),
                    "transaction_id": (
                        reconai_payment.get(
                            "transaction_id"
                        )
                    ),
                    "payment_id": (
                        reconai_payment.get(
                            "payment_id"
                        )
                    ),
                    "order_id": (
                        reconai_payment.get(
                            "order_id"
                        )
                    ),
                    "amount": (
                        reconai_payment.get(
                            "amount"
                        )
                    ),
                    "currency": (
                        reconai_payment.get(
                            "currency"
                        )
                    ),
                    "status": (
                        reconai_payment.get(
                            "status"
                        )
                    ),
                }
            )

        return {
            "mode": "TEST",
            "webhook_event_count": len(
                events
            ),
            "payment_evidence_count": len(
                payments
            ),
            "status_counts": dict(
                sorted(
                    status_counts.items()
                )
            ),
            "payments": payment_items[
                -10:
            ],
        }