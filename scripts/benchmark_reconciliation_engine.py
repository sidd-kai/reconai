from __future__ import annotations

import json
import statistics
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.reconciliation.engine import (
    ReconciliationEngine,
)
from backend.app.reconciliation.loader import (
    DataLoader,
)
from backend.app.reconciliation.models import (
    MatchResult,
    MatchStatus,
)


# ======================================================================
# PATHS
# ======================================================================

ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = (
    ROOT
    / "data"
    / "raw"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "results"
    / "reconciliation_engine_benchmark.json"
)


# ======================================================================
# BENCHMARK CONFIGURATION
# ======================================================================

WARMUP_RUNS = 1

TIMED_RUNS = 5


RESOLVED_STATUSES = {
    MatchStatus.MATCHED,
    MatchStatus.FUZZY_MATCHED,
}


# ======================================================================
# MODELS
# ======================================================================


@dataclass(frozen=True)
class RunMetrics:
    run_number: int
    elapsed_seconds: float
    canonical_transactions: int
    raw_decisions: int
    canonical_records_per_second: float
    raw_decisions_per_second: float


# ======================================================================
# RESULT SEMANTICS
# ======================================================================


def partition_results(
    results: list[MatchResult],
) -> tuple[
    dict[str, MatchResult],
    list[MatchResult],
]:
    """
    Split engine results into:

        canonical transaction decisions
        supplemental source-level events

    Current engine contract:
        the first emitted result for a transaction is canonical.

    Later rows for the same transaction remain visible as
    supplemental evidence.
    """

    primary: dict[
        str,
        MatchResult,
    ] = {}

    supplemental: list[
        MatchResult
    ] = []

    for result in results:
        transaction_id = (
            result.transaction_id
        )

        if transaction_id not in primary:
            primary[
                transaction_id
            ] = result
        else:
            supplemental.append(
                result
            )

    return (
        primary,
        supplemental,
    )


