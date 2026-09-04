from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

PAYMENTS_FILE = ROOT / "data/raw/payments.csv"
LEDGER_FILE = ROOT / "data/raw/merchant_ledger.csv"
GROUND_TRUTH_FILE = ROOT / "data/ground_truth/ground_truth.csv"

MISS_IDS = {
    "txn_00488",
    "txn_00527",
    "txn_00793",
    "txn_00809",
}


def main() -> None:
    payments = pd.read_csv(PAYMENTS_FILE)
    ledger = pd.read_csv(LEDGER_FILE)
    ground_truth = pd.read_csv(GROUND_TRUTH_FILE)

    print()
    print("=" * 72)
    print("ReconAI CANDIDATE MISS INVESTIGATION")
    print("=" * 72)

    for transaction_id in sorted(MISS_IDS):
        print()
        print("-" * 72)
        print(f"TRANSACTION: {transaction_id}")
        print("-" * 72)

        payment_rows = payments[
            payments["transaction_id"].astype(str)
            == transaction_id
        ]

        gt_rows = ground_truth[
            ground_truth["transaction_id"].astype(str)
            == transaction_id
        ]

        if payment_rows.empty:
            print("Payment: NOT FOUND")
            continue

        if gt_rows.empty:
            print("Ground truth: NOT FOUND")
            continue

        payment = payment_rows.iloc[0]
        gt = gt_rows.iloc[0]

        expected_ledger_id = gt["ledger_id"]

        print()
        print("PAYMENT")
        print(f"  transaction_id : {payment['transaction_id']}")
        print(f"  payment_id     : {payment['payment_id']}")
        print(f"  order_id       : {payment['order_id']}")
        print(f"  amount         : {payment['amount']}")
        print(f"  currency       : {payment['currency']}")
        print(f"  status         : {payment['status']}")
        print(f"  created_at     : {payment['created_at']}")

        print()
        print("GROUND TRUTH")
        print(f"  expected_status: {gt['expected_status']}")
        print(f"  ledger_id      : {expected_ledger_id}")

        if pd.isna(expected_ledger_id):
            print("  No ledger is expected for this transaction.")
            continue

        expected_ledger_id = str(expected_ledger_id)

        matching_ledger = ledger[
            ledger["ledger_id"].astype(str)
            == expected_ledger_id
        ]

        print()
        print("EXPECTED LEDGER")
        if matching_ledger.empty:
            print("  NOT FOUND IN RAW LEDGER")
            continue

        ledger_row = matching_ledger.iloc[0]

        print(f"  ledger_id      : {ledger_row['ledger_id']}")
        print(f"  transaction_id : {ledger_row['transaction_id']}")
        print(f"  order_ref      : {ledger_row['order_ref']}")
        print(f"  amount         : {ledger_row['amount']}")
        print(f"  currency       : {ledger_row['currency']}")
        print(f"  status         : {ledger_row['status']}")
        print(f"  recorded_at    : {ledger_row['recorded_at']}")

        print()
        print("COMPARISON")
        print(
            f"  transaction_id equal : "
            f"{str(payment['transaction_id']) == str(ledger_row['transaction_id'])}"
        )
        print(
            f"  order/reference equal: "
            f"{str(payment['order_id']) == str(ledger_row['order_ref'])}"
        )
        print(
            f"  currency equal       : "
            f"{str(payment['currency']) == str(ledger_row['currency'])}"
        )
        print(
            f"  amount equal         : "
            f"{float(payment['amount']) == float(ledger_row['amount'])}"
        )

        amount_difference = abs(
            float(payment["amount"])
            - float(ledger_row["amount"])
        )

        print(
            f"  amount difference    : "
            f"{amount_difference:.2f}"
        )

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()