from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


SEED = 42
NUM_TRANSACTIONS = 1_000

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
GROUND_TRUTH_DIR = ROOT / "data" / "ground_truth"


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    payment_id: str
    order_id: str
    ledger_id: str
    settlement_id: str
    amount: float
    currency: str
    created_at: datetime


SCENARIO_DISTRIBUTION = {
    "MATCH": 650,
    "AMOUNT_MISMATCH": 100,
    "MISSING_LEDGER": 75,
    "MISSING_PAYMENT": 50,
    "DUPLICATE_LEDGER": 40,
    "TIMESTAMP_DRIFT": 30,
    "REFERENCE_CORRUPTION": 25,
    "SETTLEMENT_MISMATCH": 20,
    "AMBIGUOUS_MATCH": 6,
    "UNRESOLVED": 4,
}


def generate_transaction(index: int) -> Transaction:
    amount = round(random.uniform(100, 25_000), 2)
    created_at = datetime(2026, 8, 1) + timedelta(
        minutes=random.randint(0, 60 * 24 * 30)
    )

    return Transaction(
        transaction_id=f"txn_{index:05d}",
        payment_id=f"pay_{index:05d}",
        order_id=f"order_{index:05d}",
        ledger_id=f"ledger_{index:05d}",
        settlement_id=f"set_{index:05d}",
        amount=amount,
        currency="INR",
        created_at=created_at,
    )


def payment_row(txn: Transaction) -> dict[str, object]:
    return {
        "transaction_id": txn.transaction_id,
        "payment_id": txn.payment_id,
        "order_id": txn.order_id,
        "amount": txn.amount,
        "currency": txn.currency,
        "status": "captured",
        "created_at": txn.created_at.isoformat(),
    }


def ledger_row(
    txn: Transaction,
    *,
    amount: float | None = None,
    order_id: str | None = None,
    recorded_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "transaction_id": txn.transaction_id,
        "ledger_id": txn.ledger_id,
        "order_ref": order_id or txn.order_id,
        "amount": amount if amount is not None else txn.amount,
        "currency": txn.currency,
        "status": "paid",
        "recorded_at": (
            recorded_at or txn.created_at + timedelta(seconds=30)
        ).isoformat(),
    }


def settlement_row(
    txn: Transaction,
    *,
    gross_amount: float | None = None,
    fee: float | None = None,
    tax: float | None = None,
) -> dict[str, object]:
    gross = gross_amount if gross_amount is not None else txn.amount
    actual_fee = fee if fee is not None else round(gross * 0.02, 2)
    actual_tax = tax if tax is not None else round(actual_fee * 0.18, 2)
    net = round(gross - actual_fee - actual_tax, 2)

    return {
        "transaction_id": txn.transaction_id,
        "settlement_id": txn.settlement_id,
        "payment_id": txn.payment_id,
        "gross_amount": gross,
        "fee": actual_fee,
        "tax": actual_tax,
        "net_amount": net,
        "currency": txn.currency,
        "settlement_date": (
            txn.created_at + timedelta(days=2)
        ).date().isoformat(),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows generated for {path}")

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_dataset() -> None:
    random.seed(SEED)

    scenarios: list[str] = []

    for scenario, count in SCENARIO_DISTRIBUTION.items():
        scenarios.extend([scenario] * count)

    random.shuffle(scenarios)

    payments: list[dict[str, object]] = []
    ledger: list[dict[str, object]] = []
    settlements: list[dict[str, object]] = []
    ground_truth: list[dict[str, object]] = []

    for index, scenario in enumerate(scenarios, start=1):
        txn = generate_transaction(index)

        # Every transaction starts with a clean payment.
        payments.append(payment_row(txn))

        expected_ledger_id: str | None = txn.ledger_id
        expected_settlement_id: str | None = txn.settlement_id

        if scenario == "MATCH":
            ledger.append(ledger_row(txn))
            settlements.append(settlement_row(txn))

        elif scenario == "AMOUNT_MISMATCH":
            ledger.append(
                ledger_row(
                    txn,
                    amount=round(txn.amount + random.uniform(50, 500), 2),
                )
            )
            settlements.append(settlement_row(txn))

        elif scenario == "MISSING_LEDGER":
            expected_ledger_id = None
            settlements.append(settlement_row(txn))

        elif scenario == "MISSING_PAYMENT":
            # Remove the payment we just added.
            payments.pop()
            ledger.append(ledger_row(txn))
            settlements.append(settlement_row(txn))

        elif scenario == "DUPLICATE_LEDGER":
            ledger.append(ledger_row(txn))
            ledger.append(ledger_row(txn))
            settlements.append(settlement_row(txn))

        elif scenario == "TIMESTAMP_DRIFT":
            ledger.append(
                ledger_row(
                    txn,
                    recorded_at=txn.created_at + timedelta(hours=8),
                )
            )
            settlements.append(settlement_row(txn))

        elif scenario == "REFERENCE_CORRUPTION":
            corrupted_reference = txn.order_id.replace("_", "-")
            ledger.append(
                ledger_row(
                    txn,
                    order_id=corrupted_reference,
                )
            )
            settlements.append(settlement_row(txn))

        elif scenario == "SETTLEMENT_MISMATCH":
            settlements.append(
                settlement_row(
                    txn,
                    gross_amount=round(txn.amount + 100, 2),
                )
            )
            ledger.append(ledger_row(txn))

        elif scenario == "AMBIGUOUS_MATCH":
            ledger.append(ledger_row(txn))

            alternative = dict(
                ledger_row(
                    txn,
                    order_id=txn.order_id[:-1] + "X",
                )
            )
            alternative["ledger_id"] = f"{txn.ledger_id}_ALT"
            ledger.append(alternative)

            settlements.append(settlement_row(txn))

        elif scenario == "UNRESOLVED":
            # Deliberately create conflicting evidence.
            ledger.append(
                ledger_row(
                    txn,
                    amount=round(txn.amount + 1_000, 2),
                    order_id=f"unknown_{index:05d}",
                )
            )

            settlements.append(
                settlement_row(
                    txn,
                    gross_amount=round(txn.amount + 500, 2),
                )
            )

        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        ground_truth.append(
            {
                "transaction_id": txn.transaction_id,
                "payment_id": txn.payment_id
                if scenario != "MISSING_PAYMENT"
                else "",
                "ledger_id": expected_ledger_id or "",
                "settlement_id": expected_settlement_id or "",
                "expected_status": scenario,
            }
        )

    write_csv(RAW_DIR / "payments.csv", payments)
    write_csv(RAW_DIR / "merchant_ledger.csv", ledger)
    write_csv(RAW_DIR / "settlements.csv", settlements)
    write_csv(
        GROUND_TRUTH_DIR / "ground_truth.csv",
        ground_truth,
    )

    print("=" * 60)
    print("ReconAI Synthetic Dataset Generated")
    print("=" * 60)
    print(f"Canonical transactions : {NUM_TRANSACTIONS}")
    print(f"Payments records       : {len(payments)}")
    print(f"Ledger records         : {len(ledger)}")
    print(f"Settlement records     : {len(settlements)}")
    print()
    print("Scenario distribution:")
    for scenario, count in SCENARIO_DISTRIBUTION.items():
        print(f"  {scenario:<22} {count}")
    print()
    print(f"Seed                   : {SEED}")
    print("=" * 60)


if __name__ == "__main__":
    build_dataset()