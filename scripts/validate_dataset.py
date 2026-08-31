from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PAYMENTS = ROOT / "data" / "raw" / "payments.csv"
LEDGER = ROOT / "data" / "raw" / "merchant_ledger.csv"
SETTLEMENTS = ROOT / "data" / "raw" / "settlements.csv"
GROUND_TRUTH = ROOT / "data" / "ground_truth" / "ground_truth.csv"


EXPECTED_TOTAL = 1_000


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def main() -> None:
    payments = read_csv(PAYMENTS)
    ledger = read_csv(LEDGER)
    settlements = read_csv(SETTLEMENTS)
    ground_truth = read_csv(GROUND_TRUTH)

    assert len(ground_truth) == EXPECTED_TOTAL

    scenarios = Counter(
        row["expected_status"]
        for row in ground_truth
    )

    print("=" * 60)
    print("ReconAI Dataset Validation")
    print("=" * 60)

    print(f"Canonical transactions : {len(ground_truth)}")
    print(f"Payments records       : {len(payments)}")
    print(f"Ledger records         : {len(ledger)}")
    print(f"Settlement records     : {len(settlements)}")

    print()
    print("Ground-truth scenarios:")

    for scenario, count in sorted(scenarios.items()):
        print(f"  {scenario:<22} {count}")

    assert scenarios["MATCH"] == 650
    assert scenarios["AMOUNT_MISMATCH"] == 100
    assert scenarios["MISSING_LEDGER"] == 75
    assert scenarios["MISSING_PAYMENT"] == 50
    assert scenarios["DUPLICATE_LEDGER"] == 40
    assert scenarios["TIMESTAMP_DRIFT"] == 30
    assert scenarios["REFERENCE_CORRUPTION"] == 25
    assert scenarios["SETTLEMENT_MISMATCH"] == 20
    assert scenarios["AMBIGUOUS_MATCH"] == 6
    assert scenarios["UNRESOLVED"] == 4

    payment_ids = {
        row["payment_id"]
        for row in payments
    }

    ledger_ids = {
        row["ledger_id"]
        for row in ledger
    }

    settlement_ids = {
        row["settlement_id"]
        for row in settlements
    }

    assert len(payment_ids) == len(payments)
    assert len(settlement_ids) == len(settlements)

    duplicate_ledger_count = len(ledger) - len(ledger_ids)

    print()
    print("Integrity checks:")
    print(f"  Duplicate ledger rows : {duplicate_ledger_count}")

    print()
    print("Dataset validation: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()