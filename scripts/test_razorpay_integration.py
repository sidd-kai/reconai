from __future__ import annotations

import hashlib
import hmac
import json
import os

from backend.app.integrations.razorpay.adapter import (
    razorpay_payments_to_reconai,
)
from backend.app.integrations.razorpay.client import (
    RazorpayClient,
)
from backend.app.integrations.razorpay.config import (
    RazorpaySettings,
)
from backend.app.integrations.razorpay.normalizer import (
    normalize_payment,
    normalize_settlement,
)
from backend.app.integrations.razorpay.webhooks import (
    verify_webhook_signature,
)


def test_webhook_signature() -> None:
    """
    Deterministic local webhook verification test.
    """

    secret = (
        "reconai_test_webhook_secret"
    )

    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": (
                        "pay_test_123"
                    ),
                }
            }
        },
    }

    raw_body = json.dumps(
        payload,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    signature = hmac.new(
        secret.encode(
            "utf-8"
        ),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    verified = (
        verify_webhook_signature(
            raw_body=raw_body,
            signature=signature,
            webhook_secret=secret,
        )
    )

    if not verified:
        raise AssertionError(
            "Webhook signature verification failed."
        )


def main() -> None:
    print(
        "=" * 72
    )
    print(
        "RECONAI RAZORPAY TEST MODE INTEGRATION"
    )
    print(
        "=" * 72
    )

    # ------------------------------------------------------------------
    # Local webhook crypto
    # ------------------------------------------------------------------

    test_webhook_signature()

    print()
    print(
        "Webhook HMAC verification : PASS"
    )

    # ------------------------------------------------------------------
    # Environment configuration
    # ------------------------------------------------------------------

    if not os.getenv(
        "RAZORPAY_KEY_ID"
    ):
        print()

        print(
            "Razorpay API test         : SKIPPED"
        )

        print(
            "Reason                    : "
            "RAZORPAY_KEY_ID is not configured"
        )

        print()
        print(
            "=" * 72
        )

        print(
            "RAZORPAY LOCAL INTEGRATION: PASS"
        )

        print(
            "=" * 72
        )

        return

    settings = (
        RazorpaySettings.from_env()
    )

    print()
    print(
        "Configuration             : PASS"
    )

    # ------------------------------------------------------------------
    # Razorpay Test Mode API
    # ------------------------------------------------------------------

    with RazorpayClient(
        settings
    ) as client:

        payments_response = (
            client.fetch_payments(
                count=10,
            )
        )

        settlements_response = (
            client.fetch_settlements(
                count=10,
            )
        )

    # ------------------------------------------------------------------
    # Razorpay normalization
    # ------------------------------------------------------------------

    normalized_payments = [
        normalize_payment(
            payment
        )
        for payment
        in payments_response.items
    ]

    normalized_settlements = [
        normalize_settlement(
            settlement
        )
        for settlement
        in settlements_response.items
    ]

    print()

    print(
        f"Payments fetched          : "
        f"{len(payments_response.items)}"
    )

    print(
        f"Payments normalized       : "
        f"{len(normalized_payments)}"
    )

    print(
        f"Settlements fetched       : "
        f"{len(settlements_response.items)}"
    )

    print(
        f"Settlements normalized    : "
        f"{len(normalized_settlements)}"
    )

    # ------------------------------------------------------------------
    # ReconAI domain adaptation
    # ------------------------------------------------------------------

    (
        reconai_payments,
        quarantined_payments,
    ) = razorpay_payments_to_reconai(
        normalized_payments
    )

    print()
    print(
        "RECONAI DOMAIN ADAPTER"
    )
    print(
        "-" * 72
    )

    print(
        f"ReconAI payments          : "
        f"{len(reconai_payments)}"
    )

    print(
        f"Quarantined payments      : "
        f"{len(quarantined_payments)}"
    )

    if reconai_payments:
        print()

        print(
            "NORMALIZED PAYMENT SAMPLE"
        )
        print(
            "-" * 72
        )

        sample = (
            reconai_payments[0]
        )

        print(
            f"transaction_id            : "
            f"{sample.transaction_id}"
        )

        print(
            f"payment_id                : "
            f"{sample.payment_id}"
        )

        print(
            f"order_id                  : "
            f"{sample.order_id}"
        )

        print(
            f"amount                    : "
            f"{sample.amount}"
        )

        print(
            f"currency                  : "
            f"{sample.currency}"
        )

        print(
            f"status                    : "
            f"{sample.status}"
        )

        print(
            f"created_at                : "
            f"{sample.created_at.isoformat()}"
        )

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    if (
        len(normalized_payments)
        != len(
            payments_response.items
        )
    ):
        raise AssertionError(
            "Not every Razorpay payment was normalized."
        )

    if (
        len(reconai_payments)
        + len(quarantined_payments)
        != len(normalized_payments)
    ):
        raise AssertionError(
            "Razorpay adapter silently lost payment records."
        )

    print()
    print(
        "=" * 72
    )

    print(
        "RAZORPAY TEST MODE INTEGRATION: PASS"
    )

    print(
        "=" * 72
    )


if __name__ == "__main__":
    main()