from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RazorpaySettings:
    """
    Razorpay Test Mode configuration.

    Secrets must come from environment variables.
    Never commit credentials to the repository.
    """

    key_id: str
    key_secret: str
    webhook_secret: str | None

    base_url: str = "https://api.razorpay.com/v1"

    request_timeout_seconds: float = 15.0

    @classmethod
    def from_env(
        cls,
    ) -> "RazorpaySettings":
        key_id = os.getenv(
            "RAZORPAY_KEY_ID",
            "",
        ).strip()

        key_secret = os.getenv(
            "RAZORPAY_KEY_SECRET",
            "",
        ).strip()

        webhook_secret = os.getenv(
            "RAZORPAY_WEBHOOK_SECRET",
        )

        if not key_id:
            raise RuntimeError(
                "RAZORPAY_KEY_ID is not configured."
            )

        if not key_secret:
            raise RuntimeError(
                "RAZORPAY_KEY_SECRET is not configured."
            )

        return cls(
            key_id=key_id,
            key_secret=key_secret,
            webhook_secret=webhook_secret,
        )