from __future__ import annotations

import statistics
from pathlib import Path

import pandas as pd

from backend.app.reconciliation.matcher import find_candidates
from backend.app.reconciliation.models import LedgerEntry, Payment


ROOT = Path(__file__).resolve().parents[1]

PAYMENTS_FILE = ROOT / "data/raw/payments.csv"
LEDGER_FILE = ROOT / "data/raw/merchant_ledger.csv"
GROUND_TRUTH_FILE = ROOT / "data/ground_truth/ground_truth.csv"


NON_RESOLVABLE_SCENARIOS = {
    "UNRESOLVED",
}


def load_payments() -> list[Payment]:
    df = pd.read_csv(PAYMENTS_FILE)

    payments: list[Payment] = []

    for row in df.to_dict(orient="records"):
        payments.append(
            Payment(
                transaction_id=str(row["transaction_id"]),
                payment_id=str(row["payment_id"]),
                order_id=str(row["order_id"]),
                amount=float(row["amount"]),
                currency=str(row["currency"]),
                status=str(row["status"]),
                created_at=pd.to_datetime(
                    row["created_at"]
                ).to_pydatetime(),
            )
        )

    return payments


def load_ledger() -> list[LedgerEntry]:
    df = pd.read_csv(LEDGER_FILE)

    ledger: list[LedgerEntry] = []

    for row in df.to_dict(orient="records"):
        ledger.append(
            LedgerEntry(
                transaction_id=str(row["transaction_id"]),
                ledger_id=str(row["ledger_id"]),
                order_ref=str(row["order_ref"]),
                amount=float(row["amount"]),
                currency=str(row["currency"]),
                status=str(row["status"]),
                recorded_at=pd.to_datetime(
                    row["recorded_at"]
                ).to_pydatetime(),
            )
        )

    return ledger


def percentile(
    values: list[int],
    percentile_value: float,
) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)

    position = (len(ordered) - 1) * percentile_value

    lower = int(position)
    upper = min(
        lower + 1,
        len(ordered) - 1,
    )

    fraction = position - lower

    return (
        ordered[lower]
        + (
            ordered[upper]
            - ordered[lower]
        )
        * fraction
    )


def main() -> None:
    payments = load_payments()
    ledger = load_ledger()

    ground_truth = pd.read_csv(
        GROUND_TRUTH_FILE
    )

    ground_truth_by_transaction = {
        str(row["transaction_id"]): row
        for row in ground_truth.to_dict(
            orient="records"
        )
    }

    candidate_counts: list[int] = []

    evaluated_transactions = 0
    candidate_recall_hits = 0

    unresolved_transactions = 0

    candidate_misses: list[str] = []

    for payment in payments:
        candidates = find_candidates(
            payment,
            ledger,
        )

        candidate_counts.append(
            len(candidates)
        )

        ground_truth_row = (
            ground_truth_by_transaction.get(
                payment.transaction_id
            )
        )

        if ground_truth_row is None:
            continue

        expected_status = str(
            ground_truth_row["expected_status"]
        )

        expected_ledger_id = (
            ground_truth_row["ledger_id"]
        )

        if expected_status in NON_RESOLVABLE_SCENARIOS:
            unresolved_transactions += 1
            continue

        if pd.isna(expected_ledger_id):
            continue

        evaluated_transactions += 1

        candidate_ids = {
            candidate.ledger.ledger_id
            for candidate in candidates
        }

        if str(expected_ledger_id) in candidate_ids:
            candidate_recall_hits += 1
        else:
            candidate_misses.append(
                payment.transaction_id
            )

    average = (
        statistics.mean(candidate_counts)
        if candidate_counts
        else 0.0
    )

    median = (
        statistics.median(candidate_counts)
        if candidate_counts
        else 0.0
    )

    p95 = percentile(
        candidate_counts,
        0.95,
    )

    maximum = (
        max(candidate_counts)
        if candidate_counts
        else 0
    )

    candidate_recall = (
        candidate_recall_hits
        / evaluated_transactions
        if evaluated_transactions
        else 0.0
    )

    print()
    print("=" * 72)
    print("ReconAI CANDIDATE QUALITY BENCHMARK")
    print("=" * 72)

    print()
    print("DATASET")
    print("-" * 72)

    print(
        f"Payments                  : "
        f"{len(payments)}"
    )

    print(
        f"Ledger records             : "
        f"{len(ledger)}"
    )

    print(
        f"Resolvable transactions    : "
        f"{evaluated_transactions}"
    )

    print(
        f"UNRESOLVED transactions    : "
        f"{unresolved_transactions}"
    )

    print()
    print("CANDIDATE SET SIZE")
    print("-" * 72)

    print(
        f"Average candidates         : "
        f"{average:.2f}"
    )

    print(
        f"Median candidates          : "
        f"{median:.2f}"
    )

    print(
        f"P95 candidates             : "
        f"{p95:.2f}"
    )

    print(
        f"Maximum candidates         : "
        f"{maximum}"
    )

    print()
    print("CANDIDATE RECALL")
    print("-" * 72)

    print(
        f"Recall                     : "
        f"{candidate_recall:.2%}"
    )

    print(
        f"Correctly retained         : "
        f"{candidate_recall_hits}/"
        f"{evaluated_transactions}"
    )

    if candidate_misses:
        print()
        print("CANDIDATE MISSES")
        print("-" * 72)

        for transaction_id in candidate_misses:
            print(transaction_id)

    print()
    print("UNRESOLVED POLICY")
    print("-" * 72)

    print(
        "UNRESOLVED records are excluded "
        "from candidate-recall requirements."
    )

    print(
        "They must instead remain unresolved "
        "rather than being force-matched."
    )

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()