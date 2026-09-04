from __future__ import annotations

import statistics
from pathlib import Path

import pandas as pd

from backend.app.reconciliation.models import LedgerEntry, Payment


ROOT = Path(__file__).resolve().parents[1]

PAYMENTS_FILE = ROOT / "data/raw/payments.csv"
LEDGER_FILE = ROOT / "data/raw/merchant_ledger.csv"
GROUND_TRUTH_FILE = ROOT / "data/ground_truth/ground_truth.csv"


def load_payments() -> list[Payment]:
    df = pd.read_csv(PAYMENTS_FILE)

    return [
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
        for row in df.to_dict(orient="records")
    ]


def load_ledger() -> list[LedgerEntry]:
    df = pd.read_csv(LEDGER_FILE)

    return [
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
        for row in df.to_dict(orient="records")
    ]


def percentile(
    values: list[int],
    percentile_value: float,
) -> float:
    ordered = sorted(values)

    if not ordered:
        return 0.0

    position = (
        len(ordered) - 1
    ) * percentile_value

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
    ground_truth = pd.read_csv(GROUND_TRUTH_FILE)

    ledger_by_transaction: dict[
        str,
        list[LedgerEntry],
    ] = {}

    for entry in ledger:
        ledger_by_transaction.setdefault(
            entry.transaction_id,
            [],
        ).append(entry)

    gt = {
        str(row["transaction_id"]): row
        for row in ground_truth.to_dict(
            orient="records"
        )
    }

    candidate_counts: list[int] = []

    evaluated = 0
    hits = 0
    misses: list[str] = []

    for payment in payments:
        candidates = ledger_by_transaction.get(
            payment.transaction_id,
            [],
        )

        candidate_counts.append(
            len(candidates)
        )

        row = gt.get(
            payment.transaction_id
        )

        if row is None:
            continue

        status = str(
            row["expected_status"]
        )

        if status == "UNRESOLVED":
            continue

        expected_ledger = row["ledger_id"]

        if pd.isna(expected_ledger):
            continue

        evaluated += 1

        candidate_ids = {
            candidate.ledger_id
            for candidate in candidates
        }

        if str(expected_ledger) in candidate_ids:
            hits += 1
        else:
            misses.append(
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

    recall = (
        hits / evaluated
        if evaluated
        else 0.0
    )

    print()
    print("=" * 72)
    print("ReconAI TRANSACTION BLOCK BENCHMARK")
    print("=" * 72)

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
        f"{recall:.2%}"
    )

    print(
        f"Correctly retained         : "
        f"{hits}/{evaluated}"
    )

    if misses:
        print()
        print("MISSES")
        print("-" * 72)

        for transaction_id in misses:
            print(transaction_id)

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()