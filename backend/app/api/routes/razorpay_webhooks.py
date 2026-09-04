from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError

from backend.app.integrations.razorpay.adapter import (
    RazorpayAdapterError,
    razorpay_payment_to_reconai,
    select_reconcilable_payments,
)
from backend.app.integrations.razorpay.normalizer import (
    normalize_payment,
)
from backend.app.integrations.razorpay.webhooks import (
    RazorpayWebhookSignatureError,
    WebhookEventStore,
    process_webhook,
)
from backend.app.services.reconciliation_service import (
    ReconciliationService,
)


router = APIRouter(
    prefix="/webhooks/razorpay",
    tags=["razorpay"],
)


DEFAULT_EVENT_STORE_PATH = Path(
    "data/results/razorpay_webhook_events.jsonl"
)

DEFAULT_PAYMENT_STORE_PATH = Path(
    "data/results/razorpay_webhook_payments.jsonl"
)

DEFAULT_RECON_AUDIT_PATH = Path(
    "data/results/razorpay_webhook_reconciliation_audit.jsonl"
)

DEFAULT_RECON_EXCEPTION_PATH = Path(
    "data/results/razorpay_webhook_reconciliation_exceptions.jsonl"
)


def _get_webhook_secret() -> str:
    secret = os.getenv(
        "RAZORPAY_WEBHOOK_SECRET",
        "",
    ).strip()

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Razorpay webhook integration is not configured."
            ),
        )

    return secret


def _get_event_store() -> WebhookEventStore:
    configured_path = os.getenv(
        "RAZORPAY_WEBHOOK_EVENT_STORE_PATH",
        "",
    ).strip()

    path = (
        Path(configured_path)
        if configured_path
        else DEFAULT_EVENT_STORE_PATH
    )

    return WebhookEventStore(
        path=path,
    )


def _get_payment_store_path() -> Path:
    configured_path = os.getenv(
        "RAZORPAY_WEBHOOK_PAYMENT_STORE_PATH",
        "",
    ).strip()

    if configured_path:
        return Path(
            configured_path
        )

    return DEFAULT_PAYMENT_STORE_PATH


def _get_reconciliation_service() -> ReconciliationService:
    audit_path_value = os.getenv(
        "RAZORPAY_WEBHOOK_RECON_AUDIT_PATH",
        "",
    ).strip()

    exception_path_value = os.getenv(
        "RAZORPAY_WEBHOOK_RECON_EXCEPTION_PATH",
        "",
    ).strip()

    audit_path = (
        Path(audit_path_value)
        if audit_path_value
        else DEFAULT_RECON_AUDIT_PATH
    )

    exception_path = (
        Path(exception_path_value)
        if exception_path_value
        else DEFAULT_RECON_EXCEPTION_PATH
    )

    return ReconciliationService(
        audit_path=audit_path,
        exception_path=exception_path,
    )


def _extract_payment_entity(
    payload: Any,
) -> dict[str, Any] | None:
    if hasattr(
        payload,
        "model_dump",
    ):
        payload_data = (
            payload.model_dump()
        )

    elif isinstance(
        payload,
        dict,
    ):
        payload_data = payload

    else:
        return None

    payment_container = (
        payload_data.get(
            "payment"
        )
    )

    if not isinstance(
        payment_container,
        dict,
    ):
        return None

    payment_entity = (
        payment_container.get(
            "entity"
        )
    )

    if not isinstance(
        payment_entity,
        dict,
    ):
        return None

    return payment_entity


def _append_payment_evidence(
    *,
    event_id: str,
    event: str,
    razorpay_payment: Any,
    reconai_payment: Any,
) -> None:
    path = (
        _get_payment_store_path()
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    record = {
        "event_id": event_id,
        "event": event,
        "razorpay_payment": (
            razorpay_payment.model_dump(
                mode="json",
            )
        ),
        "reconai_payment": (
            reconai_payment.model_dump(
                mode="json",
            )
        ),
    }

    with path.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            json.dumps(
                record,
                sort_keys=True,
            )
        )

        file.write(
            "\n"
        )


