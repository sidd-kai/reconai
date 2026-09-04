from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.app.reconciliation.matcher import (
    score_candidate,
)
from backend.app.reconciliation.models import (
    LedgerEntry,
    Payment,
)


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


def main() -> None:
    payments = load_payments()
    ledger = load_ledger()
    ground_truth = pd.read_csv(GROUND_TRUTH_FILE)

    ground_truth_map = {
        str(row["transaction_id"]): row
        for row in ground_truth.to_dict(
            orient="records"
        )
    }

    ledger_by_transaction: dict[
        str,
        list[LedgerEntry],
    ] = {}

    for entry in ledger:
        ledger_by_transaction.setdefault(
            entry.transaction_id,
            [],
        ).append(entry)

    duplicate_cases = 0
    clear_winners = 0
    ambiguous_cases = 0
    correct_winners = 0

    print()
    print("=" * 72)
    print("ReconAI DUPLICATE CANDIDATE ANALYSIS")
    print("=" * 72)

    for payment in payments:
        candidates = ledger_by_transaction.get(
            payment.transaction_id,
            [],
        )

        if len(candidates) != 2:
            continue

        duplicate_cases += 1

        scored = [
            score_candidate(
                payment,
                candidate,
            )
            for candidate in candidates
        ]

        scored.sort(
            key=lambda candidate: (
                -candidate.score,
                candidate.ledger.ledger_id,
            )
        )

        best = scored[0]
        second = scored[1]

        margin = (
            best.score
            - second.score
        )

        truth = ground_truth_map.get(
            payment.transaction_id
        )

        expected_ledger = None

        if truth is not None:
            value = truth["ledger_id"]

            if not pd.isna(value):
                expected_ledger = str(value)

        is_clear = (
            margin >= 0.05
        )

        if is_clear:
            clear_winners += 1

            if (
                expected_ledger
                == best.ledger.ledger_id
            ):
                correct_winners += 1

        else:
            ambiguous_cases += 1

        print()
        print(
            f"{payment.transaction_id}"
        )

        print(
            f"  Candidate 1: "
            f"{best.ledger.ledger_id} "
            f"score={best.score:.3f}"
        )

        print(
            f"  Candidate 2: "
            f"{second.ledger.ledger_id} "
            f"score={second.score:.3f}"
        )

        print(
            f"  Margin     : "
            f"{margin:.3f}"
        )

        print(
            f"  Expected   : "
            f"{expected_ledger}"
        )

        print(
            f"  Decision   : "
            f"{'CLEAR WINNER' if is_clear else 'AMBIGUOUS'}"
        )

    print()
    print("-" * 72)
    print("SUMMARY")
    print("-" * 72)

    print(
        f"Duplicate candidate cases : "
        f"{duplicate_cases}"
    )

    print(
        f"Clear winners              : "
        f"{clear_winners}"
    )

    print(
        f"Ambiguous cases            : "
        f"{ambiguous_cases}"
    )

    print(
        f"Correct clear winners      : "
        f"{correct_winners}"
    )

    if clear_winners:
        accuracy = (
            correct_winners
            / clear_winners
        )
    else:
        accuracy = 0.0

    print(
        f"Winner accuracy            : "
        f"{accuracy:.2%}"
    )

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()