from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

PAYMENTS_FILE = ROOT / "data/raw/payments.csv"
LEDGER_FILE = ROOT / "data/raw/merchant_ledger.csv"
GROUND_TRUTH_FILE = ROOT / "data/ground_truth/ground_truth.csv"


def main() -> None:
    payments = pd.read_csv(PAYMENTS_FILE)
    ledger = pd.read_csv(LEDGER_FILE)
    ground_truth = pd.read_csv(GROUND_TRUTH_FILE)

    gt = {
        str(row["transaction_id"]): row
        for row in ground_truth.to_dict(
            orient="records"
        )
    }

    ledger_by_transaction: dict[
        str,
        list[str],
    ] = {}

    for row in ledger.to_dict(
        orient="records"
    ):
        transaction_id = str(
            row["transaction_id"]
        )

        ledger_by_transaction.setdefault(
            transaction_id,
            [],
        ).append(
            str(row["ledger_id"])
        )

    evaluated = 0
    tier1_hits = 0
    tier1_unique_hits = 0
    tier1_ambiguous = 0
    tier1_misses = 0

    distribution: Counter[int] = Counter()

    miss_ids: list[str] = []

    for row in payments.to_dict(
        orient="records"
    ):
        transaction_id = str(
            row["transaction_id"]
        )

        truth = gt.get(
            transaction_id
        )

        if truth is None:
            continue

        expected_status = str(
            truth["expected_status"]
        )

        if expected_status == "UNRESOLVED":
            continue

        expected_ledger = truth["ledger_id"]

        if pd.isna(expected_ledger):
            continue

        evaluated += 1

        candidates = ledger_by_transaction.get(
            transaction_id,
            [],
        )

        distribution[
            len(candidates)
        ] += 1

        if str(expected_ledger) not in candidates:
            tier1_misses += 1
            miss_ids.append(
                transaction_id
            )
            continue

        tier1_hits += 1

        if len(candidates) == 1:
            tier1_unique_hits += 1
        else:
            tier1_ambiguous += 1

    recall = (
        tier1_hits / evaluated
        if evaluated
        else 0.0
    )

    unique_rate = (
        tier1_unique_hits / evaluated
        if evaluated
        else 0.0
    )

    ambiguity_rate = (
        tier1_ambiguous / evaluated
        if evaluated
        else 0.0
    )

    print()
    print("=" * 72)
    print("ReconAI BLOCKING TIER BENCHMARK")
    print("=" * 72)

    print()
    print("EVALUATED TRANSACTIONS")
    print("-" * 72)
    print(
        f"Resolvable transactions : {evaluated}"
    )

    print()
    print("TIER 1 — TRANSACTION ID")
    print("-" * 72)

    print(
        f"Recall                   : "
        f"{recall:.2%}"
    )

    print(
        f"Correctly retained       : "
        f"{tier1_hits}/{evaluated}"
    )

    print(
        f"Unique candidate         : "
        f"{tier1_unique_hits}/{evaluated} "
        f"({unique_rate:.2%})"
    )

    print(
        f"Multiple candidates      : "
        f"{tier1_ambiguous}/{evaluated} "
        f"({ambiguity_rate:.2%})"
    )

    print(
        f"Misses                   : "
        f"{tier1_misses}"
    )

    print()
    print("CANDIDATE COUNT DISTRIBUTION")
    print("-" * 72)

    for count in sorted(distribution):
        print(
            f"{count} candidate(s)          : "
            f"{distribution[count]}"
        )

    if miss_ids:
        print()
        print("TIER 1 MISSES")
        print("-" * 72)

        for transaction_id in miss_ids:
            print(transaction_id)

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()