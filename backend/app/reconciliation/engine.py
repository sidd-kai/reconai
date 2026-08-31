from __future__ import annotations

from collections import Counter

from .matcher import (
    AMBIGUITY_MARGIN,
    FUZZY_THRESHOLD,
    find_candidates,
)
from .models import (
    LedgerEntry,
    MatchMethod,
    MatchResult,
    MatchStatus,
    Payment,
    Settlement,
)
from .validator import validate_settlement


class ReconciliationEngine:
    """
    Deterministic multi-source reconciliation engine.

    Ground truth is intentionally NOT used here.
    """

    def reconcile(
        self,
        payments: list[Payment],
        ledger: list[LedgerEntry],
        settlements: list[Settlement],
    ) -> list[MatchResult]:

        results: list[MatchResult] = []

        settlement_by_payment = {
            settlement.payment_id: settlement
            for settlement in settlements
        }

        payment_ids = {
            payment.payment_id
            for payment in payments
        }

        # ---------------------------------------------------------
        # Phase 1: Payment -> Ledger reconciliation
        # ---------------------------------------------------------

        matched_ledger_ids: set[str] = set()

        for payment in payments:
            candidates = find_candidates(
                payment,
                ledger,
            )

            if not candidates:
                settlement = settlement_by_payment.get(
                    payment.payment_id
                )

                settlement_id = (
                    settlement.settlement_id
                    if settlement
                    else None
                )

                results.append(
                    MatchResult(
                        transaction_id=payment.transaction_id,
                        payment_id=payment.payment_id,
                        ledger_id=None,
                        settlement_id=settlement_id,
                        status=MatchStatus.MISSING_LEDGER,
                        method=MatchMethod.NONE,
                        confidence=0.0,
                        candidate_count=0,
                        reason="No viable ledger candidate found",
                    )
                )

                continue

            top = candidates[0]

            # Multiple strong candidates = unsafe to auto-match.
            strong_candidates = [
                candidate
                for candidate in candidates
                if candidate.score >= FUZZY_THRESHOLD
            ]

            if len(strong_candidates) > 1:
                second = strong_candidates[1]

                if (
                    top.score - second.score
                    <= AMBIGUITY_MARGIN
                ):
                    results.append(
                        MatchResult(
                            transaction_id=payment.transaction_id,
                            payment_id=payment.payment_id,
                            ledger_id=None,
                            settlement_id=None,
                            status=MatchStatus.AMBIGUOUS,
                            method=MatchMethod.NONE,
                            confidence=top.score,
                            candidate_count=len(
                                strong_candidates
                            ),
                            reason=(
                                "Multiple high-confidence "
                                "ledger candidates"
                            ),
                        )
                    )

                    continue

            ledger_entry = top.ledger

            # Detect duplicate ledger entries for the same
            # normalized business reference.
            same_reference = [
                entry
                for entry in ledger
                if (
                    entry.order_ref == ledger_entry.order_ref
                    and entry.amount == ledger_entry.amount
                    and entry.currency == ledger_entry.currency
                )
            ]

            if len(same_reference) > 1:
                results.append(
                    MatchResult(
                        transaction_id=payment.transaction_id,
                        payment_id=payment.payment_id,
                        ledger_id=None,
                        settlement_id=None,
                        status=MatchStatus.DUPLICATE,
                        method=MatchMethod.NONE,
                        confidence=top.score,
                        candidate_count=len(same_reference),
                        reason=(
                            "Multiple duplicate ledger "
                            "records detected"
                        ),
                    )
                )

                continue

            # Financial amount mismatch gets quarantined.
            if not top.amount_match:
                results.append(
                    MatchResult(
                        transaction_id=payment.transaction_id,
                        payment_id=payment.payment_id,
                        ledger_id=ledger_entry.ledger_id,
                        settlement_id=None,
                        status=MatchStatus.AMOUNT_MISMATCH,
                        method=MatchMethod.FUZZY,
                        confidence=top.score,
                        amount_difference=round(
                            abs(
                                payment.amount
                                - ledger_entry.amount
                            ),
                            2,
                        ),
                        candidate_count=len(candidates),
                        reason=(
                            "Payment and ledger references "
                            "are related but amounts differ"
                        ),
                    )
                )

                continue

            # Settlement validation.
            settlement = settlement_by_payment.get(
                payment.payment_id
            )

            if settlement is None:
                results.append(
                    MatchResult(
                        transaction_id=payment.transaction_id,
                        payment_id=payment.payment_id,
                        ledger_id=ledger_entry.ledger_id,
                        settlement_id=None,
                        status=MatchStatus.UNRESOLVED,
                        method=MatchMethod.FUZZY,
                        confidence=top.score,
                        candidate_count=len(candidates),
                        reason="Settlement record not found",
                    )
                )

                continue

            settlement_valid, settlement_reason = (
                validate_settlement(settlement)
            )

            if (
                not settlement_valid
                or abs(
                    settlement.gross_amount
                    - payment.amount
                ) > 0.01
            ):
                results.append(
                    MatchResult(
                        transaction_id=payment.transaction_id,
                        payment_id=payment.payment_id,
                        ledger_id=ledger_entry.ledger_id,
                        settlement_id=settlement.settlement_id,
                        status=MatchStatus.SETTLEMENT_MISMATCH,
                        method=MatchMethod.FUZZY,
                        confidence=top.score,
                        amount_difference=round(
                            abs(
                                settlement.gross_amount
                                - payment.amount
                            ),
                            2,
                        ),
                        candidate_count=len(candidates),
                        reason=settlement_reason,
                    )
                )

                continue

            # Final safe match.
            method = (
                MatchMethod.EXACT
                if (
                    top.reference_score == 1.0
                    and top.amount_match
                    and top.currency_match
                )
                else MatchMethod.FUZZY
            )

            status = (
                MatchStatus.MATCHED
                if method == MatchMethod.EXACT
                else MatchStatus.FUZZY_MATCHED
            )

            matched_ledger_ids.add(
                ledger_entry.ledger_id
            )

            results.append(
                MatchResult(
                    transaction_id=payment.transaction_id,
                    payment_id=payment.payment_id,
                    ledger_id=ledger_entry.ledger_id,
                    settlement_id=settlement.settlement_id,
                    status=status,
                    method=method,
                    confidence=top.score,
                    amount_difference=0.0,
                    candidate_count=len(candidates),
                    reason=(
                        "Payment, ledger and settlement "
                        "evidence consistent"
                    ),
                )
            )

        # ---------------------------------------------------------
        # Phase 2: Detect ledger records without payments
        # ---------------------------------------------------------

        #processed_transactions = {
        #    result.transaction_id
        #    for result in results
        #}

        for ledger_entry in ledger:
            if ledger_entry.ledger_id in matched_ledger_ids:
                continue

            # We use payment_id/order evidence here rather than
            # transaction_id for reconciliation.
            possible_payment = next(
                (
                    payment
                    for payment in payments
                    if (
                        payment.order_id
                        == ledger_entry.order_ref
                    )
                ),
                None,
            )

            if possible_payment is not None:
                continue

            # Ledger entry with no corresponding payment.
            results.append(
                MatchResult(
                    transaction_id=ledger_entry.transaction_id,
                    payment_id=None,
                    ledger_id=ledger_entry.ledger_id,
                    settlement_id=None,
                    status=MatchStatus.MISSING_PAYMENT,
                    method=MatchMethod.NONE,
                    confidence=0.0,
                    candidate_count=0,
                    reason=(
                        "Ledger entry has no corresponding "
                        "payment record"
                    ),
                )
            )

        return results