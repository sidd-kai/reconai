from __future__ import annotations

from pathlib import Path

from .audit import AuditLogger
from .exceptions import ExceptionManifest
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

    Every decision is:
        1. Returned as a MatchResult.
        2. Written to the immutable audit log.
        3. Written to the exception manifest when unsafe
           reconciliation is detected.

    Safety principles:
        - Never silently consume the same ledger twice.
        - Never auto-resolve ambiguous candidate sets.
        - Never auto-resolve structurally conflicting ledger evidence.
        - Quarantine unsafe reconciliation instead of guessing.
    """

    def __init__(
        self,
        *,
        audit_path: Path | None = None,
        exception_path: Path | None = None,
    ) -> None:

        self.audit_logger = AuditLogger(
            audit_path
            or Path(
                "data/results/audit.jsonl"
            )
        )

        self.exception_manifest = ExceptionManifest(
            exception_path
            or Path(
                "data/results/exceptions.jsonl"
            )
        )

    # ==================================================================
    # AUDIT / EXCEPTION RECORDING
    # ==================================================================

    def _record_decision(
        self,
        result: MatchResult,
    ) -> None:
        """
        Write every reconciliation decision to the immutable
        audit trail.
        """

        self.audit_logger.append(
            event_type="RECONCILIATION_DECISION",
            payload={
                "transaction_id": result.transaction_id,
                "payment_id": result.payment_id,
                "ledger_id": result.ledger_id,
                "settlement_id": result.settlement_id,
                "status": result.status.value,
                "method": result.method.value,
                "confidence": result.confidence,
                "amount_difference": (
                    result.amount_difference
                ),
                "candidate_count": (
                    result.candidate_count
                ),
                "reason": result.reason,
            },
        )

    def _record_exception(
        self,
        result: MatchResult,
    ) -> None:
        """
        Write unsafe or unresolved decisions to the exception
        manifest.

        Automatically reconciled records are never written
        as exceptions.
        """

        if result.status == MatchStatus.MATCHED:
            return

        if result.status == MatchStatus.FUZZY_MATCHED:
            return

        self.exception_manifest.record(
            transaction_id=result.transaction_id,
            status=result.status.value,
            reason=result.reason,
            confidence=result.confidence,
            evidence={
                "payment_id": result.payment_id,
                "ledger_id": result.ledger_id,
                "settlement_id": result.settlement_id,
                "amount_difference": (
                    result.amount_difference
                ),
                "candidate_count": (
                    result.candidate_count
                ),
            },
        )

    def _append_result(
        self,
        results: list[MatchResult],
        result: MatchResult,
    ) -> None:
        """
        Centralize result handling.

        Every result receives identical:
            - result collection
            - immutable audit logging
            - exception-manifest handling
        """

        results.append(
            result
        )

        self._record_decision(
            result
        )

        self._record_exception(
            result
        )

    # ==================================================================
    # STRUCTURAL AMBIGUITY
    # ==================================================================

    @staticmethod
    def _transaction_ledger_entries(
        payment: Payment,
        ledger: list[LedgerEntry],
    ) -> list[LedgerEntry]:
        """
        Return every ledger row belonging to the same canonical
        transaction context as the payment.

        This catches cases where:

            payment
                -> one perfectly matching ledger

        but also:

            same transaction
                -> additional conflicting ledger row

        Example:

            txn_00180
                ledger_00180
                ledger_00180_ALT

        A perfect individual match is not enough to safely close
        the transaction when unresolved competing source evidence
        exists.
        """

        return [
            entry
            for entry in ledger
            if (
                entry.transaction_id
                == payment.transaction_id
            )
        ]

    # ==================================================================
    # RECONCILIATION
    # ==================================================================

    def reconcile(
        self,
        payments: list[Payment],
        ledger: list[LedgerEntry],
        settlements: list[Settlement],
    ) -> list[MatchResult]:

        results: list[
            MatchResult
        ] = []

        settlement_by_payment = {
            settlement.payment_id: settlement
            for settlement in settlements
        }

        matched_ledger_ids: set[
            str
        ] = set()

        # ==============================================================
        # PHASE 1
        #
        # PAYMENT -> LEDGER -> SETTLEMENT
        # ==============================================================

        for payment in payments:

            candidates = find_candidates(
                payment,
                ledger,
            )

            # ----------------------------------------------------------
            # No viable ledger candidate
            # ----------------------------------------------------------

            if not candidates:

                settlement = (
                    settlement_by_payment.get(
                        payment.payment_id
                    )
                )

                settlement_id = (
                    settlement.settlement_id
                    if settlement
                    else None
                )

                result = MatchResult(
                    transaction_id=(
                        payment.transaction_id
                    ),
                    payment_id=(
                        payment.payment_id
                    ),
                    ledger_id=None,
                    settlement_id=(
                        settlement_id
                    ),
                    status=(
                        MatchStatus.MISSING_LEDGER
                    ),
                    method=(
                        MatchMethod.NONE
                    ),
                    confidence=0.0,
                    candidate_count=0,
                    reason=(
                        "No viable ledger candidate found"
                    ),
                )

                self._append_result(
                    results,
                    result,
                )

                continue

            top = candidates[0]

            # ==========================================================
            # SCORE-BASED AMBIGUITY PROTECTION
            # ==========================================================
            #
            # If multiple candidates independently have sufficiently
            # strong scores and their scores are too close, deterministic
            # matching cannot safely choose between them.
            # ==========================================================

            strong_candidates = [
                candidate
                for candidate in candidates
                if (
                    candidate.score
                    >= FUZZY_THRESHOLD
                )
            ]

            if len(
                strong_candidates
            ) > 1:

                second = (
                    strong_candidates[1]
                )

                score_gap = (
                    top.score
                    - second.score
                )

                if (
                    score_gap
                    <= AMBIGUITY_MARGIN
                ):

                    result = MatchResult(
                        transaction_id=(
                            payment.transaction_id
                        ),
                        payment_id=(
                            payment.payment_id
                        ),
                        ledger_id=None,
                        settlement_id=None,
                        status=(
                            MatchStatus.AMBIGUOUS
                        ),
                        method=(
                            MatchMethod.NONE
                        ),
                        confidence=(
                            top.score
                        ),
                        candidate_count=len(
                            strong_candidates
                        ),
                        reason=(
                            "Multiple high-confidence "
                            "ledger candidates"
                        ),
                    )

                    self._append_result(
                        results,
                        result,
                    )

                    continue

            ledger_entry = (
                top.ledger
            )

            # ==========================================================
            # DUPLICATE LEDGER PROTECTION
            # ==========================================================
            #
            # This catches genuinely duplicate source records:
            #
            # same reference
            # same amount
            # same currency
            #
            # Multiple exact duplicates must never be silently consumed.
            # ==========================================================

            normalized_reference = (
                ledger_entry.order_ref
            )

            same_reference = [
                entry
                for entry in ledger
                if (
                    entry.order_ref
                    == normalized_reference
                    and entry.amount
                    == ledger_entry.amount
                    and entry.currency
                    == ledger_entry.currency
                )
            ]

            if len(
                same_reference
            ) > 1:

                result = MatchResult(
                    transaction_id=(
                        payment.transaction_id
                    ),
                    payment_id=(
                        payment.payment_id
                    ),
                    ledger_id=None,
                    settlement_id=None,
                    status=(
                        MatchStatus.DUPLICATE
                    ),
                    method=(
                        MatchMethod.NONE
                    ),
                    confidence=(
                        top.score
                    ),
                    candidate_count=len(
                        same_reference
                    ),
                    reason=(
                        "Multiple duplicate ledger "
                        "records detected"
                    ),
                )

                self._append_result(
                    results,
                    result,
                )

                continue

            # ==========================================================
            # AMOUNT VALIDATION
            # ==========================================================
            #
            # Important:
            # amount mismatch is evaluated BEFORE the new structural
            # ambiguity rule.
            #
            # This preserves cases such as txn_00488, txn_00527,
            # txn_00793 and txn_00809 as AMOUNT_MISMATCH instead of
            # incorrectly converting them to AMBIGUOUS.
            # ==========================================================

            if not top.amount_match:

                result = MatchResult(
                    transaction_id=(
                        payment.transaction_id
                    ),
                    payment_id=(
                        payment.payment_id
                    ),
                    ledger_id=(
                        ledger_entry.ledger_id
                    ),
                    settlement_id=None,
                    status=(
                        MatchStatus.AMOUNT_MISMATCH
                    ),
                    method=(
                        MatchMethod.FUZZY
                    ),
                    confidence=(
                        top.score
                    ),
                    amount_difference=round(
                        abs(
                            payment.amount
                            - ledger_entry.amount
                        ),
                        2,
                    ),
                    candidate_count=len(
                        candidates
                    ),
                    reason=(
                        "Payment and ledger references "
                        "are related but amounts differ"
                    ),
                )

                self._append_result(
                    results,
                    result,
                )

                continue

            # ==========================================================
            # STRUCTURAL AMBIGUITY PROTECTION
            # ==========================================================
            #
            # This is the key new protection.
            #
            # A payment may have one individually perfect ledger match,
            # but the same transaction context may contain another
            # unresolved ledger row.
            #
            # Example:
            #
            #   txn_00180
            #       ledger_00180
            #       ledger_00180_ALT
            #
            # The old engine auto-resolved ledger_00180 because the
            # individual pair was perfect.
            #
            # Finance-safe behavior:
            #
            #   exact candidate
            #   + competing transaction ledger evidence
            #   -> AMBIGUOUS
            #   -> quarantine
            #
            # We only apply this rule when the top pair itself looks
            # exact. Amount mismatch cases have already exited above.
            # ==========================================================

            is_exact_pair = (
                top.reference_score
                == 1.0
                and top.amount_match
                and top.currency_match
            )

            if is_exact_pair:

                transaction_ledger_entries = (
                    self._transaction_ledger_entries(
                        payment,
                        ledger,
                    )
                )

                distinct_transaction_ledger_ids = {
                    entry.ledger_id
                    for entry
                    in transaction_ledger_entries
                }

                if len(
                    distinct_transaction_ledger_ids
                ) > 1:

                    result = MatchResult(
                        transaction_id=(
                            payment.transaction_id
                        ),
                        payment_id=(
                            payment.payment_id
                        ),
                        ledger_id=None,
                        settlement_id=None,
                        status=(
                            MatchStatus.AMBIGUOUS
                        ),
                        method=(
                            MatchMethod.NONE
                        ),
                        confidence=(
                            top.score
                        ),
                        candidate_count=len(
                            distinct_transaction_ledger_ids
                        ),
                        reason=(
                            "Exact ledger match exists, "
                            "but additional ledger evidence "
                            "exists for the same transaction"
                        ),
                    )

                    self._append_result(
                        results,
                        result,
                    )

                    continue

            # ==========================================================
            # SETTLEMENT VALIDATION
            # ==========================================================

            settlement = (
                settlement_by_payment.get(
                    payment.payment_id
                )
            )

            if settlement is None:

                result = MatchResult(
                    transaction_id=(
                        payment.transaction_id
                    ),
                    payment_id=(
                        payment.payment_id
                    ),
                    ledger_id=(
                        ledger_entry.ledger_id
                    ),
                    settlement_id=None,
                    status=(
                        MatchStatus.UNRESOLVED
                    ),
                    method=(
                        MatchMethod.FUZZY
                    ),
                    confidence=(
                        top.score
                    ),
                    candidate_count=len(
                        candidates
                    ),
                    reason=(
                        "Settlement record not found"
                    ),
                )

                self._append_result(
                    results,
                    result,
                )

                continue

            (
                settlement_valid,
                settlement_reason,
            ) = validate_settlement(
                settlement
            )

            settlement_amount_difference = abs(
                settlement.gross_amount
                - payment.amount
            )

            if (
                not settlement_valid
                or settlement_amount_difference
                > 0.01
            ):

                result = MatchResult(
                    transaction_id=(
                        payment.transaction_id
                    ),
                    payment_id=(
                        payment.payment_id
                    ),
                    ledger_id=(
                        ledger_entry.ledger_id
                    ),
                    settlement_id=(
                        settlement.settlement_id
                    ),
                    status=(
                        MatchStatus.SETTLEMENT_MISMATCH
                    ),
                    method=(
                        MatchMethod.FUZZY
                    ),
                    confidence=(
                        top.score
                    ),
                    amount_difference=round(
                        settlement_amount_difference,
                        2,
                    ),
                    candidate_count=len(
                        candidates
                    ),
                    reason=(
                        settlement_reason
                    ),
                )

                self._append_result(
                    results,
                    result,
                )

                continue

            # ==========================================================
            # FINAL SAFE MATCH
            # ==========================================================

            method = (
                MatchMethod.EXACT
                if is_exact_pair
                else MatchMethod.FUZZY
            )

            status = (
                MatchStatus.MATCHED
                if (
                    method
                    == MatchMethod.EXACT
                )
                else MatchStatus.FUZZY_MATCHED
            )

            # Only safely resolved ledger records are consumed.
            matched_ledger_ids.add(
                ledger_entry.ledger_id
            )

            result = MatchResult(
                transaction_id=(
                    payment.transaction_id
                ),
                payment_id=(
                    payment.payment_id
                ),
                ledger_id=(
                    ledger_entry.ledger_id
                ),
                settlement_id=(
                    settlement.settlement_id
                ),
                status=(
                    status
                ),
                method=(
                    method
                ),
                confidence=(
                    top.score
                ),
                amount_difference=0.0,
                candidate_count=len(
                    candidates
                ),
                reason=(
                    "Payment, ledger and settlement "
                    "evidence consistent"
                ),
            )

            self._append_result(
                results,
                result,
            )

        # ==============================================================
        # PHASE 2
        #
        # LEDGER RECORDS WITHOUT PAYMENTS
        # ==============================================================

        for ledger_entry in ledger:

            # Already safely consumed by an automatic reconciliation.
            if (
                ledger_entry.ledger_id
                in matched_ledger_ids
            ):
                continue

            # Determine whether this ledger row still has a direct
            # payment reference.
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

            if (
                possible_payment
                is not None
            ):
                continue

            result = MatchResult(
                transaction_id=(
                    ledger_entry.transaction_id
                ),
                payment_id=None,
                ledger_id=(
                    ledger_entry.ledger_id
                ),
                settlement_id=None,
                status=(
                    MatchStatus.MISSING_PAYMENT
                ),
                method=(
                    MatchMethod.NONE
                ),
                confidence=0.0,
                candidate_count=0,
                reason=(
                    "Ledger entry has no corresponding "
                    "payment record"
                ),
            )

            self._append_result(
                results,
                result,
            )

        return results