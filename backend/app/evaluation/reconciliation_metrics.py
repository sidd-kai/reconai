from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


MATCHED_STATUS = "MATCHED"


@dataclass(frozen=True)
class LoadedRecords:
    records: dict[str, dict[str, Any]]
    total_rows: int
    malformed_rows: int
    duplicate_transaction_ids: tuple[str, ...]


@dataclass(frozen=True)
class DuplicateMatchReport:
    payment_ids: tuple[str, ...]
    ledger_ids: tuple[str, ...]
    settlement_ids: tuple[str, ...]

    @property
    def total_duplicate_groups(self) -> int:
        return (
            len(self.payment_ids)
            + len(self.ledger_ids)
            + len(self.settlement_ids)
        )


@dataclass(frozen=True)
class ExceptionManifestReport:
    expected_exceptions: int
    manifest_exceptions: int
    missing_transaction_ids: tuple[str, ...]
    orphan_transaction_ids: tuple[str, ...]

    @property
    def coverage_rate(self) -> float:
        if self.expected_exceptions == 0:
            return 1.0

        covered = (
            self.expected_exceptions
            - len(self.missing_transaction_ids)
        )

        return covered / self.expected_exceptions


@dataclass(frozen=True)
class ReconciliationEvaluation:
    ground_truth_rows: int
    prediction_rows: int
    evaluated_transactions: int

    malformed_ground_truth_rows: int
    malformed_prediction_rows: int

    duplicate_ground_truth_transaction_ids: tuple[str, ...]
    duplicate_prediction_transaction_ids: tuple[str, ...]

    missing_predictions: tuple[str, ...]
    unexpected_predictions: tuple[str, ...]

    status_correct: int
    status_accuracy: float

    match_true_positive: int
    match_false_positive: int
    match_false_negative: int
    match_true_negative: int

    match_precision: float
    match_recall: float
    match_f1: float

    linkage_true_positive: int
    linkage_false_positive: int
    linkage_false_negative: int

    linkage_precision: float
    linkage_recall: float
    linkage_f1: float

    wrong_linkage_transaction_ids: tuple[str, ...]

    duplicate_matches: DuplicateMatchReport

    exception_manifest: ExceptionManifestReport | None

    integrity_passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_divide(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def _f1_score(
    precision: float,
    recall: float,
) -> float:
    denominator = precision + recall

    if denominator == 0.0:
        return 0.0

    return (
        2.0
        * precision
        * recall
        / denominator
    )


def _normalize_status(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(value).strip().upper()


def _extract_transaction_id(
    record: dict[str, Any],
) -> str | None:
    value = record.get("transaction_id")

    if value is None:
        return None

    transaction_id = str(value).strip()

    if not transaction_id:
        return None

    return transaction_id


def _extract_status(
    record: dict[str, Any],
    *,
    ground_truth: bool,
) -> str:
    if ground_truth:
        value = record.get(
            "expected_status",
            record.get("status"),
        )
    else:
        value = record.get("status")

    return _normalize_status(value)


def _extract_expected_id(
    record: dict[str, Any],
    field_name: str,
) -> Any:
    expected_name = f"expected_{field_name}"

    if expected_name in record:
        return record.get(expected_name)

    return record.get(field_name)


def _load_json_or_jsonl(
    path: Path,
) -> list[Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    if path.suffix.lower() == ".jsonl":
        rows: list[Any] = []

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
                    rows.append(
                        json.loads(line)
                    )
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL at "
                        f"{path}:{line_number}: {exc}"
                    ) from exc

        return rows

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in (
            "records",
            "transactions",
            "ground_truth",
            "results",
        ):
            value = payload.get(key)

            if isinstance(value, list):
                return value

    raise ValueError(
        f"Expected a JSON array or JSONL file: {path}"
    )


def load_records(
    path: Path,
    *,
    ground_truth: bool,
) -> LoadedRecords:
    rows = _load_json_or_jsonl(path)

    records: dict[
        str,
        dict[str, Any],
    ] = {}

    malformed_rows = 0

    duplicate_transaction_ids: set[str] = set()

    for row in rows:
        if not isinstance(row, dict):
            malformed_rows += 1
            continue

        transaction_id = _extract_transaction_id(
            row
        )

        status = _extract_status(
            row,
            ground_truth=ground_truth,
        )

        if (
            transaction_id is None
            or not status
        ):
            malformed_rows += 1
            continue

        if transaction_id in records:
            duplicate_transaction_ids.add(
                transaction_id
            )

            # Never silently overwrite duplicate records.
            continue

        records[transaction_id] = row

    return LoadedRecords(
        records=records,
        total_rows=len(rows),
        malformed_rows=malformed_rows,
        duplicate_transaction_ids=tuple(
            sorted(
                duplicate_transaction_ids
            )
        ),
    )


def _matched_linkage_is_correct(
    prediction: dict[str, Any],
    truth: dict[str, Any],
) -> bool:
    """
    Compare deterministic linkage identifiers.

    A correct MATCHED result must point to the same
    source records as the benchmark ground truth.
    """

    fields = (
        "payment_id",
        "ledger_id",
        "settlement_id",
    )

    for field_name in fields:
        predicted_value = prediction.get(
            field_name
        )

        expected_value = _extract_expected_id(
            truth,
            field_name,
        )

        if predicted_value != expected_value:
            return False

    return True


def _find_duplicate_values(
    records: dict[str, dict[str, Any]],
    field_name: str,
) -> tuple[str, ...]:
    consumers: dict[
        str,
        list[str],
    ] = {}

    for transaction_id, record in records.items():
        status = _extract_status(
            record,
            ground_truth=False,
        )

        if status != MATCHED_STATUS:
            continue

        raw_value = record.get(
            field_name
        )

        if raw_value is None:
            continue

        value = str(raw_value).strip()

        if not value:
            continue

        consumers.setdefault(
            value,
            [],
        ).append(
            transaction_id
        )

    duplicates = [
        value
        for value, transaction_ids
        in consumers.items()
        if len(transaction_ids) > 1
    ]

    return tuple(
        sorted(
            duplicates
        )
    )


def find_duplicate_matches(
    predictions: dict[str, dict[str, Any]],
) -> DuplicateMatchReport:
    """
    Detect silent reuse of source records.

    A source payment, ledger record, or settlement must not
    be consumed by multiple MATCHED transactions.
    """

    return DuplicateMatchReport(
        payment_ids=_find_duplicate_values(
            predictions,
            "payment_id",
        ),
        ledger_ids=_find_duplicate_values(
            predictions,
            "ledger_id",
        ),
        settlement_ids=_find_duplicate_values(
            predictions,
            "settlement_id",
        ),
    )


def evaluate_exception_manifest(
    predictions: dict[str, dict[str, Any]],
    exception_path: Path,
) -> ExceptionManifestReport:
    """
    Verify that every predicted exception is represented
    in the append-only exception manifest.

    Historical duplicate events are reduced to their latest
    state by transaction_id.
    """

    rows = _load_json_or_jsonl(
        exception_path
    )

    latest: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in rows:
        if not isinstance(row, dict):
            continue

        transaction_id = _extract_transaction_id(
            row
        )

        if transaction_id is None:
            continue

        latest[transaction_id] = row

    expected_exception_ids = {
        transaction_id
        for transaction_id, record
        in predictions.items()
        if _extract_status(
            record,
            ground_truth=False,
        )
        != MATCHED_STATUS
    }

    manifest_exception_ids = {
        transaction_id
        for transaction_id, record
        in latest.items()
        if _extract_status(
            record,
            ground_truth=False,
        )
        != MATCHED_STATUS
    }

    missing = (
        expected_exception_ids
        - manifest_exception_ids
    )

    orphan = (
        manifest_exception_ids
        - expected_exception_ids
    )

    return ExceptionManifestReport(
        expected_exceptions=len(
            expected_exception_ids
        ),
        manifest_exceptions=len(
            manifest_exception_ids
        ),
        missing_transaction_ids=tuple(
            sorted(
                missing
            )
        ),
        orphan_transaction_ids=tuple(
            sorted(
                orphan
            )
        ),
    )


def evaluate_reconciliation(
    *,
    predictions_path: Path,
    ground_truth_path: Path,
    exception_path: Path | None = None,
) -> ReconciliationEvaluation:
    predictions_loaded = load_records(
        predictions_path,
        ground_truth=False,
    )

    truth_loaded = load_records(
        ground_truth_path,
        ground_truth=True,
    )

    predictions = predictions_loaded.records
    truth = truth_loaded.records

    prediction_ids = set(
        predictions
    )

    truth_ids = set(
        truth
    )

    missing_predictions = tuple(
        sorted(
            truth_ids
            - prediction_ids
        )
    )

    unexpected_predictions = tuple(
        sorted(
            prediction_ids
            - truth_ids
        )
    )

    common_ids = sorted(
        truth_ids
        & prediction_ids
    )

    status_correct = 0

    match_tp = 0
    match_fp = 0
    match_fn = 0
    match_tn = 0

    linkage_tp = 0
    linkage_fp = 0
    linkage_fn = 0

    wrong_linkage_ids: list[str] = []

    for transaction_id in common_ids:
        predicted = predictions[
            transaction_id
        ]

        expected = truth[
            transaction_id
        ]

        predicted_status = _extract_status(
            predicted,
            ground_truth=False,
        )

        expected_status = _extract_status(
            expected,
            ground_truth=True,
        )

        predicted_matched = (
            predicted_status
            == MATCHED_STATUS
        )

        expected_matched = (
            expected_status
            == MATCHED_STATUS
        )

        if predicted_status == expected_status:
            status_correct += 1

        # ----------------------------------------------------------
        # MATCHED classification metrics
        # ----------------------------------------------------------

        if predicted_matched and expected_matched:
            match_tp += 1

        elif (
            predicted_matched
            and not expected_matched
        ):
            match_fp += 1

        elif (
            not predicted_matched
            and expected_matched
        ):
            match_fn += 1

        else:
            match_tn += 1

        # ----------------------------------------------------------
        # Linkage correctness metrics
        # ----------------------------------------------------------

        if expected_matched:
            if predicted_matched:
                linkage_correct = (
                    _matched_linkage_is_correct(
                        predicted,
                        expected,
                    )
                )

                if linkage_correct:
                    linkage_tp += 1
                else:
                    # Wrong linkage is both an incorrect positive
                    # and a missed correct linkage.
                    linkage_fp += 1
                    linkage_fn += 1

                    wrong_linkage_ids.append(
                        transaction_id
                    )
            else:
                linkage_fn += 1

        elif predicted_matched:
            linkage_fp += 1

    # Ground-truth records that have no prediction are false
    # negatives when the expected result is MATCHED.
    for transaction_id in missing_predictions:
        expected = truth[
            transaction_id
        ]

        expected_status = _extract_status(
            expected,
            ground_truth=True,
        )

        if expected_status == MATCHED_STATUS:
            match_fn += 1
            linkage_fn += 1

    match_precision = _safe_divide(
        match_tp,
        match_tp + match_fp,
    )

    match_recall = _safe_divide(
        match_tp,
        match_tp + match_fn,
    )

    match_f1 = _f1_score(
        match_precision,
        match_recall,
    )

    linkage_precision = _safe_divide(
        linkage_tp,
        linkage_tp + linkage_fp,
    )

    linkage_recall = _safe_divide(
        linkage_tp,
        linkage_tp + linkage_fn,
    )

    linkage_f1 = _f1_score(
        linkage_precision,
        linkage_recall,
    )

    status_accuracy = _safe_divide(
        status_correct,
        len(common_ids),
    )

    duplicate_matches = (
        find_duplicate_matches(
            predictions
        )
    )

    manifest_report: (
        ExceptionManifestReport
        | None
    ) = None

    if exception_path is not None:
        manifest_report = (
            evaluate_exception_manifest(
                predictions,
                exception_path,
            )
        )

    manifest_integrity = True

    if manifest_report is not None:
        manifest_integrity = (
            not manifest_report
            .missing_transaction_ids
            and not manifest_report
            .orphan_transaction_ids
        )

    integrity_passed = all(
        (
            predictions_loaded
            .malformed_rows
            == 0,

            truth_loaded
            .malformed_rows
            == 0,

            not predictions_loaded
            .duplicate_transaction_ids,

            not truth_loaded
            .duplicate_transaction_ids,

            not missing_predictions,

            not unexpected_predictions,

            duplicate_matches
            .total_duplicate_groups
            == 0,

            manifest_integrity,
        )
    )

    return ReconciliationEvaluation(
        ground_truth_rows=(
            truth_loaded.total_rows
        ),
        prediction_rows=(
            predictions_loaded.total_rows
        ),
        evaluated_transactions=len(
            common_ids
        ),
        malformed_ground_truth_rows=(
            truth_loaded.malformed_rows
        ),
        malformed_prediction_rows=(
            predictions_loaded.malformed_rows
        ),
        duplicate_ground_truth_transaction_ids=(
            truth_loaded
            .duplicate_transaction_ids
        ),
        duplicate_prediction_transaction_ids=(
            predictions_loaded
            .duplicate_transaction_ids
        ),
        missing_predictions=(
            missing_predictions
        ),
        unexpected_predictions=(
            unexpected_predictions
        ),
        status_correct=status_correct,
        status_accuracy=status_accuracy,
        match_true_positive=match_tp,
        match_false_positive=match_fp,
        match_false_negative=match_fn,
        match_true_negative=match_tn,
        match_precision=match_precision,
        match_recall=match_recall,
        match_f1=match_f1,
        linkage_true_positive=linkage_tp,
        linkage_false_positive=linkage_fp,
        linkage_false_negative=linkage_fn,
        linkage_precision=linkage_precision,
        linkage_recall=linkage_recall,
        linkage_f1=linkage_f1,
        wrong_linkage_transaction_ids=tuple(
            sorted(
                wrong_linkage_ids
            )
        ),
        duplicate_matches=duplicate_matches,
        exception_manifest=manifest_report,
        integrity_passed=integrity_passed,
    )