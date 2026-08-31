"""Generate the initial synthetic dataset in data/generated/."""
from __future__ import annotations

from pathlib import Path
import random
import pandas as pd

SEED = 42
N = 1000
OUT = Path(__file__).resolve().parents[1] / "data" / "generated"


def main() -> None:
    random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    payments = []
    ledger = []
    settlements = []
    truth = []

    for i in range(1, N + 1):
        payment_id = f"pay_{i:05d}"
        order_id = f"ord_{i:05d}"
        ledger_id = f"led_{i:05d}"
        settlement_id = f"set_{i:05d}"
        amount_rupees = random.choice([499, 799, 999, 1499, 2499, 4999])
        fee = round(amount_rupees * 0.02, 2)
        tax = round(fee * 0.18, 2)
        net = round(amount_rupees - fee - tax, 2)

        payments.append({
            "payment_id": payment_id,
            "order_id": order_id,
            "amount": amount_rupees,
            "currency": "INR",
            "status": "captured",
            "payment_ref": order_id,
        })
        ledger.append({
            "ledger_id": ledger_id,
            "order_ref": order_id,
            "amount": amount_rupees,
            "currency": "INR",
            "status": "paid",
        })
        settlements.append({
            "settlement_id": settlement_id,
            "payment_id": payment_id,
            "gross_amount": amount_rupees,
            "fee": fee,
            "tax": tax,
            "net_amount": net,
            "currency": "INR",
        })
        truth.append({
            "payment_id": payment_id,
            "ledger_id": ledger_id,
            "settlement_id": settlement_id,
            "expected_status": "MATCH",
        })

    pd.DataFrame(payments).to_csv(OUT / "payments.csv", index=False)
    pd.DataFrame(ledger).to_csv(OUT / "merchant_ledger.csv", index=False)
    pd.DataFrame(settlements).to_csv(OUT / "settlements.csv", index=False)
    pd.DataFrame(truth).to_csv(OUT / "ground_truth.csv", index=False)
    print(f"Generated {N} baseline records in {OUT}")


if __name__ == "__main__":
    main()
