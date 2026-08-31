from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.reconciliation.engine import ReconciliationEngine
from backend.app.reconciliation.loader import DataLoader


RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "data" / "results"

OUTPUT_FILE = OUTPUT_DIR / "reconciliation_results.json"


def main() -> None:
    loader = DataLoader(RAW_DIR)

    payments = loader.load_payments()
    ledger = loader.load_ledger()
    settlements = loader.load_settlements()

    print("Loaded:")
    print(f"  Payments    : {len(payments)}")
    print(f"  Ledger      : {len(ledger)}")
    print(f"  Settlements : {len(settlements)}")

    engine = ReconciliationEngine()

    results = engine.reconcile(
        payments=payments,
        ledger=ledger,
        settlements=settlements,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            [result.model_dump(mode="json") for result in results],
            file,
            indent=2,
        )

    counts: dict[str, int] = {}

    for result in results:
        counts[result.status.value] = (
            counts.get(result.status.value, 0) + 1
        )

    print()
    print("=" * 60)
    print("RECONCILIATION COMPLETE")
    print("=" * 60)

    for status, count in sorted(counts.items()):
        print(f"{status:<25} {count}")

    print()
    print(f"Results written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()