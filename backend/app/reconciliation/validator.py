from __future__ import annotations

from .models import Settlement


AMOUNT_TOLERANCE = 0.01


def validate_settlement(settlement: Settlement) -> tuple[bool, str]:
    expected_net = round(
        settlement.gross_amount
        - settlement.fee
        - settlement.tax,
        2,
    )

    difference = abs(
        expected_net - settlement.net_amount
    )

    if difference > AMOUNT_TOLERANCE:
        return (
            False,
            (
                "Settlement arithmetic mismatch: "
                f"expected net={expected_net:.2f}, "
                f"actual net={settlement.net_amount:.2f}"
            ),
        )

    return True, "Settlement arithmetic valid"