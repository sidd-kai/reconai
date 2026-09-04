from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any, Literal

from backend.app.agent.agent import (
    FinanceAgent,
    ToolExecutionResult,
)
from backend.app.agent.provider import (
    LLMProviderError,
)
from backend.app.agent.provider_factory import (
    configured_provider_name,
    create_llm_provider,
)
from backend.app.agent.runtime import (
    FinanceAgentRuntime,
    SYSTEM_PROMPT,
)


AgentAction = Literal[
    "batch_summary",
    "finance_ops_summary",
    "high_value_exceptions",
    "verify_audit_chain",
    "exception_manifest",
    "investigate_exception",
]


@dataclass(frozen=True)
class AgentQueryResult:
    success: bool
    answer: str
    transaction_id: str | None
    tools_used: tuple[str, ...]
    deterministic_evidence: Any
    ai_explanation_used: bool
    provider_status: str
    financial_state_mutated: bool = False


class AgentService:
    """
    Application-facing ReconAI finance-controller service.

    Financial truth always comes from deterministic registered tools.
    The AI provider is used only for language understanding,
    tool selection, and explanation.
    """

    ACTION_TO_TOOL: dict[
        AgentAction,
        str,
    ] = {
        "batch_summary": "get_batch_summary",
        "finance_ops_summary": "get_finance_ops_summary",
        "high_value_exceptions": "get_high_value_exceptions",
        "verify_audit_chain": "verify_audit_chain",
        "exception_manifest": "get_exception_manifest",
        "investigate_exception": "investigate_exception",
    }

    def __init__(
        self,
        agent: FinanceAgent | None = None,
    ) -> None:
        self._agent = (
            agent
            if agent is not None
            else FinanceAgent()
        )

    # ---------------------------------------------------------
    # SERIALIZATION
    # ---------------------------------------------------------

    @staticmethod
    def _serialize_payload(
        value: Any,
    ) -> Any:
        if hasattr(
            value,
            "__dataclass_fields__",
        ):
            return AgentService._serialize_payload(
                asdict(value)
            )

        if isinstance(
            value,
            tuple,
        ):
            return [
                AgentService._serialize_payload(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            list,
        ):
            return [
                AgentService._serialize_payload(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): (
                    AgentService._serialize_payload(
                        nested
                    )
                )
                for key, nested in value.items()
            }

        return value

    # ---------------------------------------------------------
    # SAFE FORMATTERS
    # ---------------------------------------------------------

    @staticmethod
    def _number(
        value: Any,
        *,
        default: float = 0.0,
    ) -> float:
        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def _integer(
        value: Any,
        *,
        default: int = 0,
    ) -> int:
        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return default

    @staticmethod
    def _percent(
        value: Any,
    ) -> str:
        numeric = AgentService._number(
            value
        )

        if abs(numeric) <= 1.0:
            numeric *= 100.0

        return f"{numeric:.2f}%"

    @staticmethod
    def _money(
        value: Any,
    ) -> str:
        numeric = AgentService._number(
            value
        )

        return f"₹{abs(numeric):,.2f}"

    # ---------------------------------------------------------
    # TOOL EXECUTION
    # ---------------------------------------------------------

    def _execute_tool(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolExecutionResult:
        return self._agent.execute_tool(
            tool_name,
            **(
                arguments
                or {}
            ),
        )

    # ---------------------------------------------------------
    # TRANSACTION SUMMARY
    # ---------------------------------------------------------

    @staticmethod
    def _transaction_answer(
        *,
        transaction_id: str,
        evidence: dict[str, Any],
    ) -> str:
        status = str(
            evidence.get(
                "status",
                "UNKNOWN",
            )
        )

        reason = str(
            evidence.get(
                "reason",
                "No deterministic reason recorded.",
            )
        )

        confidence = (
            AgentService._percent(
                evidence.get(
                    "confidence",
                    0.0,
                )
            )
        )

        difference = (
            AgentService._money(
                evidence.get(
                    "amount_difference",
                    0.0,
                )
            )
        )

        payment_id = evidence.get(
            "payment_id"
        )

        ledger_id = evidence.get(
            "ledger_id"
        )

        settlement_id = evidence.get(
            "settlement_id"
        )

        candidate_count = evidence.get(
            "candidate_count",
            0,
        )

        return (
            f"Transaction {transaction_id}\n\n"
            f"Status: {status}\n"
            f"Confidence: {confidence}\n"
            f"Amount difference: {difference}\n\n"
            f"Reason:\n{reason}\n\n"
            "Source evidence:\n"
            f"- Payment: {payment_id or 'not available'}\n"
            f"- Ledger: {ledger_id or 'not available'}\n"
            f"- Settlement: {settlement_id or 'not available'}\n"
            f"- Candidate count: {candidate_count}\n\n"
            "Finance action:\n"
            "Review the source evidence before making any "
            "manual adjustment. ReconAI has not automatically "
            "resolved or modified this transaction."
        )

    # ---------------------------------------------------------
    # BATCH SUMMARY
    # ---------------------------------------------------------

    @classmethod
    def _batch_summary_answer(
        cls,
        evidence: dict[str, Any],
    ) -> str:
        records = cls._integer(
            evidence.get(
                "records_processed",
                evidence.get(
                    "canonical_transactions",
                    0,
                ),
            )
        )

        matched = cls._integer(
            evidence.get(
                "matched",
                evidence.get(
                    "resolved",
                    0,
                ),
            )
        )

        exceptions = cls._integer(
            evidence.get(
                "exceptions",
                0,
            )
        )

        match_rate = cls._percent(
            evidence.get(
                "match_rate",
                0.0,
            )
        )

        exception_rate = cls._percent(
            evidence.get(
                "exception_rate",
                0.0,
            )
        )

        audit_verified = bool(
            evidence.get(
                "audit_chain_verified",
                evidence.get(
                    "audit_verified",
                    False,
                ),
            )
        )

        raw_rows = cls._integer(
            evidence.get(
                "raw_result_rows",
                0,
            )
        )

        supplemental = cls._integer(
            evidence.get(
                "supplemental_source_events",
                0,
            )
        )

        breakdown = evidence.get(
            "exception_breakdown",
            [],
        )

        breakdown_lines: list[str] = []

        if isinstance(
            breakdown,
            list,
        ):
            for item in breakdown:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                status = str(
                    item.get(
                        "status",
                        "UNKNOWN",
                    )
                )

                count = cls._integer(
                    item.get(
                        "count",
                        0,
                    )
                )

                breakdown_lines.append(
                    f"- {status}: {count}"
                )

        breakdown_text = (
            "\n".join(
                breakdown_lines
            )
            if breakdown_lines
            else "- No exception breakdown available"
        )

        return (
            "Batch Summary\n\n"
            f"Canonical transactions: {records:,}\n"
            f"Automatically reconciled: {matched:,}\n"
            f"Exceptions: {exceptions:,}\n"
            f"Match rate: {match_rate}\n"
            f"Exception rate: {exception_rate}\n"
            f"Audit chain verified: "
            f"{'YES' if audit_verified else 'NO'}\n"
            f"Raw result rows: {raw_rows:,}\n"
            f"Supplemental source events: {supplemental:,}\n\n"
            "Exception breakdown:\n"
            f"{breakdown_text}\n\n"
            "No financial state was modified."
        )

    # ---------------------------------------------------------
    # FINANCE OPS SUMMARY
    # ---------------------------------------------------------

    @classmethod
    def _finance_ops_answer(
        cls,
        evidence: dict[str, Any],
    ) -> str:
        records = cls._integer(
            evidence.get(
                "records_processed",
                0,
            )
        )

        matched = cls._integer(
            evidence.get(
                "matched",
                0,
            )
        )

        exceptions = cls._integer(
            evidence.get(
                "exceptions",
                0,
            )
        )

        match_rate = cls._percent(
            evidence.get(
                "match_rate",
                0.0,
            )
        )

        exception_rate = cls._percent(
            evidence.get(
                "exception_rate",
                0.0,
            )
        )

        highest_impact = cls._money(
            evidence.get(
                "highest_financial_impact",
                0.0,
            )
        )

        audit_verified = bool(
            evidence.get(
                "audit_verified",
                evidence.get(
                    "audit_chain_verified",
                    False,
                ),
            )
        )

        top_exceptions = evidence.get(
            "top_exceptions",
            [],
        )

        top_lines: list[str] = []

        if isinstance(
            top_exceptions,
            list,
        ):
            for index, item in enumerate(
                top_exceptions[:5],
                start=1,
            ):
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                transaction_id = str(
                    item.get(
                        "transaction_id",
                        "unknown",
                    )
                )

                status = str(
                    item.get(
                        "status",
                        "UNKNOWN",
                    )
                )

                difference = cls._money(
                    item.get(
                        "amount_difference",
                        0.0,
                    )
                )

                top_lines.append(
                    f"{index}. {transaction_id} — "
                    f"{difference} — {status}"
                )

        top_text = (
            "\n".join(
                top_lines
            )
            if top_lines
            else "No high-value exceptions available."
        )

        return (
            "Finance Operations Attention\n\n"
            f"Transactions reviewed: {records:,}\n"
            f"Automatically reconciled: {matched:,}\n"
            f"Exceptions requiring attention: {exceptions:,}\n"
            f"Match rate: {match_rate}\n"
            f"Exception rate: {exception_rate}\n"
            f"Highest financial discrepancy: {highest_impact}\n"
            f"Audit chain verified: "
            f"{'YES' if audit_verified else 'NO'}\n\n"
            "Highest-value exceptions:\n"
            f"{top_text}\n\n"
            "Finance operations should prioritize the largest "
            "unresolved discrepancies while preserving the "
            "deterministic exception classifications."
        )

    # ---------------------------------------------------------
    # HIGH-VALUE EXCEPTIONS
    # ---------------------------------------------------------

    @classmethod
    def _high_value_answer(
        cls,
        evidence: Any,
    ) -> str:
        if isinstance(
            evidence,
            dict,
        ):
            items = evidence.get(
                "items",
                evidence.get(
                    "exceptions",
                    [],
                ),
            )
        else:
            items = evidence

        if not isinstance(
            items,
            list,
        ):
            items = []

        lines: list[str] = []

        for index, item in enumerate(
            items[:10],
            start=1,
        ):
            if not isinstance(
                item,
                dict,
            ):
                continue

            transaction_id = str(
                item.get(
                    "transaction_id",
                    "unknown",
                )
            )

            status = str(
                item.get(
                    "status",
                    "UNKNOWN",
                )
            )

            difference = cls._money(
                item.get(
                    "amount_difference",
                    0.0,
                )
            )

            confidence = cls._percent(
                item.get(
                    "confidence",
                    0.0,
                )
            )

            lines.append(
                f"{index}. {transaction_id}\n"
                f"   {status} · {difference} · "
                f"{confidence} confidence"
            )

        if not lines:
            return (
                "High-Value Exceptions\n\n"
                "No unresolved high-value exceptions were returned "
                "by the deterministic tool."
            )

        return (
            "High-Value Exceptions\n\n"
            f"{chr(10).join(lines)}\n\n"
            "These transactions remain exceptions. "
            "No automatic financial resolution was performed."
        )

    # ---------------------------------------------------------
    # AUDIT SUMMARY
    # ---------------------------------------------------------

    @classmethod
    def _audit_answer(
        cls,
        evidence: dict[str, Any],
    ) -> str:
        verified = bool(
            evidence.get(
                "verified",
                evidence.get(
                    "valid",
                    False,
                ),
            )
        )

        records = cls._integer(
            evidence.get(
                "records_verified",
                0,
            )
        )

        error = evidence.get(
            "error"
        )

        if verified:
            return (
                "Audit Verification\n\n"
                "Status: VERIFIED\n"
                f"Records verified: {records:,}\n"
                "Hash-chain integrity: PASS\n\n"
                "The canonical deterministic audit verifier "
                "found no integrity break."
            )

        return (
            "Audit Verification\n\n"
            "Status: FAILED\n"
            f"Records checked: {records:,}\n"
            f"Error: {error or 'verification did not pass'}\n\n"
            "Finance operations should treat the audit chain "
            "as unverified until the integrity issue is resolved."
        )

    # ---------------------------------------------------------
    # EXCEPTION MANIFEST
    # ---------------------------------------------------------

    @classmethod
    def _manifest_answer(
        cls,
        evidence: Any,
    ) -> str:
        if isinstance(
            evidence,
            dict,
        ):
            items = evidence.get(
                "items",
                evidence.get(
                    "exceptions",
                    [],
                ),
            )
        else:
            items = evidence

        if not isinstance(
            items,
            list,
        ):
            items = []

        counts: Counter[str] = Counter()

        for item in items:
            if not isinstance(
                item,
                dict,
            ):
                continue

            status = str(
                item.get(
                    "status",
                    "UNKNOWN",
                )
            )

            counts[
                status
            ] += 1

        breakdown = "\n".join(
            f"- {status}: {count}"
            for status, count
            in sorted(
                counts.items()
            )
        )

        return (
            "Exception Manifest\n\n"
            f"Current exceptions: {len(items):,}\n\n"
            "Status breakdown:\n"
            f"{breakdown or '- No exception rows returned'}\n\n"
            "Historical duplicate exception events are reduced "
            "to their latest deterministic transaction state."
        )

    # ---------------------------------------------------------
    # ACTION ANSWER DISPATCH
    # ---------------------------------------------------------

    @classmethod
    def _format_action_answer(
        cls,
        *,
        action: AgentAction,
        evidence: Any,
        transaction_id: str | None,
    ) -> str:
        if (
            action == "batch_summary"
            and isinstance(
                evidence,
                dict,
            )
        ):
            return cls._batch_summary_answer(
                evidence
            )

        if (
            action == "finance_ops_summary"
            and isinstance(
                evidence,
                dict,
            )
        ):
            return cls._finance_ops_answer(
                evidence
            )

        if action == "high_value_exceptions":
            return cls._high_value_answer(
                evidence
            )

        if (
            action == "verify_audit_chain"
            and isinstance(
                evidence,
                dict,
            )
        ):
            return cls._audit_answer(
                evidence
            )

        if action == "exception_manifest":
            return cls._manifest_answer(
                evidence
            )

        if (
            action == "investigate_exception"
            and transaction_id
            and isinstance(
                evidence,
                dict,
            )
        ):
            return cls._transaction_answer(
                transaction_id=transaction_id,
                evidence=evidence,
            )

        return (
            "Deterministic finance evidence is available below.\n\n"
            "No financial state was modified."
        )

    # ---------------------------------------------------------
    # TRANSACTION AI EXPLANATION
    # ---------------------------------------------------------

    @staticmethod
    def _build_explanation_messages(
        *,
        message: str,
        transaction_id: str,
        evidence: dict[str, Any],
    ) -> list[dict[str, Any]]:
        evidence_json = json.dumps(
            evidence,
            indent=2,
            default=str,
        )

        return [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    "The deterministic ReconAI investigation "
                    "tool has already been executed.\n\n"
                    "Treat the following evidence as authoritative. "
                    "Do not alter financial facts or claim the "
                    "exception is resolved.\n\n"
                    f"Transaction ID:\n{transaction_id}\n\n"
                    "Deterministic evidence:\n"
                    f"{evidence_json}\n\n"
                    f"User request:\n{message}\n\n"
                    "Explain what happened and what finance "
                    "operations should review next."
                ),
            },
        ]

    def _try_transaction_ai_explanation(
        self,
        *,
        message: str,
        transaction_id: str,
        evidence: dict[str, Any],
    ) -> tuple[
        str | None,
        str,
    ]:
        if configured_provider_name() is None:
            return (
                None,
                "NOT_CONFIGURED",
            )

        try:
            provider = create_llm_provider()

            response = provider.generate(
                messages=(
                    self._build_explanation_messages(
                        message=message,
                        transaction_id=transaction_id,
                        evidence=evidence,
                    )
                ),
                tools=[],
            )

        except LLMProviderError as exc:
            return (
                None,
                f"UNAVAILABLE:{exc.code}",
            )

        except Exception as exc:
            return (
                None,
                f"UNAVAILABLE:{type(exc).__name__}",
            )

        content = (
            response.content
            or ""
        ).strip()

        if not content:
            return (
                None,
                "EMPTY_RESPONSE",
            )

        return (
            content,
            "AVAILABLE",
        )

    def ask_about_transaction(
        self,
        *,
        transaction_id: str,
        message: str,
    ) -> AgentQueryResult:
        transaction_id = (
            transaction_id.strip()
        )

        message = (
            message.strip()
        )

        if not transaction_id:
            raise ValueError(
                "transaction_id cannot be empty."
            )

        if not message:
            raise ValueError(
                "message cannot be empty."
            )

        execution = self._execute_tool(
            tool_name="investigate_exception",
            arguments={
                "transaction_id": transaction_id,
            },
        )

        if not execution.success:
            return AgentQueryResult(
                success=False,
                answer=(
                    "ReconAI could not retrieve deterministic "
                    f"evidence for {transaction_id}. "
                    f"{execution.error}"
                ),
                transaction_id=transaction_id,
                tools_used=(
                    execution.tool_name,
                ),
                deterministic_evidence=None,
                ai_explanation_used=False,
                provider_status="NOT_ATTEMPTED",
            )

        serialized = (
            self._serialize_payload(
                execution.result
            )
        )

        if not isinstance(
            serialized,
            dict,
        ):
            serialized = {
                "result": serialized,
            }

        (
            ai_answer,
            provider_status,
        ) = (
            self._try_transaction_ai_explanation(
                message=message,
                transaction_id=transaction_id,
                evidence=serialized,
            )
        )

        if ai_answer is None:
            answer = (
                self._transaction_answer(
                    transaction_id=transaction_id,
                    evidence=serialized,
                )
            )

            ai_used = False

        else:
            answer = ai_answer
            ai_used = True

        return AgentQueryResult(
            success=True,
            answer=answer,
            transaction_id=transaction_id,
            tools_used=(
                execution.tool_name,
            ),
            deterministic_evidence=serialized,
            ai_explanation_used=ai_used,
            provider_status=provider_status,
        )

    # ---------------------------------------------------------
    # DETERMINISTIC QUICK ACTIONS
    # ---------------------------------------------------------

    def run_action(
        self,
        *,
        action: AgentAction,
        transaction_id: str | None = None,
        limit: int = 5,
    ) -> AgentQueryResult:
        try:
            tool_name = (
                self.ACTION_TO_TOOL[
                    action
                ]
            )

        except KeyError as exc:
            raise ValueError(
                f"Unsupported agent action: {action}"
            ) from exc

        arguments: dict[
            str,
            Any,
        ] = {}

        if action == "investigate_exception":
            if not transaction_id:
                raise ValueError(
                    "transaction_id is required for "
                    "investigate_exception."
                )

            transaction_id = (
                transaction_id.strip()
            )

            arguments[
                "transaction_id"
            ] = transaction_id

        elif action in {
            "high_value_exceptions",
            "finance_ops_summary",
        }:
            arguments[
                "limit"
            ] = limit

        execution = self._execute_tool(
            tool_name=tool_name,
            arguments=arguments,
        )

        if not execution.success:
            return AgentQueryResult(
                success=False,
                answer=(
                    "The deterministic finance tool "
                    "could not complete successfully.\n\n"
                    f"Tool: {execution.tool_name}\n"
                    f"Error: {execution.error}"
                ),
                transaction_id=transaction_id,
                tools_used=(
                    execution.tool_name,
                ),
                deterministic_evidence=None,
                ai_explanation_used=False,
                provider_status="DETERMINISTIC_DIRECT",
            )

        evidence = (
            self._serialize_payload(
                execution.result
            )
        )

        answer = (
            self._format_action_answer(
                action=action,
                evidence=evidence,
                transaction_id=transaction_id,
            )
        )

        return AgentQueryResult(
            success=True,
            answer=answer,
            transaction_id=transaction_id,
            tools_used=(
                execution.tool_name,
            ),
            deterministic_evidence=evidence,
            ai_explanation_used=False,
            provider_status="DETERMINISTIC_DIRECT",
        )

    # ---------------------------------------------------------
    # FREE-FORM AGENT
    # ---------------------------------------------------------

    def run_free_form(
        self,
        *,
        message: str,
    ) -> AgentQueryResult:
        message = (
            message.strip()
        )

        if not message:
            raise ValueError(
                "message cannot be empty."
            )

        if configured_provider_name() is None:
            return AgentQueryResult(
                success=False,
                answer=(
                    "Free-form AI reasoning is currently unavailable "
                    "because no LLM provider is configured.\n\n"
                    "The deterministic quick actions above remain "
                    "fully operational."
                ),
                transaction_id=None,
                tools_used=(),
                deterministic_evidence=None,
                ai_explanation_used=False,
                provider_status="NOT_CONFIGURED",
            )

        try:
            runtime = FinanceAgentRuntime(
                provider=create_llm_provider(),
                agent=self._agent,
                max_tool_rounds=2,
                generate_final_answer=True,
            )

            result = runtime.run(
                message
            )

        except Exception as exc:
            return AgentQueryResult(
                success=False,
                answer=(
                    "Free-form AI reasoning is temporarily unavailable.\n\n"
                    "No financial conclusion was generated. "
                    "Deterministic quick actions remain operational."
                ),
                transaction_id=None,
                tools_used=(),
                deterministic_evidence=None,
                ai_explanation_used=False,
                provider_status=(
                    "UNAVAILABLE:"
                    f"{type(exc).__name__}"
                ),
            )

        tools_used = tuple(
            execution.tool_name
            for execution
            in result.tool_executions
        )

        evidence = [
            {
                "success": execution.success,
                "tool_name": execution.tool_name,
                "result": (
                    self._serialize_payload(
                        execution.result
                    )
                    if execution.success
                    else None
                ),
                "error": execution.error,
            }
            for execution
            in result.tool_executions
        ]

        content = (
            result.content
            or ""
        ).strip()

        provider_failed = (
            content.startswith(
                "AI reasoning is temporarily unavailable."
            )
        )

        # -----------------------------------------------------
        # Provider failed after deterministic tool execution.
        # Preserve finance evidence and return a safe fallback.
        # -----------------------------------------------------

        if (
            provider_failed
            and result.tool_executions
        ):
            successful_execution = next(
                (
                    execution
                    for execution
                    in reversed(
                        result.tool_executions
                    )
                    if execution.success
                ),
                None,
            )

            if successful_execution is not None:
                serialized = (
                    self._serialize_payload(
                        successful_execution.result
                    )
                )

                tool_name = (
                    successful_execution.tool_name
                )

                if (
                    tool_name
                    == "get_batch_summary"
                    and isinstance(
                        serialized,
                        dict,
                    )
                ):
                    fallback_answer = (
                        self._batch_summary_answer(
                            serialized
                        )
                    )

                elif (
                    tool_name
                    == "get_finance_ops_summary"
                    and isinstance(
                        serialized,
                        dict,
                    )
                ):
                    fallback_answer = (
                        self._finance_ops_answer(
                            serialized
                        )
                    )

                elif (
                    tool_name
                    == "get_high_value_exceptions"
                ):
                    fallback_answer = (
                        self._high_value_answer(
                            serialized
                        )
                    )

                elif (
                    tool_name
                    == "verify_audit_chain"
                    and isinstance(
                        serialized,
                        dict,
                    )
                ):
                    fallback_answer = (
                        self._audit_answer(
                            serialized
                        )
                    )

                elif (
                    tool_name
                    == "get_exception_manifest"
                ):
                    fallback_answer = (
                        self._manifest_answer(
                            serialized
                        )
                    )

                elif (
                    tool_name
                    == "investigate_exception"
                    and isinstance(
                        serialized,
                        dict,
                    )
                ):
                    transaction_id = str(
                        serialized.get(
                            "transaction_id",
                            "unknown",
                        )
                    )

                    fallback_answer = (
                        self._transaction_answer(
                            transaction_id=transaction_id,
                            evidence=serialized,
                        )
                    )

                else:
                    fallback_answer = (
                        "The AI explanation provider became unavailable, "
                        "but the deterministic finance tool completed "
                        "successfully.\n\n"
                        "Authoritative evidence remains available below."
                    )

                return AgentQueryResult(
                    success=True,
                    answer=fallback_answer,
                    transaction_id=None,
                    tools_used=tools_used,
                    deterministic_evidence=evidence,
                    ai_explanation_used=False,
                    provider_status=(
                        "DEGRADED:"
                        "DETERMINISTIC_FALLBACK"
                    ),
                )

        # -----------------------------------------------------
        # Provider failed before any deterministic tool ran.
        # -----------------------------------------------------

        if provider_failed:
            return AgentQueryResult(
                success=False,
                answer=content,
                transaction_id=None,
                tools_used=tools_used,
                deterministic_evidence=(
                    evidence
                    if evidence
                    else None
                ),
                ai_explanation_used=False,
                provider_status=(
                    "UNAVAILABLE:"
                    "GEMINI_PROVIDER_ERROR"
                ),
            )

        # -----------------------------------------------------
        # Successful AI + tool flow.
        # -----------------------------------------------------

        if tools_used:
            return AgentQueryResult(
                success=True,
                answer=(
                    content
                    or (
                        "ReconAI completed the deterministic "
                        "finance investigation."
                    )
                ),
                transaction_id=None,
                tools_used=tools_used,
                deterministic_evidence=(
                    evidence
                    if evidence
                    else None
                ),
                ai_explanation_used=True,
                provider_status="AVAILABLE",
            )

        # -----------------------------------------------------
        # AI answered without requiring finance evidence.
        # This is allowed only for non-financial/general text.
        # -----------------------------------------------------

        return AgentQueryResult(
            success=True,
            answer=(
                content
                or "ReconAI returned no explanation."
            ),
            transaction_id=None,
            tools_used=(),
            deterministic_evidence=None,
            ai_explanation_used=True,
            provider_status="AVAILABLE",
        )
