from __future__ import annotations

from typing import Any

import httpx

from .config import RazorpaySettings
from .schemas import RazorpayCollection


class RazorpayAPIError(
    RuntimeError,
):
    """
    Raised when Razorpay returns a non-success response.
    """


class RazorpayClient:
    """
    Minimal read-only Razorpay Test Mode REST client.

    IMPORTANT:
        This adapter intentionally exposes only fetch APIs.

        No capture.
        No refund.
        No mutation.
    """

    def __init__(
        self,
        settings: RazorpaySettings,
    ) -> None:
        self.settings = settings

        self._client = httpx.Client(
            base_url=settings.base_url,
            auth=(
                settings.key_id,
                settings.key_secret,
            ),
            timeout=settings.request_timeout_seconds,
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "ReconAI-Razorpay-Integration/1.0"
                ),
            },
        )

    def close(
        self,
    ) -> None:
        self._client.close()

    def __enter__(
        self,
    ) -> "RazorpayClient":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        self.close()

    def _get(
        self,
        path: str,
        *,
        params: dict[
            str,
            Any,
        ] | None = None,
    ) -> dict[str, Any]:

        response = self._client.get(
            path,
            params=params,
        )

        if (
            response.status_code
            < 200
            or response.status_code
            >= 300
        ):
            raise RazorpayAPIError(
                "Razorpay API request failed: "
                f"status={response.status_code}, "
                f"body={response.text[:500]}"
            )

        payload = response.json()

        if not isinstance(
            payload,
            dict,
        ):
            raise RazorpayAPIError(
                "Razorpay returned a non-object "
                "JSON response."
            )

        return payload

    def fetch_payments(
        self,
        *,
        count: int = 100,
        skip: int = 0,
        from_timestamp: int | None = None,
        to_timestamp: int | None = None,
    ) -> RazorpayCollection:
        """
        Fetch one page of Razorpay payments.

        Razorpay currently documents count up to 100.
        """

        if not 1 <= count <= 100:
            raise ValueError(
                "count must be between 1 and 100."
            )

        params: dict[
            str,
            Any,
        ] = {
            "count": count,
            "skip": skip,
        }

        if from_timestamp is not None:
            params[
                "from"
            ] = from_timestamp

        if to_timestamp is not None:
            params[
                "to"
            ] = to_timestamp

        payload = self._get(
            "/payments",
            params=params,
        )

        return RazorpayCollection.model_validate(
            payload
        )

    def fetch_all_payments(
        self,
        *,
        max_records: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Fetch payments using explicit pagination.

        This prevents silently assuming a single API page contains
        the complete Test Mode dataset.
        """

        if max_records <= 0:
            return []

        items: list[
            dict[str, Any]
        ] = []

        skip = 0

        while len(
            items
        ) < max_records:
            remaining = (
                max_records
                - len(
                    items
                )
            )

            count = min(
                remaining,
                100,
            )

            page = self.fetch_payments(
                count=count,
                skip=skip,
            )

            if not page.items:
                break

            items.extend(
                page.items
            )

            received = len(
                page.items
            )

            skip += received

            if received < count:
                break

        return items[
            :max_records
        ]

    def fetch_orders(
        self,
        *,
        count: int = 100,
        skip: int = 0,
    ) -> RazorpayCollection:
        """
        Fetch one page of Razorpay orders.
        """

        if not 1 <= count <= 100:
            raise ValueError(
                "count must be between 1 and 100."
            )

        payload = self._get(
            "/orders",
            params={
                "count": count,
                "skip": skip,
            },
        )

        return RazorpayCollection.model_validate(
            payload
        )

    def fetch_settlements(
        self,
        *,
        count: int = 100,
        skip: int = 0,
        from_timestamp: int | None = None,
        to_timestamp: int | None = None,
    ) -> RazorpayCollection:
        """
        Fetch one page of Razorpay settlements.
        """

        if not 1 <= count <= 100:
            raise ValueError(
                "count must be between 1 and 100."
            )

        params: dict[
            str,
            Any,
        ] = {
            "count": count,
            "skip": skip,
        }

        if from_timestamp is not None:
            params[
                "from"
            ] = from_timestamp

        if to_timestamp is not None:
            params[
                "to"
            ] = to_timestamp

        payload = self._get(
            "/settlements/",
            params=params,
        )

        return RazorpayCollection.model_validate(
            payload
        )