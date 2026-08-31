from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from .models import LedgerEntry, Payment


FUZZY_TIME_WINDOW_SECONDS = 24 * 60 * 60
AMOUNT_TOLERANCE = 0.01
FUZZY_THRESHOLD = 0.85
AMBIGUITY_MARGIN = 0.05


@dataclass(frozen=True)
class Candidate:
    ledger: LedgerEntry
    score: float
    reference_score: float
    amount_match: bool
    currency_match: bool
    within_time_window: bool


def normalize_reference(value: str) -> str:
    """
    Normalize transaction references for comparison.

    Example:
        order_00123 -> order00123
        order-00123 -> order00123
    """
    return re.sub(r"[^a-zA-Z0-9]", "", value).lower()


def reference_similarity(left: str, right: str) -> float:
    """
    Lightweight deterministic similarity.

    Exact normalized references score 1.0.
    Otherwise use character-level similarity.
    """
    left_normalized = normalize_reference(left)
    right_normalized = normalize_reference(right)

    if left_normalized == right_normalized:
        return 1.0

    if not left_normalized or not right_normalized:
        return 0.0

    # Simple sequence similarity without external dependencies.
    from difflib import SequenceMatcher

    return SequenceMatcher(
        None,
        left_normalized,
        right_normalized,
    ).ratio()


def amount_matches(payment: Payment, ledger: LedgerEntry) -> bool:
    return abs(payment.amount - ledger.amount) <= AMOUNT_TOLERANCE


def timestamp_matches(payment: Payment, ledger: LedgerEntry) -> bool:
    difference = abs(
        (
            payment.created_at - ledger.recorded_at
        ).total_seconds()
    )

    return difference <= FUZZY_TIME_WINDOW_SECONDS


def score_candidate(
    payment: Payment,
    ledger: LedgerEntry,
) -> Candidate:
    ref_score = reference_similarity(
        payment.order_id,
        ledger.order_ref,
    )

    amount_match = amount_matches(payment, ledger)
    currency_match = payment.currency == ledger.currency
    within_window = timestamp_matches(payment, ledger)

    score = 0.0

    # Reference is the strongest identity signal.
    score += ref_score * 0.50

    # Amount is critical financial evidence.
    if amount_match:
        score += 0.30

    # Currency is a mandatory consistency signal.
    if currency_match:
        score += 0.10

    # Timestamp provides supporting evidence.
    if within_window:
        score += 0.10

    return Candidate(
        ledger=ledger,
        score=min(score, 1.0),
        reference_score=ref_score,
        amount_match=amount_match,
        currency_match=currency_match,
        within_time_window=within_window,
    )


def find_candidates(
    payment: Payment,
    ledger_entries: list[LedgerEntry],
) -> list[Candidate]:
    candidates: list[Candidate] = []

    for ledger in ledger_entries:
        candidate = score_candidate(payment, ledger)

        # Candidate generation is deliberately permissive.
        # Decision policy comes later.
        if candidate.reference_score >= 0.60:
            candidates.append(candidate)

    return sorted(
        candidates,
        key=lambda candidate: candidate.score,
        reverse=True,
    )