from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path

from .schemas import RazorpayWebhookEnvelope


class RazorpayWebhookSignatureError(ValueError):
    """
    Raised when Razorpay webhook signature validation fails.
    """


@dataclass(frozen=True)
class WebhookProcessingResult:
    event_id: str
    event: str
    duplicate: bool
    payload: RazorpayWebhookEnvelope | None


class WebhookEventStore:
    """
    Durable Test Mode idempotency store.

    Each successfully processed x-razorpay-event-id is written
    to JSONL.

    For the Buildathon single-instance demo this is sufficient.

    Production migration:
        PostgreSQL table with UNIQUE(event_id).
    """

    def __init__(
        self,
        path: Path = Path(
            "data/results/razorpay_webhook_events.jsonl"
        ),
    ) -> None:
        self.path = path

    def contains(
        self,
        event_id: str,
    ) -> bool:
        if not self.path.exists():
            return False

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if record.get("event_id") == event_id:
                    return True

        return False

    def record(
        self,
        *,
        event_id: str,
        event: str,
    ) -> None:
        """
        Commit a successfully processed webhook event.
        """

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    {
                        "event_id": event_id,
                        "event": event,
                    },
                    sort_keys=True,
                )
            )
            file.write("\n")


def verify_webhook_signature(
    *,
    raw_body: bytes,
    signature: str,
    webhook_secret: str,
) -> bool:
    """
    Verify Razorpay HMAC-SHA256 against the exact raw body.
    """

    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature,
    )


def process_webhook(
    *,
    raw_body: bytes,
    signature: str,
    event_id: str,
    webhook_secret: str,
    event_store: WebhookEventStore,
) -> WebhookProcessingResult:
    """
    Verify, deduplicate and validate a Razorpay webhook.

    IMPORTANT:
    This function does NOT record the event ID.

    Event commit happens only after downstream processing succeeds.

    Flow:
        1. Require event ID
        2. Verify signature
        3. Check duplicate
        4. Parse JSON
        5. Validate envelope
        6. Return validated event
    """

    normalized_event_id = event_id.strip()

    if not normalized_event_id:
        raise ValueError(
            "Missing x-razorpay-event-id."
        )

    if not verify_webhook_signature(
        raw_body=raw_body,
        signature=signature,
        webhook_secret=webhook_secret,
    ):
        raise RazorpayWebhookSignatureError(
            "Invalid Razorpay webhook signature."
        )

    if event_store.contains(
        normalized_event_id
    ):
        return WebhookProcessingResult(
            event_id=normalized_event_id,
            event="DUPLICATE",
            duplicate=True,
            payload=None,
        )

    try:
        decoded = json.loads(
            raw_body
        )

    except json.JSONDecodeError as exc:
        raise ValueError(
            "Invalid Razorpay webhook JSON."
        ) from exc

    envelope = RazorpayWebhookEnvelope.model_validate(
        decoded
    )

    return WebhookProcessingResult(
        event_id=normalized_event_id,
        event=envelope.event,
        duplicate=False,
        payload=envelope,
    )