def detect_unsafe_duplicate_resolutions(
    results: list[MatchResult],
) -> dict[str, int]:
    """
    Detect transactions receiving more than one automatically
    resolved decision.

    ReconAI must never silently resolve one transaction twice.
    """

    resolved_counts: dict[
        str,
        int,
    ] = {}

    for result in results:
        if (
            result.status
            not in RESOLVED_STATUSES
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

    return {
        transaction_id: count
        for (
            transaction_id,
            count,
        ) in resolved_counts.items()
        if count > 1
    }


def build_result_signature(
    results: list[MatchResult],
) -> tuple[
    tuple[Any, ...],
    ...,
]:
    """
    Build a deterministic signature of reconciliation decisions.

    All benchmark runs must produce exactly the same financial
    decisions.

    Performance testing must never hide nondeterminism.
    """

    return tuple(
        (
            result.transaction_id,
            result.payment_id,
            result.ledger_id,
            result.settlement_id,
            result.status.value,
            result.method.value,
            round(
                result.confidence,
                12,
            ),
            round(
                result.amount_difference,
                12,
            ),
            result.candidate_count,
            result.reason,
        )
        for result in results
    )


# ======================================================================
# SINGLE ENGINE EXECUTION
# ======================================================================


def execute_engine(
    *,
    payments: list[Any],
    ledger: list[Any],
    settlements: list[Any],
    audit_path: Path,
    exception_path: Path,
) -> tuple[
    list[MatchResult],
    float,
]:
    """
    Execute and time the real ReconciliationEngine.

    Timing includes:
        matching
        validation
        result construction
        immutable audit logging
        exception-manifest logging

    Timing excludes:
        raw dataset loading
        benchmark reporting
        benchmark JSON serialization
    """

    engine = ReconciliationEngine(
        audit_path=audit_path,
        exception_path=exception_path,
    )

    start = (
        time.perf_counter()
    )

    results = engine.reconcile(
        payments=payments,
        ledger=ledger,
        settlements=settlements,
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    return (
        results,
        elapsed,
    )


# ======================================================================
# BENCHMARK
# ======================================================================


def benchmark() -> dict[str, Any]:
    """
    Run warmup + repeated timed reconciliation runs.
    """

    # ------------------------------------------------------------------
    # Load source records OUTSIDE timed section.
    # ------------------------------------------------------------------

    loader = DataLoader(
        RAW_DIR
    )

    payments = (
        loader.load_payments()
    )

    ledger = (
        loader.load_ledger()
    )

    settlements = (
        loader.load_settlements()
    )

    print()
    print(
        "SOURCE DATA"
    )
    print(
        "-" * 72
    )

    print(
        f"Payment rows            : "
        f"{len(payments)}"
    )

    print(
        f"Ledger rows             : "
        f"{len(ledger)}"
    )

    print(
        f"Settlement rows         : "
        f"{len(settlements)}"
    )

    run_metrics: list[
        RunMetrics
    ] = []

    reference_signature: tuple[
        tuple[Any, ...],
        ...,
    ] | None = None

    reference_results: list[
        MatchResult
    ] | None = None

    # ------------------------------------------------------------------
    # Use temporary output paths.
    #
    # Benchmarking must never pollute:
    #
    # data/results/audit.jsonl
    # data/results/exceptions.jsonl
    # ------------------------------------------------------------------

    with tempfile.TemporaryDirectory(
        prefix="reconai_engine_benchmark_"
    ) as temp_dir:

        temp_root = Path(
            temp_dir
        )

        # --------------------------------------------------------------
        # Warmup
        # --------------------------------------------------------------

        print()
        print(
            "WARMUP"
        )
        print(
            "-" * 72
        )

        for warmup_index in range(
            1,
            WARMUP_RUNS + 1,
        ):
            warmup_audit = (
                temp_root
                / f"warmup_{warmup_index}_audit.jsonl"
            )

            warmup_exceptions = (
                temp_root
                / f"warmup_{warmup_index}_exceptions.jsonl"
            )

            (
                warmup_results,
                warmup_elapsed,
            ) = execute_engine(
                payments=payments,
                ledger=ledger,
                settlements=settlements,
                audit_path=warmup_audit,
                exception_path=(
                    warmup_exceptions
                ),
            )

            print(
                f"Warmup {warmup_index:<2} "
                f": "
                f"{warmup_elapsed:.6f} sec "
                f"| "
                f"{len(warmup_results)} decisions"
            )

        # --------------------------------------------------------------
        # Timed runs
        # --------------------------------------------------------------

        print()
        print(
            "TIMED RUNS"
        )
        print(
            "-" * 72
        )

        for run_number in range(
            1,
            TIMED_RUNS + 1,
        ):
            audit_path = (
                temp_root
                / f"run_{run_number}_audit.jsonl"
            )

            exception_path = (
                temp_root
                / f"run_{run_number}_exceptions.jsonl"
            )

            (
                results,
                elapsed,
            ) = execute_engine(
                payments=payments,
                ledger=ledger,
                settlements=settlements,
                audit_path=audit_path,
                exception_path=(
                    exception_path
                ),
            )

            (
                primary,
                _,
            ) = partition_results(
                results
            )

            canonical_count = len(
                primary
            )

            raw_decision_count = len(
                results
            )

            canonical_throughput = (
                canonical_count
                / elapsed
                if elapsed > 0
                else 0.0
            )

            raw_decision_throughput = (
                raw_decision_count
                / elapsed
                if elapsed > 0
                else 0.0
            )

            signature = (
                build_result_signature(
                    results
                )
            )

            if reference_signature is None:
                reference_signature = (
                    signature
                )

                reference_results = (
                    results
                )

            elif signature != reference_signature:
                raise AssertionError(
                    "Reconciliation decisions changed "
                    "between benchmark runs. "
                    "Engine output is not deterministic."
                )

            metrics = RunMetrics(
                run_number=run_number,
                elapsed_seconds=elapsed,
                canonical_transactions=(
                    canonical_count
                ),
                raw_decisions=(
                    raw_decision_count
                ),
                canonical_records_per_second=(
                    canonical_throughput
                ),
                raw_decisions_per_second=(
                    raw_decision_throughput
                ),
            )

            run_metrics.append(
                metrics
            )

            print(
                f"Run {run_number:<2} "
                f": "
                f"{elapsed:.6f} sec "
                f"| "
                f"{canonical_throughput:,.2f} canonical/sec "
                f"| "
                f"{raw_decision_throughput:,.2f} decisions/sec"
            )

    if reference_results is None:
        raise RuntimeError(
            "Benchmark produced no reconciliation results."
        )

    # ------------------------------------------------------------------
    # Canonical result analysis
    # ------------------------------------------------------------------

    (
        primary_results,
        supplemental_results,
    ) = partition_results(
        reference_results
    )

    canonical_count = len(
        primary_results
    )

    raw_decision_count = len(
        reference_results
    )

    supplemental_count = len(
        supplemental_results
    )

    resolved_count = sum(
        1
        for result
        in primary_results.values()
        if result.status
        in RESOLVED_STATUSES
    )

    exception_count = (
        canonical_count
        - resolved_count
    )

    match_rate = (
        resolved_count
        / canonical_count
        if canonical_count
        else 0.0
    )

    exception_rate = (
        exception_count
        / canonical_count
        if canonical_count
        else 0.0
    )

    unsafe_duplicate_resolutions = (
        detect_unsafe_duplicate_resolutions(
            reference_results
        )
    )

    canonical_status_counts = Counter(
        result.status.value
        for result
        in primary_results.values()
    )

    supplemental_status_counts = Counter(
        result.status.value
        for result
        in supplemental_results
    )

    # ------------------------------------------------------------------
    # Timing statistics
    # ------------------------------------------------------------------

    elapsed_values = [
        metrics.elapsed_seconds
        for metrics
        in run_metrics
    ]

    canonical_throughputs = [
        metrics.canonical_records_per_second
        for metrics
        in run_metrics
    ]

    raw_throughputs = [
        metrics.raw_decisions_per_second
        for metrics
        in run_metrics
    ]

    mean_elapsed = (
        statistics.mean(
            elapsed_values
        )
    )

    median_elapsed = (
        statistics.median(
            elapsed_values
        )
    )

    min_elapsed = min(
        elapsed_values
    )

    max_elapsed = max(
        elapsed_values
    )

    mean_canonical_throughput = (
        statistics.mean(
            canonical_throughputs
        )
    )

    median_canonical_throughput = (
        statistics.median(
            canonical_throughputs
        )
    )

    mean_raw_throughput = (
        statistics.mean(
            raw_throughputs
        )
    )

    median_raw_throughput = (
        statistics.median(
            raw_throughputs
        )
    )

    # ------------------------------------------------------------------
    # Integrity gates
    # ------------------------------------------------------------------

    integrity_failures: list[
        str
    ] = []

    if canonical_count != 1000:
        integrity_failures.append(
            "Expected 1,000 canonical benchmark transactions, "
            f"got {canonical_count}."
        )

    if raw_decision_count < canonical_count:
        integrity_failures.append(
            "Raw decision count is lower than canonical count."
        )

    if unsafe_duplicate_resolutions:
        integrity_failures.append(
            "Unsafe duplicate automatic resolutions detected."
        )

    if resolved_count + exception_count != canonical_count:
        integrity_failures.append(
            "Resolved + exception counts do not equal "
            "canonical transaction count."
        )

    if reference_signature is None:
        integrity_failures.append(
            "No deterministic result signature produced."
        )

    integrity_passed = (
        len(
            integrity_failures
        )
        == 0
    )

    # ------------------------------------------------------------------
    # Machine-readable output
    # ------------------------------------------------------------------

    return {
        "benchmark_type": (
            "reconciliation_engine"
        ),
        "timing_scope": (
            "ReconciliationEngine.reconcile only; "
            "includes audit and exception JSONL writes; "
            "excludes source loading and benchmark reporting"
        ),

        "configuration": {
            "warmup_runs": (
                WARMUP_RUNS
            ),
            "timed_runs": (
                TIMED_RUNS
            ),
        },

        "source_rows": {
            "payments": (
                len(payments)
            ),
            "ledger": (
                len(ledger)
            ),
            "settlements": (
                len(settlements)
            ),
        },

        "results": {
            "canonical_transactions": (
                canonical_count
            ),
            "raw_decisions": (
                raw_decision_count
            ),
            "supplemental_source_events": (
                supplemental_count
            ),
            "resolved": (
                resolved_count
            ),
            "exceptions": (
                exception_count
            ),
            "match_rate": (
                match_rate
            ),
            "exception_rate": (
                exception_rate
            ),
            "unsafe_duplicate_resolutions": (
                unsafe_duplicate_resolutions
            ),
            "canonical_status_counts": dict(
                sorted(
                    canonical_status_counts.items()
                )
            ),
            "supplemental_status_counts": dict(
                sorted(
                    supplemental_status_counts.items()
                )
            ),
        },

        "latency_seconds": {
            "mean": (
                mean_elapsed
            ),
            "median": (
                median_elapsed
            ),
            "min": (
                min_elapsed
            ),
            "max": (
                max_elapsed
            ),
        },

        "throughput": {
            "canonical_records_per_second_mean": (
                mean_canonical_throughput
            ),
            "canonical_records_per_second_median": (
                median_canonical_throughput
            ),
            "raw_decisions_per_second_mean": (
                mean_raw_throughput
            ),
            "raw_decisions_per_second_median": (
                median_raw_throughput
            ),
        },

        "runs": [
            {
                "run_number": (
                    metrics.run_number
                ),
                "elapsed_seconds": (
                    metrics.elapsed_seconds
                ),
                "canonical_transactions": (
                    metrics.canonical_transactions
                ),
                "raw_decisions": (
                    metrics.raw_decisions
                ),
                "canonical_records_per_second": (
                    metrics.canonical_records_per_second
                ),
                "raw_decisions_per_second": (
                    metrics.raw_decisions_per_second
                ),
            }
            for metrics
            in run_metrics
        ],

        "deterministic_across_runs": True,

        "integrity_passed": (
            integrity_passed
        ),

        "integrity_failures": (
            integrity_failures
        ),
    }


# ======================================================================
# REPORTING
# ======================================================================


def print_report(
    benchmark_result: dict[str, Any],
) -> None:
    results = (
        benchmark_result[
            "results"
        ]
    )

    latency = (
        benchmark_result[
            "latency_seconds"
        ]
    )

    throughput = (
        benchmark_result[
            "throughput"
        ]
    )

    print()
    print(
        "=" * 72
    )

    print(
        "RECONAI RECONCILIATION ENGINE BENCHMARK"
    )

    print(
        "=" * 72
    )

    print()
    print(
        "BENCHMARK SEMANTICS"
    )
    print(
        "-" * 72
    )

    print(
        "Timed operation          : "
        "ReconciliationEngine.reconcile()"
    )

    print(
        "Source loading timed     : False"
    )

    print(
        "Audit logging included   : True"
    )

    print(
        "Exception writes included: True"
    )

    print()
    print(
        "DATASET"
    )
    print(
        "-" * 72
    )

    print(
        f"Payment source rows      : "
        f"{benchmark_result['source_rows']['payments']}"
    )

    print(
        f"Ledger source rows       : "
        f"{benchmark_result['source_rows']['ledger']}"
    )

    print(
        f"Settlement source rows   : "
        f"{benchmark_result['source_rows']['settlements']}"
    )

    print(
        f"Canonical transactions   : "
        f"{results['canonical_transactions']}"
    )

    print(
        f"Raw engine decisions     : "
        f"{results['raw_decisions']}"
    )

    print(
        f"Supplemental events      : "
        f"{results['supplemental_source_events']}"
    )

    print()
    print(
        "FINANCE OUTCOMES"
    )
    print(
        "-" * 72
    )

    print(
        f"Automatically resolved   : "
        f"{results['resolved']}"
    )

    print(
        f"Canonical exceptions     : "
        f"{results['exceptions']}"
    )

    print(
        f"Automatic match rate     : "
        f"{results['match_rate']:.2%}"
    )

    print(
        f"Exception rate           : "
        f"{results['exception_rate']:.2%}"
    )

    print(
        f"Unsafe duplicate resolves: "
        f"{len(results['unsafe_duplicate_resolutions'])}"
    )

    print()
    print(
        "LATENCY"
    )
    print(
        "-" * 72
    )

    print(
        f"Mean                    : "
        f"{latency['mean']:.6f} sec"
    )

    print(
        f"Median                  : "
        f"{latency['median']:.6f} sec"
    )

    print(
        f"Fastest                 : "
        f"{latency['min']:.6f} sec"
    )

    print(
        f"Slowest                 : "
        f"{latency['max']:.6f} sec"
    )

    print()
    print(
        "ACTUAL ENGINE THROUGHPUT"
    )
    print(
        "-" * 72
    )

    print(
        f"Mean canonical throughput: "
        f"{throughput['canonical_records_per_second_mean']:,.2f} "
        f"records/sec"
    )

    print(
        f"Median canonical throughput: "
        f"{throughput['canonical_records_per_second_median']:,.2f} "
        f"records/sec"
    )

    print(
        f"Mean raw decision throughput: "
        f"{throughput['raw_decisions_per_second_mean']:,.2f} "
        f"decisions/sec"
    )

    print(
        f"Median raw decision throughput: "
        f"{throughput['raw_decisions_per_second_median']:,.2f} "
        f"decisions/sec"
    )

    print()
    print(
        "DETERMINISM / SAFETY"
    )
    print(
        "-" * 72
    )

    print(
        f"Deterministic across runs: "
        f"{benchmark_result['deterministic_across_runs']}"
    )

    print(
        f"Integrity passed         : "
        f"{benchmark_result['integrity_passed']}"
    )

    if benchmark_result[
        "integrity_failures"
    ]:
        for failure in benchmark_result[
            "integrity_failures"
        ]:
            print(
                f"FAIL                     : "
                f"{failure}"
            )

    print()
    print(
        "=" * 72
    )

    if benchmark_result[
        "integrity_passed"
    ]:
        print(
            "RECONCILIATION ENGINE BENCHMARK: PASS"
        )
    else:
        print(
            "RECONCILIATION ENGINE BENCHMARK: FAIL"
        )

    print(
        "=" * 72
    )


# ======================================================================
# ARTIFACT
# ======================================================================


def write_artifact(
    benchmark_result: dict[str, Any],
) -> None:
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            benchmark_result,
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
    result = (
        benchmark()
    )

    print_report(
        result
    )

    write_artifact(
        result
    )

    print()
    print(
        f"Benchmark artifact       : "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()