@router.post("")
async def razorpay_webhook(
    request: Request,
) -> dict[str, Any]:
    raw_body = (
        await request.body()
    )

    signature = (
        request.headers.get(
            "x-razorpay-signature",
            "",
        )
        .strip()
    )

    event_id = (
        request.headers.get(
            "x-razorpay-event-id",
            "",
        )
        .strip()
    )

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Missing x-razorpay-signature."
            ),
        )

    if not event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Missing x-razorpay-event-id."
            ),
        )

    webhook_secret = (
        _get_webhook_secret()
    )

    event_store = (
        _get_event_store()
    )

    try:
        result = process_webhook(
            raw_body=raw_body,
            signature=signature,
            event_id=event_id,
            webhook_secret=webhook_secret,
            event_store=event_store,
        )

    except RazorpayWebhookSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(
                exc
            ),
        ) from exc

    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Razorpay webhook payload validation failed."
            ),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                exc
            ),
        ) from exc

    if result.duplicate:
        return {
            "success": True,
            "event_id": (
                result.event_id
            ),
            "event": (
                result.event
            ),
            "duplicate": True,
            "payment_ingested": False,
            "payment_id": None,
            "order_id": None,
            "reconai_transaction_id": None,
            "reconciliation_status": None,
            "reconciliation_method": None,
            "reconciliation_confidence": None,
        }

    if result.payload is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Webhook processing produced no validated payload."
            ),
        )

    if result.event != "payment.captured":
        event_store.record(
            event_id=result.event_id,
            event=result.event,
        )

        return {
            "success": True,
            "event_id": (
                result.event_id
            ),
            "event": (
                result.event
            ),
            "duplicate": False,
            "payment_ingested": False,
            "payment_id": None,
            "order_id": None,
            "reconai_transaction_id": None,
            "reconciliation_status": None,
            "reconciliation_method": None,
            "reconciliation_confidence": None,
        }

    envelope_data = (
        result.payload.model_dump()
    )

    payload_data = (
        envelope_data.get(
            "payload"
        )
    )

    payment_entity = (
        _extract_payment_entity(
            payload_data
        )
    )

    if payment_entity is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "payment.captured webhook contains no "
                "payload.payment.entity."
            ),
        )

    try:
        normalized_payment = (
            normalize_payment(
                payment_entity
            )
        )

    except (
        ValidationError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Unable to normalize Razorpay payment."
            ),
        ) from exc

    try:
        reconai_payment = (
            razorpay_payment_to_reconai(
                normalized_payment
            )
        )

    except RazorpayAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Unable to adapt Razorpay payment into "
                "ReconAI domain model: "
                f"{exc}"
            ),
        ) from exc

    (
        eligible,
        excluded,
    ) = select_reconcilable_payments(
        [
            reconai_payment,
        ]
    )

    if excluded or not eligible:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "payment.captured webhook produced "
                "a non-reconcilable payment state."
            ),
        )

    if len(
        eligible
    ) != 1:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unexpected Razorpay payment eligibility result."
            ),
        )

    eligible_payment = (
        eligible[0]
    )

    try:
        _append_payment_evidence(
            event_id=result.event_id,
            event=result.event,
            razorpay_payment=normalized_payment,
            reconai_payment=eligible_payment,
        )

    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to persist Razorpay payment evidence."
            ),
        ) from exc

    # --------------------------------------------------------------
    # EVENT-DRIVEN RECONCILIATION
    # --------------------------------------------------------------
    #
    # At webhook arrival time we currently have payment evidence only.
    #
    # We DO NOT invent ledger or settlement records.
    #
    # Finance-safe expected outcome:
    #
    #     MISSING_LEDGER
    #
    # This is recorded in the reconciliation audit and exception
    # manifest by the existing deterministic engine.
    # --------------------------------------------------------------

    reconciliation_service = (
        _get_reconciliation_service()
    )

    try:
        reconciliation_result = (
            reconciliation_service.reconcile_payment(
                payment=eligible_payment,
                ledger=[],
                settlements=[],
            )
        )

    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to persist reconciliation evidence."
            ),
        ) from exc

    if len(
        reconciliation_result.results
    ) != 1:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unexpected reconciliation result count."
            ),
        )

    decision = (
        reconciliation_result.results[
            0
        ]
    )

    # --------------------------------------------------------------
    # COMMIT EVENT ID LAST
    # --------------------------------------------------------------

    try:
        event_store.record(
            event_id=result.event_id,
            event=result.event,
        )

    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unable to commit Razorpay webhook event."
            ),
        ) from exc

    return {
        "success": True,
        "event_id": (
            result.event_id
        ),
        "event": (
            result.event
        ),
        "duplicate": False,
        "payment_ingested": True,
        "payment_id": (
            eligible_payment.payment_id
        ),
        "order_id": (
            eligible_payment.order_id
        ),
        "reconai_transaction_id": (
            eligible_payment.transaction_id
        ),
        "reconciliation_status": (
            decision.status.value
        ),
        "reconciliation_method": (
            decision.method.value
        ),
        "reconciliation_confidence": (
            decision.confidence
        ),
    }