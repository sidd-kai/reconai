from __future__ import annotations

from pathlib import Path

import pandas as pd

from .models import LedgerEntry, Payment, Settlement


class DataLoader:
    """Load and validate reconciliation source files."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def load_payments(self) -> list[Payment]:
        frame = pd.read_csv(self.data_dir / "payments.csv")

        return [
            Payment(
                transaction_id=row["transaction_id"],
                payment_id=row["payment_id"],
                order_id=row["order_id"],
                amount=float(row["amount"]),
                currency=row["currency"],
                status=row["status"],
                created_at=row["created_at"],
            )
            for _, row in frame.iterrows()
        ]

    def load_ledger(self) -> list[LedgerEntry]:
        frame = pd.read_csv(self.data_dir / "merchant_ledger.csv")

        return [
            LedgerEntry(
                transaction_id=row["transaction_id"],
                ledger_id=row["ledger_id"],
                order_ref=row["order_ref"],
                amount=float(row["amount"]),
                currency=row["currency"],
                status=row["status"],
                recorded_at=row["recorded_at"],
            )
            for _, row in frame.iterrows()
        ]

    def load_settlements(self) -> list[Settlement]:
        frame = pd.read_csv(self.data_dir / "settlements.csv")

        return [
            Settlement(
                transaction_id=row["transaction_id"],
                settlement_id=row["settlement_id"],
                payment_id=row["payment_id"],
                gross_amount=float(row["gross_amount"]),
                fee=float(row["fee"]),
                tax=float(row["tax"]),
                net_amount=float(row["net_amount"]),
                currency=row["currency"],
                settlement_date=row["settlement_date"],
            )
            for _, row in frame.iterrows()
        ]