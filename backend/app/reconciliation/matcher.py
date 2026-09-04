from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


from .models import LedgerEntry, Payment


AMOUNT_TOLERANCE = 0.01

REFERENCE_BLOCK_THRESHOLD = 0.80

FUZZY_THRESHOLD = 0.80

FUZZY_TIME_WINDOW_SECONDS = 24 * 60 * 60

AMBIGUITY_MARGIN = 0.05

REFERENCE_PREFIX_LENGTH = 8


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
    Normalize a payment/ledger reference.

    Examples:

        order_00123
        order-00123
        ORDER 00123

    become:

        order00123
    """
    return re.sub(
        r"[^a-zA-Z0-9]",
        "",
        value,
    ).lower()


def reference_similarity(
    left: str,
    right: str,
) -> float:
    """
    Calculate deterministic reference similarity.
    """
    left_normalized = normalize_reference(left)
    right_normalized = normalize_reference(right)

    if not left_normalized or not right_normalized:
        return 0.0

    if left_normalized == right_normalized:
        return 1.0

    return SequenceMatcher(
        None,
        left_normalized,
        right_normalized,
    ).ratio()


def amount_matches(
    payment: Payment,
    ledger: LedgerEntry,
) -> bool:
    return (
        abs(
            payment.amount
            - ledger.amount
        )
        <= AMOUNT_TOLERANCE
    )


def timestamp_matches(
    payment: Payment,
    ledger: LedgerEntry,
) -> bool:
    difference = abs(
        (
            payment.created_at
            - ledger.recorded_at
        ).total_seconds()
    )

    return (
        difference
        <= FUZZY_TIME_WINDOW_SECONDS
    )


def score_candidate(
    payment: Payment,
    ledger: LedgerEntry,
) -> Candidate:
    """
    Score independent reconciliation evidence.

    Reference: 50%
    Amount:    30%
    Currency:  10%
    Time:      10%
    """

    ref_score = reference_similarity(
        payment.order_id,
        ledger.order_ref,
    )

    amount_match = amount_matches(
        payment,
        ledger,
    )

    currency_match = (
        payment.currency
        == ledger.currency
    )

    within_time_window = timestamp_matches(
        payment,
        ledger,
    )

    score = (
        ref_score * 0.50
        + (0.30 if amount_match else 0.0)
        + (0.10 if currency_match else 0.0)
        + (
            0.10
            if within_time_window
            else 0.0
        )
    )

    return Candidate(
        ledger=ledger,
        score=min(
            score,
            1.0,
        ),
        reference_score=ref_score,
        amount_match=amount_match,
        currency_match=currency_match,
        within_time_window=within_time_window,
    )


def _reference_block_key(
    reference: str,
) -> str:
    normalized = normalize_reference(
        reference
    )

    if len(normalized) <= REFERENCE_PREFIX_LENGTH:
        return normalized

    return normalized[
        :REFERENCE_PREFIX_LENGTH
    ]


def _build_transaction_index(
    ledger_entries: list[LedgerEntry],
) -> dict[
    str,
    list[LedgerEntry],
]:
    """
    Build an O(1)-style lookup index for
    transaction_id.
    """

    index: dict[
        str,
        list[LedgerEntry],
    ] = {}

    for ledger in ledger_entries:
        index.setdefault(
            ledger.transaction_id,
            [],
        ).append(ledger)

    return index


def _build_reference_index(
    ledger_entries: list[LedgerEntry],
) -> dict[
    str,
    list[LedgerEntry],
]:
    """
    Build an exact normalized-reference index.
    """

    index: dict[
        str,
        list[LedgerEntry],
    ] = {}

    for ledger in ledger_entries:
        reference = normalize_reference(
            ledger.order_ref
        )

        if not reference:
            continue

        index.setdefault(
            reference,
            [],
        ).append(ledger)

    return index


def _build_prefix_index(
    ledger_entries: list[LedgerEntry],
) -> dict[
    str,
    list[LedgerEntry],
]:
    """
    Build a conservative reference-prefix index.
    """

    index: dict[
        str,
        list[LedgerEntry],
    ] = {}

    for ledger in ledger_entries:
        key = _reference_block_key(
            ledger.order_ref
        )

        if not key:
            continue

        index.setdefault(
            key,
            [],
        ).append(ledger)

    return index


def generate_candidates(
    payment: Payment,
    ledger_entries: list[LedgerEntry],
) -> list[LedgerEntry]:
    """
    Hierarchical candidate generation.

    Tier 1:
        Exact transaction_id.

    Tier 2:
        Exact normalized reference.

    Tier 3:
        Conservative reference-prefix recovery.

    The tiers are fallback-based rather than broad UNION
    blocking. This keeps the candidate set small while
    preserving recovery paths for corrupted references.
    """

    if not ledger_entries:
        return []

    transaction_index = _build_transaction_index(
        ledger_entries
    )

    transaction_candidates = (
        transaction_index.get(
            payment.transaction_id,
            [],
        )
    )

    # ---------------------------------------------------------
    # TIER 1
    #
    # Exact transaction identity is our strongest blocking key.
    # ---------------------------------------------------------

    if transaction_candidates:
        return sorted(
            transaction_candidates,
            key=lambda ledger: ledger.ledger_id,
        )

    # ---------------------------------------------------------
    # TIER 2
    #
    # Exact normalized order/reference.
    # ---------------------------------------------------------

    reference_index = _build_reference_index(
        ledger_entries
    )

    normalized_reference = (
        normalize_reference(
            payment.order_id
        )
    )

    if normalized_reference:
        exact_reference_candidates = (
            reference_index.get(
                normalized_reference,
                [],
            )
        )

        if exact_reference_candidates:
            return sorted(
                exact_reference_candidates,
                key=lambda ledger: (
                    ledger.ledger_id
                ),
            )

    # ---------------------------------------------------------
    # TIER 3
    #
    # Conservative prefix-based reference recovery.
    #
    # We do not fall back to amount/date-wide blocking here.
    # Those signals remain evidence for scoring rather than
    # broad candidate-generation keys.
    # ---------------------------------------------------------

    prefix_index = _build_prefix_index(
        ledger_entries
    )

    prefix = _reference_block_key(
        payment.order_id
    )

    if not prefix:
        return []

    recovered_candidates: list[
        LedgerEntry
    ] = []

    for ledger in prefix_index.get(
        prefix,
        [],
    ):
        similarity = reference_similarity(
            payment.order_id,
            ledger.order_ref,
        )

        if similarity >= REFERENCE_BLOCK_THRESHOLD:
            recovered_candidates.append(
                ledger
            )

    recovered_candidates.sort(
        key=lambda ledger: ledger.ledger_id
    )

    return recovered_candidates


def find_candidates(
    payment: Payment,
    ledger_entries: list[LedgerEntry],
) -> list[Candidate]:
    """
    Generate and score candidates.

    Candidate generation is separated from evidence
    scoring so the final decision remains auditable.
    """

    ledger_candidates = generate_candidates(
        payment,
        ledger_entries,
    )

    scored_candidates = [
        score_candidate(
            payment,
            ledger,
        )
        for ledger in ledger_candidates
    ]

    return sorted(
        scored_candidates,
        key=lambda candidate: (
            -candidate.score,
            candidate.ledger.ledger_id,
        ),
    )