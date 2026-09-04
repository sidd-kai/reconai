from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from pydantic import BaseModel

from backend.app.services.audit_verification_service import (
    AuditVerificationService,
)


router = APIRouter(
    prefix="/api/audit",
    tags=["audit"],
)


class AuditVerificationResponse(
    BaseModel
):
    success: bool
    verified: bool

    tool_name: str

    evidence: (
        dict[str, Any]
        | None
    )

    error: (
        str
        | None
    )

    financial_state_mutated: bool


@router.post(
    "/verify",
    response_model=AuditVerificationResponse,
)
def verify_audit_chain() -> AuditVerificationResponse:
    try:
        result = (
            AuditVerificationService()
            .verify()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Audit verification failed safely. "
                "No audit or financial records were modified. "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    return AuditVerificationResponse(
        **asdict(
            result
        )
    )