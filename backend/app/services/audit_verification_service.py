from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from backend.app.agent.agent import (
    FinanceAgent,
)


@dataclass(frozen=True)
class AuditVerificationResult:
    success: bool
    verified: bool

    tool_name: str

    evidence: dict[str, Any] | None

    error: str | None

    financial_state_mutated: bool = False


class AuditVerificationService:
    """
    Application-facing immutable audit verification service.

    Verification is delegated to the canonical registered
    ReconAI audit tool.

    This service:
        - does not modify the audit log
        - does not invoke an LLM
        - does not infer verification from file presence
    """

    def __init__(
        self,
        agent: FinanceAgent | None = None,
    ) -> None:
        self._agent = (
            agent
            if agent is not None
            else FinanceAgent()
        )

    @staticmethod
    def _serialize_payload(
        value: Any,
    ) -> Any:
        if hasattr(
            value,
            "__dataclass_fields__",
        ):
            return asdict(
                value
            )

        return value

    @staticmethod
    def _extract_verified(
        payload: dict[str, Any],
    ) -> bool:
        """
        Support common verifier result shapes without fabricating
        success.

        Explicit verification fields are authoritative.
        """

        for key in (
            "verified",
            "valid",
            "is_valid",
            "chain_valid",
            "integrity_passed",
        ):
            value = payload.get(
                key
            )

            if isinstance(
                value,
                bool,
            ):
                return value

        success = payload.get(
            "success"
        )

        if isinstance(
            success,
            bool,
        ):
            return success

        return False

    def verify(
        self,
    ) -> AuditVerificationResult:
        execution = (
            self._agent.execute_tool(
                "verify_audit_chain"
            )
        )

        if not execution.success:
            return AuditVerificationResult(
                success=False,
                verified=False,
                tool_name=execution.tool_name,
                evidence=None,
                error=execution.error,
            )

        payload = (
            self._serialize_payload(
                execution.result
            )
        )

        if isinstance(
            payload,
            dict,
        ):
            evidence = payload
        else:
            evidence = {
                "result": payload,
            }

        verified = (
            self._extract_verified(
                evidence
            )
        )

        return AuditVerificationResult(
            success=True,
            verified=verified,
            tool_name=execution.tool_name,
            evidence=evidence,
            error=None,
        )