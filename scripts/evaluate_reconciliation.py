from __future__ import annotations

import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


# ======================================================================
# PATHS
# ======================================================================

ROOT = Path(__file__).resolve().parents[1]

GROUND_TRUTH_FILE = (
    ROOT
    / "data"
    / "ground_truth"
    / "ground_truth.csv"
)

RESULT_FILE = (
    ROOT
    / "data"
    / "results"
    / "reconciliation_results.json"
)

EXCEPTION_FILE = (
    ROOT
    / "data"
    / "results"
    / "exceptions.jsonl"
)

EVALUATION_OUTPUT_FILE = (
    ROOT
    / "data"
    / "results"
    / "reconciliation_evaluation.json"
)


# ======================================================================
# BENCHMARK SEMANTICS
# ======================================================================

# Engine statuses that represent a successful automatic reconciliation.
RESOLVED_STATUSES = {
    "MATCHED",
    "FUZZY_MATCHED",
}


# Ground-truth scenarios expected to be safely reconciled.
RESOLVABLE_GROUND_TRUTH = {
    "MATCH",
    "TIMESTAMP_DRIFT",
    "REFERENCE_CORRUPTION",
}


# Engine statuses intentionally routed to exception handling.
EXCEPTION_STATUSES = {
    "AMOUNT_MISMATCH",
    "MISSING_PAYMENT",
    "MISSING_LEDGER",
    "DUPLICATE",
    "SETTLEMENT_MISMATCH",
    "AMBIGUOUS",
    "UNRESOLVED",
}


KNOWN_ENGINE_STATUSES = (
    RESOLVED_STATUSES
    | EXCEPTION_STATUSES
)


# ======================================================================
# LOADING
# ======================================================================


def load_ground_truth() -> pd.DataFrame:
    """
    Load canonical benchmark ground truth.
    """

    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError(
            f"Ground truth not found: "
            f"{GROUND_TRUTH_FILE}"
        )

    return pd.read_csv(
        GROUND_TRUTH_FILE
    )


def load_results() -> list[dict[str, Any]]:
    """
    Load reconciliation engine result rows.
    """

    if not RESULT_FILE.exists():
        raise FileNotFoundError(
            f"Reconciliation results not found: "
            f"{RESULT_FILE}"
        )

    with RESULT_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(
        payload,
        list,
    ):
        raise ValueError(
            "reconciliation_results.json "
            "must contain a JSON array."
        )

    return payload


# ======================================================================
# NORMALIZATION HELPERS
# ======================================================================


def normalize_status(
    value: Any,
) -> str:
    """
    Normalize a status string for deterministic comparisons.
    """

    if value is None:
        return ""

    return str(value).strip().upper()


def normalize_optional_id(
    value: Any,
) -> str | None:
    """
    Normalize optional payment/ledger/settlement/transaction IDs.

    Handles:
        - None
        - pandas NaN
        - empty strings
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    normalized = str(value).strip()

    if not normalized:
        return None

    return normalized


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Safely convert arbitrary input to float.
    """

    try:
        result = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default

    if math.isnan(result):
        return default

    return result


def safe_divide(
    numerator: int,
    denominator: int,
) -> float:
    """
    Divide safely.
    """

    if denominator == 0:
        return 0.0

    return numerator / denominator


def calculate_f1(
    precision: float,
    recall: float,
) -> float:
    """
    Calculate F1 score.
    """

    denominator = (
        precision
        + recall
    )

    if denominator == 0.0:
        return 0.0

    return (
        2.0
        * precision
        * recall
        / denominator
    )


# ======================================================================
# GROUND-TRUTH VALIDATION
# ======================================================================


