from __future__ import annotations

from typing import Any

from .schemas import (
    RazorpayPaymentRecord,
    RazorpaySettlementRecord,
)


def _subunits_to_major(
    amount: Any,
) -> float:
    """
    Convert Razorpay currency subunits to major units.

    Razorpay payment APIs return amounts in currency subunits.
    Example:
        10000 -> 100.00
    """

    try:
        amount_subunits = int(
            amount
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"Invalid Razorpay amount: {amount!r}"
        ) from exc

    return round(
        amount_subunits / 100.0,
        2,
    )


def normalize_payment(
    payload: dict[str, Any],
) -> RazorpayPaymentRecord:
    """
    Normalize a Razorpay payment API payload.
    """

    payment_id = str(
        payload.get(
            "id",
            "",
        )
    ).strip()

    if not payment_id:
        raise ValueError(
            "Razorpay payment is missing id."
        )

    raw_amount = payload.get(
        "amount"
    )

    try:
        amount_subunits = int(
            raw_amount
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Razorpay payment has invalid amount."
        ) from exc

    currency = str(
        payload.get(
            "currency",
            "",
        )
    ).strip().upper()

    if not currency:
        raise ValueError(
            "Razorpay payment is missing currency."
        )

    created_at = payload.get(
        "created_at"
    )

    try:
        created_at_int = int(
            created_at
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Razorpay payment has invalid created_at."
        ) from exc

    notes = payload.get(
        "notes",
        {},
    )

    if not isinstance(
        notes,
        dict,
    ):
        notes = {}

    order_id_raw = payload.get(
        "order_id"
    )

    order_id = (
        str(
            order_id_raw
        )
        if order_id_raw
        else None
    )

    return RazorpayPaymentRecord(
        payment_id=payment_id,
        order_id=order_id,
        amount=_subunits_to_major(
            amount_subunits
        ),
        amount_subunits=amount_subunits,
        currency=currency,
        status=str(
            payload.get(
                "status",
                "unknown",
            )
        ),
        captured=bool(
            payload.get(
                "captured",
                False,
            )
        ),
        created_at=created_at_int,
        method=(
            str(
                payload[
                    "method"
                ]
            )
            if payload.get(
                "method"
            )
            else None
        ),
        email=(
            str(
                payload[
                    "email"
                ]
            )
            if payload.get(
                "email"
            )
            else None
        ),
        contact=(
            str(
                payload[
                    "contact"
                ]
            )
            if payload.get(
                "contact"
            )
            else None
        ),
        description=(
            str(
                payload[
                    "description"
                ]
            )
            if payload.get(
                "description"
            )
            else None
        ),
        notes=notes,
    )


def normalize_settlement(
    payload: dict[str, Any],
) -> RazorpaySettlementRecord:
    """
    Normalize a Razorpay settlement API payload.
    """

    settlement_id = str(
        payload.get(
            "id",
            "",
        )
    ).strip()

    if not settlement_id:
        raise ValueError(
            "Razorpay settlement is missing id."
        )

    try:
        amount_subunits = int(
            payload.get(
                "amount",
                0,
            )
        )

        fees_subunits = int(
            payload.get(
                "fees",
                0,
            )
        )

        tax_subunits = int(
            payload.get(
                "tax",
                0,
            )
        )

        created_at = int(
            payload.get(
                "created_at"
            )
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Razorpay settlement contains "
            "invalid numeric fields."
        ) from exc

    return RazorpaySettlementRecord(
        settlement_id=settlement_id,
        amount=_subunits_to_major(
            amount_subunits
        ),
        amount_subunits=amount_subunits,
        status=str(
            payload.get(
                "status",
                "unknown",
            )
        ),
        fees=_subunits_to_major(
            fees_subunits
        ),
        fees_subunits=fees_subunits,
        tax=_subunits_to_major(
            tax_subunits
        ),
        tax_subunits=tax_subunits,
        utr=(
            str(
                payload[
                    "utr"
                ]
            )
            if payload.get(
                "utr"
            )
            else None
        ),
        created_at=created_at,
    )