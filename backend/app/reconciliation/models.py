from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MatchStatus(StrEnum):
    MATCHED = "MATCHED"
    FUZZY_MATCHED = "FUZZY_MATCHED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    MISSING_PAYMENT = "MISSING_PAYMENT"
    MISSING_LEDGER = "MISSING_LEDGER"
    DUPLICATE = "DUPLICATE"
    SETTLEMENT_MISMATCH = "SETTLEMENT_MISMATCH"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


class MatchMethod(StrEnum):
    EXACT = "EXACT"
    FUZZY = "FUZZY"
    NONE = "NONE"


class Payment(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_id: str
    payment_id: str
    order_id: str
    amount: float = Field(ge=0)
    currency: str
    status: str
    created_at: datetime


class LedgerEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_id: str
    ledger_id: str
    order_ref: str
    amount: float = Field(ge=0)
    currency: str
    status: str
    recorded_at: datetime


class Settlement(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_id: str
    settlement_id: str
    payment_id: str
    gross_amount: float = Field(ge=0)
    fee: float = Field(ge=0)
    tax: float = Field(ge=0)
    net_amount: float
    currency: str
    settlement_date: str


class MatchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_id: str
    payment_id: str | None = None
    ledger_id: str | None = None
    settlement_id: str | None = None

    status: MatchStatus
    method: MatchMethod

    confidence: float = Field(ge=0, le=1)

    amount_difference: float = 0.0
    candidate_count: int = 0

    reason: str