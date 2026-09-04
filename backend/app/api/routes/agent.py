from __future__ import annotations

from dataclasses import asdict
from typing import Any, Literal

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from pydantic import (
    BaseModel,
    Field,
)

from backend.app.services.agent_service import (
    AgentService,
)


router = APIRouter(
    prefix="/api/agent",
    tags=["agent"],
)


AgentAction = Literal[
    "batch_summary",
    "finance_ops_summary",
    "high_value_exceptions",
    "verify_audit_chain",
    "exception_manifest",
    "investigate_exception",
]


class AgentQueryRequest(
    BaseModel
):
    message: str = Field(
        default="",
        max_length=4000,
    )

    transaction_id: (
        str
        | None
    ) = Field(
        default=None,
        max_length=200,
    )

    action: (
        AgentAction
        | None
    ) = None

    limit: int = Field(
        default=5,
        ge=1,
        le=100,
    )


class AgentQueryResponse(
    BaseModel
):
    success: bool

    answer: str

    transaction_id: (
        str
        | None
    )

    tools_used: list[str]

    deterministic_evidence: Any

    ai_explanation_used: bool

    provider_status: str

    financial_state_mutated: bool


@router.post(
    "/query",
    response_model=AgentQueryResponse,
)
def query_agent(
    request: AgentQueryRequest,
) -> AgentQueryResponse:
    service = AgentService()

    try:
        if (
            request.transaction_id
            and request.message.strip()
            and request.action is None
        ):
            result = (
                service.ask_about_transaction(
                    transaction_id=(
                        request.transaction_id
                    ),
                    message=(
                        request.message
                    ),
                )
            )

        elif request.action is not None:
            result = service.run_action(
                action=request.action,
                transaction_id=(
                    request.transaction_id
                ),
                limit=request.limit,
            )

        else:
            result = service.run_free_form(
                message=request.message,
            )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(
                exc
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "ReconAI agent request failed safely. "
                "No financial state was changed. "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    payload = asdict(
        result
    )

    payload[
        "tools_used"
    ] = list(
        result.tools_used
    )

    return AgentQueryResponse(
        **payload
    )