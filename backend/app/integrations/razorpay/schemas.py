from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RazorpayPaymentRecord(
    BaseModel,
):
    """
    Normalized read-only Razorpay payment.

    Monetary amounts are represented in major currency units
    inside ReconAI, while the original Razorpay subunit value
    is preserved separately.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    payment_id: str

    order_id: str | None = None

    amount: float

    amount_subunits: int

    currency: str

    status: str

    captured: bool

    created_at: int

    method: str | None = None

    email: str | None = None

    contact: str | None = None

    description: str | None = None

    notes: dict[str, Any] = Field(
        default_factory=dict,
    )


class RazorpaySettlementRecord(
    BaseModel,
):
    """
    Normalized Razorpay settlement entity.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    settlement_id: str

    amount: float

    amount_subunits: int

    status: str

    fees: float

    fees_subunits: int

    tax: float

    tax_subunits: int

    utr: str | None = None

    created_at: int


class RazorpayCollection(
    BaseModel,
):
    """
    Generic Razorpay collection response.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    entity: str | None = None

    count: int = 0

    items: list[
        dict[str, Any]
    ] = Field(
        default_factory=list,
    )


class RazorpayWebhookEnvelope(
    BaseModel,
):
    """
    Minimal validated webhook envelope.

    The raw request body must still be used for signature
    verification before this model is created.
    """

    model_config = ConfigDict(
        extra="allow",
    )

    event: str

    account_id: str | None = None

    contains: list[str] = Field(
        default_factory=list,
    )

    payload: dict[
        str,
        Any,
    ]