def validate_ground_truth(
    ground_truth: pd.DataFrame,
) -> dict[str, Any]:
    """
    Validate benchmark ground-truth structural integrity.
    """

    required_columns = {
        "transaction_id",
        "expected_status",
    }

    missing_columns = (
        required_columns
        - set(
            ground_truth.columns
        )
    )

    if missing_columns:
        raise ValueError(
            "Ground truth is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    malformed_rows = 0

    transaction_ids: list[
        str
    ] = []

    for record in ground_truth.to_dict(
        orient="records"
    ):
        transaction_id = (
            normalize_optional_id(
                record.get(
                    "transaction_id"
                )
            )
        )

        expected_status = (
            normalize_status(
                record.get(
                    "expected_status"
                )
            )
        )

        if (
            transaction_id is None
            or not expected_status
        ):
            malformed_rows += 1
            continue

        transaction_ids.append(
            transaction_id
        )

    counts = Counter(
        transaction_ids
    )

    duplicate_transaction_ids = sorted(
        transaction_id
        for transaction_id, count
        in counts.items()
        if count > 1
    )

    return {
        "malformed_rows": (
            malformed_rows
        ),
        "duplicate_transaction_ids": (
            duplicate_transaction_ids
        ),
    }


# ======================================================================
# RESULT INDEXING
# ======================================================================


def build_result_index(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build the reconciliation engine result index.

    ReconAI may legitimately emit:

        1. One canonical reconciliation decision.
        2. One or more supplemental source-level exception rows.

    Example:

        txn_00180
            MATCHED
            pay_00180
            ledger_00180

        txn_00180
            MISSING_PAYMENT
            ledger_00180_ALT

    That is NOT automatically an unsafe duplicate match.

    Unsafe duplication occurs when more than one resolved decision
    exists for the same transaction.

    No repeated row is silently discarded:
        - the first row is retained as the canonical decision
        - later rows are retained as supplemental results
        - unsafe duplicate resolved decisions are explicitly reported
    """

    grouped: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    malformed_rows = 0

    unknown_statuses: set[
        str
    ] = set()

    for result in results:
        if not isinstance(
            result,
            dict,
        ):
            malformed_rows += 1
            continue

        transaction_id = (
            normalize_optional_id(
                result.get(
                    "transaction_id"
                )
            )
        )

        actual_status = (
            normalize_status(
                result.get(
                    "status"
                )
            )
        )

        if (
            transaction_id is None
            or not actual_status
        ):
            malformed_rows += 1
            continue

        if (
            actual_status
            not in KNOWN_ENGINE_STATUSES
        ):
            unknown_statuses.add(
                actual_status
            )

        grouped.setdefault(
            transaction_id,
            [],
        ).append(
            result
        )

    primary: dict[
        str,
        dict[str, Any],
    ] = {}

    supplemental: list[
        dict[str, Any]
    ] = []

    repeated_transaction_ids: list[
        str
    ] = []

    unsafe_duplicate_decisions: list[
        str
    ] = []

    for (
        transaction_id,
        transaction_rows,
    ) in grouped.items():
        if len(
            transaction_rows
        ) > 1:
            repeated_transaction_ids.append(
                transaction_id
            )

        resolved_rows = [
            row
            for row
            in transaction_rows
            if normalize_status(
                row.get(
                    "status"
                )
            )
            in RESOLVED_STATUSES
        ]

        # More than one automatic reconciliation for the same
        # transaction is unsafe.
        if len(
            resolved_rows
        ) > 1:
            unsafe_duplicate_decisions.append(
                transaction_id
            )

        # Current engine contract:
        # first emitted row is the canonical transaction decision.
        primary_row = (
            transaction_rows[0]
        )

        primary[
            transaction_id
        ] = primary_row

        # Preserve every additional source-level event.
        supplemental.extend(
            transaction_rows[1:]
        )

    return {
        "primary": (
            primary
        ),
        "supplemental": (
            supplemental
        ),
        "malformed_rows": (
            malformed_rows
        ),
        "repeated_transaction_ids": tuple(
            sorted(
                repeated_transaction_ids
            )
        ),
        "unsafe_duplicate_decisions": tuple(
            sorted(
                unsafe_duplicate_decisions
            )
        ),
        "unknown_statuses": tuple(
            sorted(
                unknown_statuses
            )
        ),
    }


# ======================================================================
# CLASSIFICATION
# ======================================================================


def classify_prediction(
    expected_status: str,
    actual_status: str,
) -> str:
    """
    Convert reconciliation output into benchmark classification.

    Returns:
        TRUE_POSITIVE
        TRUE_NEGATIVE
        FALSE_POSITIVE
        FALSE_NEGATIVE
    """

    expected_resolvable = (
        expected_status
        in RESOLVABLE_GROUND_TRUTH
    )

    actual_resolved = (
        actual_status
        in RESOLVED_STATUSES
    )

    if (
        expected_resolvable
        and actual_resolved
    ):
        return "TRUE_POSITIVE"

    if (
        not expected_resolvable
        and not actual_resolved
    ):
        return "TRUE_NEGATIVE"

    if (
        not expected_resolvable
        and actual_resolved
    ):
        return "FALSE_POSITIVE"

    return "FALSE_NEGATIVE"


# ======================================================================
# LINKAGE CORRECTNESS
# ======================================================================


def detect_ground_truth_link_fields(
    ground_truth: pd.DataFrame,
) -> dict[str, str]:
    """
    Detect source linkage columns available in ground truth.

    Supported preferred names:

        expected_payment_id
        expected_ledger_id
        expected_settlement_id

    Fallback:

        payment_id
        ledger_id
        settlement_id
    """

    available: dict[
        str,
        str,
    ] = {}

    for field_name in (
        "payment_id",
        "ledger_id",
        "settlement_id",
    ):
        expected_field = (
            f"expected_{field_name}"
        )

        if (
            expected_field
            in ground_truth.columns
        ):
            available[
                field_name
            ] = expected_field

        elif (
            field_name
            in ground_truth.columns
        ):
            available[
                field_name
            ] = field_name

    return available


def compare_linkage(
    *,
    expected_record: dict[str, Any],
    actual_record: dict[str, Any],
    link_fields: dict[str, str],
) -> bool:
    """
    Compare selected reconciliation source IDs
    against benchmark ground truth.
    """

    if not link_fields:
        return True

    for (
        actual_field,
        expected_field,
    ) in link_fields.items():
        expected_value = (
            normalize_optional_id(
                expected_record.get(
                    expected_field
                )
            )
        )

        actual_value = (
            normalize_optional_id(
                actual_record.get(
                    actual_field
                )
            )
        )

        if (
            actual_value
            != expected_value
        ):
            return False

    return True


# ======================================================================
# DUPLICATE SOURCE CONSUMPTION
# ======================================================================


def detect_duplicate_source_consumption(
    results: dict[
        str,
        dict[str, Any],
    ],
    field_name: str,
) -> dict[
    str,
    tuple[str, ...],
]:
    """
    Detect source IDs consumed by multiple resolved transactions.

    payment_id reuse:
        considered unsafe.

    ledger_id reuse:
        considered unsafe.

    settlement_id reuse:
        reported for visibility but not automatically unsafe,
        because settlements can aggregate transactions.
    """

    consumers: dict[
        str,
        list[str],
    ] = {}

    for (
        transaction_id,
        result,
    ) in results.items():
        status = (
            normalize_status(
                result.get(
                    "status"
                )
            )
        )

        if (
            status
            not in RESOLVED_STATUSES
        ):
            continue

        source_id = (
            normalize_optional_id(
                result.get(
                    field_name
                )
            )
        )

        if source_id is None:
            continue

        consumers.setdefault(
            source_id,
            [],
        ).append(
            transaction_id
        )

    return {
        source_id: tuple(
            sorted(
                transaction_ids
            )
        )
        for (
            source_id,
            transaction_ids,
        ) in sorted(
            consumers.items()
        )
        if len(
            transaction_ids
        ) > 1
    }


# ======================================================================
# EXCEPTION MANIFEST
# ======================================================================


def load_exception_manifest() -> dict[str, Any]:
    """
    Load append-only exceptions.jsonl.

    Latest state is retained per transaction_id.

    Malformed records are counted rather than silently ignored.
    """

    if not EXCEPTION_FILE.exists():
        return {
            "exists": False,
            "latest": {},
            "total_events": 0,
            "malformed_rows": 0,
        }

    latest: dict[
        str,
        dict[str, Any],
    ] = {}

    total_events = 0
    malformed_rows = 0

    with EXCEPTION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            if not line.strip():
                continue

            total_events += 1

            try:
                record = json.loads(
                    line
                )
            except json.JSONDecodeError:
                malformed_rows += 1
                continue

            if not isinstance(
                record,
                dict,
            ):
                malformed_rows += 1
                continue

            transaction_id = (
                normalize_optional_id(
                    record.get(
                        "transaction_id"
                    )
                )
            )

            status = (
                normalize_status(
                    record.get(
                        "status"
                    )
                )
            )

            if (
                transaction_id is None
                or not status
            ):
                malformed_rows += 1
                continue

            latest[
                transaction_id
            ] = record

    return {
        "exists": True,
        "latest": latest,
        "total_events": (
            total_events
        ),
        "malformed_rows": (
            malformed_rows
        ),
    }


def evaluate_exception_manifest(
    primary_results: dict[
        str,
        dict[str, Any],
    ],
    supplemental_results: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:
    """
    Evaluate current exception-manifest integrity.

    Both canonical exception decisions and supplemental
    source-level exception rows count as legitimate expected
    exception transaction IDs.

    This prevents valid supplemental exceptions from being
    incorrectly classified as orphan manifest records.
    """

    manifest = (
        load_exception_manifest()
    )

    expected_exception_ids: set[
        str
    ] = set()

    primary_exception_ids: set[
        str
    ] = set()

    supplemental_exception_ids: set[
        str
    ] = set()

    # --------------------------------------------------------------
    # Canonical exception decisions
    # --------------------------------------------------------------

    for (
        transaction_id,
        result,
    ) in primary_results.items():
        status = (
            normalize_status(
                result.get(
                    "status"
                )
            )
        )

        if (
            status
            in EXCEPTION_STATUSES
        ):
            primary_exception_ids.add(
                transaction_id
            )

            expected_exception_ids.add(
                transaction_id
            )

    # --------------------------------------------------------------
    # Supplemental source-level exceptions
    # --------------------------------------------------------------

    for result in supplemental_results:
        transaction_id = (
            normalize_optional_id(
                result.get(
                    "transaction_id"
                )
            )
        )

        status = (
            normalize_status(
                result.get(
                    "status"
                )
            )
        )

        if (
            transaction_id is not None
            and status
            in EXCEPTION_STATUSES
        ):
            supplemental_exception_ids.add(
                transaction_id
            )

            expected_exception_ids.add(
                transaction_id
            )

    manifest_latest: dict[
        str,
        dict[str, Any],
    ] = manifest[
        "latest"
    ]

    manifest_exception_ids = {
        transaction_id
        for (
            transaction_id,
            record,
        ) in manifest_latest.items()
        if normalize_status(
            record.get(
                "status"
            )
        )
        in EXCEPTION_STATUSES
    }

    missing_ids = sorted(
        expected_exception_ids
        - manifest_exception_ids
    )

    orphan_ids = sorted(
        manifest_exception_ids
        - expected_exception_ids
    )

    expected_count = len(
        expected_exception_ids
    )

    covered_count = (
        expected_count
        - len(
            missing_ids
        )
    )

    coverage_rate = (
        covered_count
        / expected_count
        if expected_count
        else 1.0
    )

    return {
        "file_exists": (
            manifest[
                "exists"
            ]
        ),
        "total_events": (
            manifest[
                "total_events"
            ]
        ),
        "malformed_rows": (
            manifest[
                "malformed_rows"
            ]
        ),
        "primary_exception_count": len(
            primary_exception_ids
        ),
        "supplemental_exception_count": len(
            supplemental_exception_ids
        ),
        "supplemental_exception_ids": sorted(
            supplemental_exception_ids
        ),
        "expected_current_exceptions": (
            expected_count
        ),
        "manifest_current_exceptions": len(
            manifest_exception_ids
        ),
        "coverage_rate": (
            coverage_rate
        ),
        "missing_transaction_ids": (
            missing_ids
        ),
        "orphan_transaction_ids": (
            orphan_ids
        ),
    }


# ======================================================================
# MAIN EVALUATION
# ======================================================================


def evaluate(
    ground_truth: pd.DataFrame,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Evaluate reconciliation output against canonical
    ground truth while separately auditing supplemental rows.
    """

    # ------------------------------------------------------------------
    # Structural validation
    # ------------------------------------------------------------------

    ground_truth_integrity = (
        validate_ground_truth(
            ground_truth
        )
    )

    result_index = (
        build_result_index(
            results
        )
    )

    primary_results: dict[
        str,
        dict[str, Any],
    ] = result_index[
        "primary"
    ]

    supplemental_results: list[
        dict[str, Any]
    ] = result_index[
        "supplemental"
    ]

    # ------------------------------------------------------------------
    # Canonical IDs
    # ------------------------------------------------------------------

    canonical_ids: set[
        str
    ] = set()

    for value in ground_truth[
        "transaction_id"
    ].tolist():
        transaction_id = (
            normalize_optional_id(
                value
            )
        )

        if transaction_id is not None:
            canonical_ids.add(
                transaction_id
            )

    engine_ids = set(
        primary_results
    )

    missing_canonical_ids = sorted(
        canonical_ids
        - engine_ids
    )

    extra_engine_ids = sorted(
        engine_ids
        - canonical_ids
    )

    extra_results = {
        transaction_id: (
            primary_results[
                transaction_id
            ]
        )
        for transaction_id
        in extra_engine_ids
    }

    extra_status_counts = Counter(
        normalize_status(
            result.get(
                "status"
            )
        )
        for result
        in extra_results.values()
    )

    extra_resolved_ids = sorted(
        transaction_id
        for (
            transaction_id,
            result,
        ) in extra_results.items()
        if normalize_status(
            result.get(
                "status"
            )
        )
        in RESOLVED_STATUSES
    )

    # ------------------------------------------------------------------
    # Canonical benchmark evaluation rows
    # ------------------------------------------------------------------

    rows: list[
        dict[str, Any]
    ] = []

    false_positive_ids: list[
        str
    ] = []

    false_negative_ids: list[
        str
    ] = []

    link_fields = (
        detect_ground_truth_link_fields(
            ground_truth
        )
    )

    linkage_evaluable = bool(
        link_fields
    )

    linkage_correct = 0
    linkage_wrong = 0
    linkage_missed = 0

    wrong_linkage_ids: list[
        str
    ] = []

    for record in ground_truth.to_dict(
        orient="records"
    ):
        transaction_id = (
            normalize_optional_id(
                record.get(
                    "transaction_id"
                )
            )
        )

        expected_status = (
            normalize_status(
                record.get(
                    "expected_status"
                )
            )
        )

        if transaction_id is None:
            continue

        result = primary_results.get(
            transaction_id
        )

        if result is None:
            actual_status = (
                "UNRESOLVED"
            )

            actual_method = (
                "NONE"
            )

            confidence = 0.0

        else:
            actual_status = (
                normalize_status(
                    result.get(
                        "status"
                    )
                )
            )

            actual_method = (
                normalize_status(
                    result.get(
                        "method",
                        "NONE",
                    )
                )
            )

            confidence = safe_float(
                result.get(
                    "confidence",
                    0.0,
                )
            )

        outcome = (
            classify_prediction(
                expected_status=(
                    expected_status
                ),
                actual_status=(
                    actual_status
                ),
            )
        )

        if (
            outcome
            == "FALSE_POSITIVE"
        ):
            false_positive_ids.append(
                transaction_id
            )

        elif (
            outcome
            == "FALSE_NEGATIVE"
        ):
            false_negative_ids.append(
                transaction_id
            )

        expected_resolvable = (
            expected_status
            in RESOLVABLE_GROUND_TRUTH
        )

        actual_resolved = (
            actual_status
            in RESOLVED_STATUSES
        )

        linkage_status = (
            "NOT_EVALUATED"
        )

        if (
            linkage_evaluable
            and expected_resolvable
        ):
            if not actual_resolved:
                linkage_missed += 1

                linkage_status = (
                    "MISSED"
                )

            elif result is not None:
                correct_link = (
                    compare_linkage(
                        expected_record=record,
                        actual_record=result,
                        link_fields=link_fields,
                    )
                )

                if correct_link:
                    linkage_correct += 1

                    linkage_status = (
                        "CORRECT"
                    )

                else:
                    linkage_wrong += 1

                    wrong_linkage_ids.append(
                        transaction_id
                    )

                    linkage_status = (
                        "WRONG"
                    )

        rows.append(
            {
                "transaction_id": (
                    transaction_id
                ),
                "expected_status": (
                    expected_status
                ),
                "actual_status": (
                    actual_status
                ),
                "actual_method": (
                    actual_method
                ),
                "confidence": (
                    confidence
                ),
                "outcome": (
                    outcome
                ),
                "linkage_status": (
                    linkage_status
                ),
            }
        )

    evaluation = pd.DataFrame(
        rows
    )

    # ------------------------------------------------------------------
    # Classification metrics
    # ------------------------------------------------------------------

    counts = Counter(
        evaluation[
            "outcome"
        ]
    )

    true_positive = int(
        counts[
            "TRUE_POSITIVE"
        ]
    )

    true_negative = int(
        counts[
            "TRUE_NEGATIVE"
        ]
    )

    false_positive = int(
        counts[
            "FALSE_POSITIVE"
        ]
    )

    false_negative = int(
        counts[
            "FALSE_NEGATIVE"
        ]
    )

    total = len(
        evaluation
    )

    precision = (
        safe_divide(
            true_positive,
            (
                true_positive
                + false_positive
            ),
        )
    )

    recall = (
        safe_divide(
            true_positive,
            (
                true_positive
                + false_negative
            ),
        )
    )

    f1 = (
        calculate_f1(
            precision,
            recall,
        )
    )

    correctly_classified = (
        true_positive
        + true_negative
    )

    classification_accuracy = (
        safe_divide(
            correctly_classified,
            total,
        )
    )

    # ------------------------------------------------------------------
    # Automation metrics
    # ------------------------------------------------------------------

    resolved_count = int(
        sum(
            normalize_status(
                actual_status
            )
            in RESOLVED_STATUSES
            for actual_status
            in evaluation[
                "actual_status"
            ]
        )
    )

    exception_count = (
        total
        - resolved_count
    )

    automatic_match_rate = (
        safe_divide(
            resolved_count,
            total,
        )
    )

    exception_rate = (
        safe_divide(
            exception_count,
            total,
        )
    )

    # ------------------------------------------------------------------
    # Scenario metrics
    # ------------------------------------------------------------------

    scenario_metrics: dict[
        str,
        dict[str, Any],
    ] = {}

    for scenario in sorted(
        evaluation[
            "expected_status"
        ].unique()
    ):
        subset = evaluation[
            evaluation[
                "expected_status"
            ]
            == scenario
        ]

        correct = int(
            subset[
                "outcome"
            ]
            .isin(
                [
                    "TRUE_POSITIVE",
                    "TRUE_NEGATIVE",
                ]
            )
            .sum()
        )

        scenario_metrics[
            str(
                scenario
            )
        ] = {
            "total": int(
                len(
                    subset
                )
            ),
            "correct": (
                correct
            ),
            "accuracy": (
                float(
                    correct
                    / len(
                        subset
                    )
                )
                if len(
                    subset
                )
                else 0.0
            ),
        }

    # ------------------------------------------------------------------
    # Linkage metrics
    # ------------------------------------------------------------------

    linkage_precision = 0.0
    linkage_recall = 0.0
    linkage_f1 = 0.0

    if linkage_evaluable:
        linkage_precision = (
            safe_divide(
                linkage_correct,
                (
                    linkage_correct
                    + linkage_wrong
                ),
            )
        )

        linkage_recall = (
            safe_divide(
                linkage_correct,
                (
                    linkage_correct
                    + linkage_wrong
                    + linkage_missed
                ),
            )
        )

        linkage_f1 = (
            calculate_f1(
                linkage_precision,
                linkage_recall,
            )
        )

    # ------------------------------------------------------------------
    # Duplicate source consumption
    # ------------------------------------------------------------------

    duplicate_payment_consumption = (
        detect_duplicate_source_consumption(
            primary_results,
            "payment_id",
        )
    )

    duplicate_ledger_consumption = (
        detect_duplicate_source_consumption(
            primary_results,
            "ledger_id",
        )
    )

    duplicate_settlement_usage = (
        detect_duplicate_source_consumption(
            primary_results,
            "settlement_id",
        )
    )

    # ------------------------------------------------------------------
    # Exception manifest integrity
    # ------------------------------------------------------------------

    exception_manifest = (
        evaluate_exception_manifest(
            primary_results,
            supplemental_results,
        )
    )

    # ------------------------------------------------------------------
    # Supplemental result statistics
    # ------------------------------------------------------------------

    supplemental_status_counts = Counter(
        normalize_status(
            result.get(
                "status"
            )
        )
        for result
        in supplemental_results
    )

    supplemental_resolved_count = sum(
        1
        for result
        in supplemental_results
        if normalize_status(
            result.get(
                "status"
            )
        )
        in RESOLVED_STATUSES
    )

    supplemental_exception_count = sum(
        1
        for result
        in supplemental_results
        if normalize_status(
            result.get(
                "status"
            )
        )
        in EXCEPTION_STATUSES
    )

    # ------------------------------------------------------------------
    # Integrity gate
    # ------------------------------------------------------------------

    integrity_failures: list[
        str
    ] = []

    if (
        ground_truth_integrity[
            "malformed_rows"
        ]
        > 0
    ):
        integrity_failures.append(
            "Malformed ground-truth rows detected."
        )

    if (
        ground_truth_integrity[
            "duplicate_transaction_ids"
        ]
    ):
        integrity_failures.append(
            "Duplicate transaction IDs detected "
            "in ground truth."
        )

    if (
        result_index[
            "malformed_rows"
        ]
        > 0
    ):
        integrity_failures.append(
            "Malformed reconciliation result rows detected."
        )

    if (
        result_index[
            "unsafe_duplicate_decisions"
        ]
    ):
        integrity_failures.append(
            "Multiple resolved decisions detected "
            "for the same transaction."
        )

    if (
        result_index[
            "unknown_statuses"
        ]
    ):
        integrity_failures.append(
            "Unknown reconciliation statuses detected."
        )

    if missing_canonical_ids:
        integrity_failures.append(
            "Canonical transactions are missing "
            "reconciliation decisions."
        )

    if extra_resolved_ids:
        integrity_failures.append(
            "Extra non-canonical engine records "
            "were automatically resolved."
        )

    if duplicate_payment_consumption:
        integrity_failures.append(
            "Payment IDs were consumed by multiple "
            "resolved transactions."
        )

    if duplicate_ledger_consumption:
        integrity_failures.append(
            "Ledger IDs were consumed by multiple "
            "resolved transactions."
        )

    if not exception_manifest[
        "file_exists"
    ]:
        integrity_failures.append(
            "Exception manifest does not exist."
        )

    if (
        exception_manifest[
            "malformed_rows"
        ]
        > 0
    ):
        integrity_failures.append(
            "Malformed exception-manifest rows detected."
        )

    if (
        exception_manifest[
            "missing_transaction_ids"
        ]
    ):
        integrity_failures.append(
            "Current exceptions are missing "
            "from the exception manifest."
        )

    if (
        exception_manifest[
            "orphan_transaction_ids"
        ]
    ):
        integrity_failures.append(
            "Exception manifest contains unexplained "
            "current exceptions."
        )

    integrity_passed = (
        len(
            integrity_failures
        )
        == 0
    )

    # ------------------------------------------------------------------
    # Final evaluation result
    # ------------------------------------------------------------------

    return {
        # --------------------------------------------------------------
        # Dataset
        # --------------------------------------------------------------
        "canonical_transactions": (
            total
        ),
        "engine_decisions_raw": (
            len(
                results
            )
        ),
        "engine_decisions_unique": (
            len(
                primary_results
            )
        ),
        "missing_canonical_count": (
            len(
                missing_canonical_ids
            )
        ),
        "missing_canonical_ids": (
            missing_canonical_ids
        ),
        "extra_engine_count": (
            len(
                extra_engine_ids
            )
        ),
        "extra_engine_ids": (
            extra_engine_ids
        ),
        "extra_engine_status_counts": dict(
            sorted(
                extra_status_counts.items()
            )
        ),
        "extra_resolved_ids": (
            extra_resolved_ids
        ),

        # --------------------------------------------------------------
        # Supplemental results
        # --------------------------------------------------------------
        "repeated_transaction_ids": list(
            result_index[
                "repeated_transaction_ids"
            ]
        ),
        "repeated_transaction_count": len(
            result_index[
                "repeated_transaction_ids"
            ]
        ),
        "supplemental_result_count": len(
            supplemental_results
        ),
        "supplemental_status_counts": dict(
            sorted(
                supplemental_status_counts.items()
            )
        ),
        "supplemental_resolved_count": int(
            supplemental_resolved_count
        ),
        "supplemental_exception_count": int(
            supplemental_exception_count
        ),
        "unsafe_duplicate_decisions": list(
            result_index[
                "unsafe_duplicate_decisions"
            ]
        ),

        # --------------------------------------------------------------
        # Ground-truth integrity
        # --------------------------------------------------------------
        "ground_truth_malformed_rows": (
            ground_truth_integrity[
                "malformed_rows"
            ]
        ),
        "ground_truth_duplicate_transaction_ids": (
            ground_truth_integrity[
                "duplicate_transaction_ids"
            ]
        ),

        # --------------------------------------------------------------
        # Engine result integrity
        # --------------------------------------------------------------
        "result_malformed_rows": (
            result_index[
                "malformed_rows"
            ]
        ),
        "unknown_engine_statuses": list(
            result_index[
                "unknown_statuses"
            ]
        ),

        # --------------------------------------------------------------
        # Classification
        # --------------------------------------------------------------
        "true_positive": (
            true_positive
        ),
        "true_negative": (
            true_negative
        ),
        "false_positive": (
            false_positive
        ),
        "false_negative": (
            false_negative
        ),
        "false_positive_ids": sorted(
            false_positive_ids
        ),
        "false_negative_ids": sorted(
            false_negative_ids
        ),
        "classification_accuracy": (
            classification_accuracy
        ),
        "precision": (
            precision
        ),
        "recall": (
            recall
        ),
        "f1": (
            f1
        ),

        # --------------------------------------------------------------
        # Automation
        # --------------------------------------------------------------
        "resolved_count": (
            resolved_count
        ),
        "exception_count": (
            exception_count
        ),
        "automatic_match_rate": (
            automatic_match_rate
        ),
        "exception_rate": (
            exception_rate
        ),

        # --------------------------------------------------------------
        # Linkage
        # --------------------------------------------------------------
        "linkage_evaluable": (
            linkage_evaluable
        ),
        "linkage_fields": (
            link_fields
        ),
        "linkage_correct": (
            linkage_correct
        ),
        "linkage_wrong": (
            linkage_wrong
        ),
        "linkage_missed": (
            linkage_missed
        ),
        "linkage_precision": (
            linkage_precision
        ),
        "linkage_recall": (
            linkage_recall
        ),
        "linkage_f1": (
            linkage_f1
        ),
        "wrong_linkage_ids": sorted(
            wrong_linkage_ids
        ),

        # --------------------------------------------------------------
        # Duplicate source consumption
        # --------------------------------------------------------------
        "duplicate_payment_consumption": (
            duplicate_payment_consumption
        ),
        "duplicate_ledger_consumption": (
            duplicate_ledger_consumption
        ),
        "duplicate_settlement_usage": (
            duplicate_settlement_usage
        ),

        # --------------------------------------------------------------
        # Exception manifest
        # --------------------------------------------------------------
        "exception_manifest": (
            exception_manifest
        ),

        # --------------------------------------------------------------
        # Scenario metrics
        # --------------------------------------------------------------
        "scenario_metrics": (
            scenario_metrics
        ),

        # --------------------------------------------------------------
        # Integrity result
        # --------------------------------------------------------------
        "integrity_passed": (
            integrity_passed
        ),
        "integrity_failures": (
            integrity_failures
        ),

        # Not included in JSON output.
        "evaluation_rows": (
            evaluation
        ),
    }


# ======================================================================
# REPORTING
# ======================================================================


def print_report(
    evaluation: dict[str, Any],
    elapsed: float,
) -> None:
    """
    Print human-readable reconciliation benchmark report.
    """

    print()
    print("=" * 72)
    print(
        "ReconAI GROUND-TRUTH RECONCILIATION EVALUATION"
    )
    print("=" * 72)

    # ------------------------------------------------------------------
    # Dataset
    # ------------------------------------------------------------------

    print()
    print("DATASET")
    print("-" * 72)

    print(
        f"Canonical transactions  : "
        f"{evaluation['canonical_transactions']}"
    )

    print(
        f"Raw engine decisions    : "
        f"{evaluation['engine_decisions_raw']}"
    )

    print(
        f"Unique transactions     : "
        f"{evaluation['engine_decisions_unique']}"
    )

    print(
        f"Missing canonical rows  : "
        f"{evaluation['missing_canonical_count']}"
    )

    print(
        f"Extra transaction IDs   : "
        f"{evaluation['extra_engine_count']}"
    )

    # ------------------------------------------------------------------
    # Supplemental events
    # ------------------------------------------------------------------

    print()
    print("SUPPLEMENTAL SOURCE EVENTS")
    print("-" * 72)

    print(
        f"Repeated transaction IDs: "
        f"{evaluation['repeated_transaction_count']}"
    )

    print(
        f"Supplemental rows       : "
        f"{evaluation['supplemental_result_count']}"
    )

    print(
        f"Supplemental exceptions : "
        f"{evaluation['supplemental_exception_count']}"
    )

    print(
        f"Supplemental resolved   : "
        f"{evaluation['supplemental_resolved_count']}"
    )

    print(
        f"Unsafe duplicate matches: "
        f"{len(evaluation['unsafe_duplicate_decisions'])}"
    )

    if evaluation[
        "supplemental_status_counts"
    ]:
        print()

        for (
            status,
            count,
        ) in evaluation[
            "supplemental_status_counts"
        ].items():
            print(
                f"{status:<28}: "
                f"{count}"
            )

    # ------------------------------------------------------------------
    # Automation
    # ------------------------------------------------------------------

    print()
    print("AUTOMATION")
    print("-" * 72)

    print(
        f"Automatically resolved  : "
        f"{evaluation['resolved_count']}"
    )

    print(
        f"Canonical exceptions    : "
        f"{evaluation['exception_count']}"
    )

    print(
        f"Automatic match rate    : "
        f"{evaluation['automatic_match_rate']:.2%}"
    )

    print(
        f"Exception rate          : "
        f"{evaluation['exception_rate']:.2%}"
    )

    # ------------------------------------------------------------------
    # Ground-truth quality
    # ------------------------------------------------------------------

    print()
    print("GROUND-TRUTH QUALITY")
    print("-" * 72)

    print(
        f"Classification accuracy : "
        f"{evaluation['classification_accuracy']:.2%}"
    )

    print(
        f"Precision               : "
        f"{evaluation['precision']:.2%}"
    )

    print(
        f"Recall                  : "
        f"{evaluation['recall']:.2%}"
    )

    print(
        f"F1 score                : "
        f"{evaluation['f1']:.2%}"
    )

    print(
        f"True positives          : "
        f"{evaluation['true_positive']}"
    )

    print(
        f"True negatives          : "
        f"{evaluation['true_negative']}"
    )

    print(
        f"False positives         : "
        f"{evaluation['false_positive']}"
    )

    print(
        f"False negatives         : "
        f"{evaluation['false_negative']}"
    )

    # ------------------------------------------------------------------
    # Linkage
    # ------------------------------------------------------------------

    print()
    print("LINKAGE CORRECTNESS")
    print("-" * 72)

    if evaluation[
        "linkage_evaluable"
    ]:
        print(
            f"Fields evaluated        : "
            f"{', '.join(evaluation['linkage_fields'].keys())}"
        )

        print(
            f"Correct linkages        : "
            f"{evaluation['linkage_correct']}"
        )

        print(
            f"Wrong linkages          : "
            f"{evaluation['linkage_wrong']}"
        )

        print(
            f"Missed linkages         : "
            f"{evaluation['linkage_missed']}"
        )

        print(
            f"Link precision          : "
            f"{evaluation['linkage_precision']:.2%}"
        )

        print(
            f"Link recall             : "
            f"{evaluation['linkage_recall']:.2%}"
        )

        print(
            f"Link F1                 : "
            f"{evaluation['linkage_f1']:.2%}"
        )

    else:
        print(
            "Ground truth contains no source-link "
            "columns. Linkage scoring skipped."
        )

    # ------------------------------------------------------------------
    # Duplicate/integrity
    # ------------------------------------------------------------------

    print()
    print("DUPLICATE / SAFETY CHECKS")
    print("-" * 72)

    print(
        f"Malformed GT rows       : "
        f"{evaluation['ground_truth_malformed_rows']}"
    )

    print(
        f"Malformed result rows   : "
        f"{evaluation['result_malformed_rows']}"
    )

    print(
        f"Repeated transaction IDs: "
        f"{evaluation['repeated_transaction_count']}"
    )

    print(
        f"Unsafe duplicate matches: "
        f"{len(evaluation['unsafe_duplicate_decisions'])}"
    )

    print(
        f"Duplicate payment use   : "
        f"{len(evaluation['duplicate_payment_consumption'])}"
    )

    print(
        f"Duplicate ledger use    : "
        f"{len(evaluation['duplicate_ledger_consumption'])}"
    )

    print(
        f"Settlement reuse        : "
        f"{len(evaluation['duplicate_settlement_usage'])}"
    )

    print(
        f"Unknown statuses        : "
        f"{len(evaluation['unknown_engine_statuses'])}"
    )

    # ------------------------------------------------------------------
    # Exception manifest
    # ------------------------------------------------------------------

    print()
    print("EXCEPTION MANIFEST")
    print("-" * 72)

    manifest = (
        evaluation[
            "exception_manifest"
        ]
    )

    print(
        f"Manifest exists         : "
        f"{manifest['file_exists']}"
    )

    print(
        f"Manifest events         : "
        f"{manifest['total_events']}"
    )

    print(
        f"Primary exception IDs   : "
        f"{manifest['primary_exception_count']}"
    )

    print(
        f"Supplemental exception IDs: "
        f"{manifest['supplemental_exception_count']}"
    )

    print(
        f"Expected current IDs    : "
        f"{manifest['expected_current_exceptions']}"
    )

    print(
        f"Manifest current IDs    : "
        f"{manifest['manifest_current_exceptions']}"
    )

    print(
        f"Manifest coverage       : "
        f"{manifest['coverage_rate']:.2%}"
    )

    print(
        f"Missing manifest IDs    : "
        f"{len(manifest['missing_transaction_ids'])}"
    )

    print(
        f"Orphan manifest IDs     : "
        f"{len(manifest['orphan_transaction_ids'])}"
    )

    # ------------------------------------------------------------------
    # Per-scenario metrics
    # ------------------------------------------------------------------

    print()
    print("PER-SCENARIO PERFORMANCE")
    print("-" * 72)

    for (
        scenario,
        metrics,
    ) in evaluation[
        "scenario_metrics"
    ].items():
        print(
            f"{scenario:<28}"
            f"{metrics['correct']:>5}/"
            f"{metrics['total']:<5}"
            f" "
            f"{metrics['accuracy']:.2%}"
        )

    # ------------------------------------------------------------------
    # Evaluator performance
    # ------------------------------------------------------------------

    print()
    print("EVALUATOR PERFORMANCE")
    print("-" * 72)

    throughput = (
        evaluation[
            "canonical_transactions"
        ]
        / elapsed
        if elapsed > 0.0
        else 0.0
    )

    print(
        f"Evaluation time         : "
        f"{elapsed:.6f} sec"
    )

    print(
        f"Evaluation throughput   : "
        f"{throughput:,.2f} records/sec"
    )

    print(
        "NOTE                     : "
        "Evaluator throughput is not "
        "reconciliation-engine throughput."
    )

    # ------------------------------------------------------------------
    # Final integrity result
    # ------------------------------------------------------------------

    print()
    print("INTEGRITY")
    print("-" * 72)

    print(
        f"Integrity passed        : "
        f"{evaluation['integrity_passed']}"
    )

    if evaluation[
        "integrity_failures"
    ]:
        for failure in evaluation[
            "integrity_failures"
        ]:
            print(
                f"FAIL                     : "
                f"{failure}"
            )

    print()
    print("=" * 72)

    if evaluation[
        "integrity_passed"
    ]:
        print(
            "RECONCILIATION BENCHMARK INTEGRITY: PASS"
        )
    else:
        print(
            "RECONCILIATION BENCHMARK INTEGRITY: FAIL"
        )

    print("=" * 72)


# ======================================================================
# JSON ARTIFACT
# ======================================================================


def write_evaluation_artifact(
    evaluation: dict[str, Any],
    elapsed: float,
) -> None:
    """
    Write machine-readable benchmark output.

    The pandas evaluation DataFrame is intentionally excluded.
    """

    payload = {
        key: value
        for (
            key,
            value,
        ) in evaluation.items()
        if key
        != "evaluation_rows"
    }

    throughput = (
        evaluation[
            "canonical_transactions"
        ]
        / elapsed
        if elapsed > 0.0
        else 0.0
    )

    payload[
        "evaluation_elapsed_seconds"
    ] = elapsed

    payload[
        "evaluation_throughput_records_per_second"
    ] = throughput

    EVALUATION_OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with EVALUATION_OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            indent=2,
            sort_keys=True,
        )

        file.write(
            "\n"
        )


# ======================================================================
# ENTRYPOINT
# ======================================================================


def main() -> None:
    """
    Run complete ReconAI benchmark evaluation.
    """

    start = (
        time.perf_counter()
    )

    ground_truth = (
        load_ground_truth()
    )

    results = (
        load_results()
    )

    evaluation = (
        evaluate(
            ground_truth=ground_truth,
            results=results,
        )
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    print_report(
        evaluation,
        elapsed,
    )

    write_evaluation_artifact(
        evaluation,
        elapsed,
    )

    print()

    print(
        f"Evaluation artifact     : "
        f"{EVALUATION_OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()