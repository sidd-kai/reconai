from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RoutedIntent:
    """
    Deterministic interpretation of an unambiguous finance query.

    None of the routing logic produces financial facts. It only
    identifies which already-approved deterministic tool should run.
    """

    tool_name: str
    arguments: dict[str, Any]


class FinanceIntentRouter:
    """
    Deterministic router for high-confidence finance-controller intents.

    The router intentionally handles only obvious requests.

    Ambiguous questions return None and are delegated to the LLM.
    """

    _TRANSACTION_PATTERN = re.compile(
        r"\btxn_[a-zA-Z0-9_-]+\b",
        re.IGNORECASE,
    )

    def route(
        self,
        question: str,
    ) -> RoutedIntent | None:
        """
        Return a deterministic intent when the question is unambiguous.

        Returns None when LLM reasoning may be useful.
        """

        normalized = " ".join(
            question.lower().strip().split()
        )

        if not normalized:
            return None

        # ---------------------------------------------------------
        # Audit verification
        # ---------------------------------------------------------
        if (
            "audit chain" in normalized
            and any(
                phrase in normalized
                for phrase in (
                    "verify",
                    "valid",
                    "validity",
                    "check",
                    "verified",
                )
            )
        ):
            return RoutedIntent(
                tool_name="verify_audit_chain",
                arguments={},
            )

        # ---------------------------------------------------------
        # Exception investigation
        # ---------------------------------------------------------
        transaction_match = self._TRANSACTION_PATTERN.search(
            normalized
        )

        if transaction_match and any(
            phrase in normalized
            for phrase in (
                "investigate",
                "what happened",
                "explain",
                "why",
            )
        ):
            return RoutedIntent(
                tool_name="investigate_exception",
                arguments={
                    "transaction_id": transaction_match.group(0)
                },
            )

        # ---------------------------------------------------------
        # High-value exceptions
        # ---------------------------------------------------------
        if (
            (
                "highest-value" in normalized
                or "highest value" in normalized
                or "largest exception" in normalized
                or "largest exceptions" in normalized
                or "biggest exception" in normalized
                or "biggest exceptions" in normalized
            )
        ):
            limit = self._extract_limit(
                normalized,
                default=3,
            )

            return RoutedIntent(
                tool_name="get_high_value_exceptions",
                arguments={
                    "limit": limit,
                },
            )

        # ---------------------------------------------------------
        # Batch summary
        # ---------------------------------------------------------
        if (
            "match rate" in normalized
            or "exception rate" in normalized
            or "how many exceptions" in normalized
            or "batch summary" in normalized
            or (
                "current reconciliation" in normalized
                and "exceptions" in normalized
            )
        ):
            return RoutedIntent(
                tool_name="get_batch_summary",
                arguments={},
            )

        return None

    @staticmethod
    def _extract_limit(
        question: str,
        default: int,
    ) -> int:
        """
        Extract a small requested result count.

        The router deliberately caps this value to avoid accidental
        large tool responses.
        """

        match = re.search(
            r"\b(\d{1,3})\b",
            question,
        )

        if match is None:
            return default

        value = int(match.group(1))

        return max(
            1,
            min(value, 100),
        )