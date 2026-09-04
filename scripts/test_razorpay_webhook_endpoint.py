from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.app.main import app


TEST_WEBHOOK_SECRET = (
    "reconai_local_webhook_test_secret"
)

TEST_PAYMENT_ID = (
    "pay_reconai_webhook_test"
)

TEST_ORDER_ID = (
    "order_reconai_webhook_test"
)

TEST_TRANSACTION_ID = (
    f"rzp_{TEST_PAYMENT_ID}"
)


def build_signature(
    raw_body: bytes,
) -> str:
    return hmac.new(
        TEST_WEBHOOK_SECRET.encode(
            "utf-8"
        ),
        raw_body,
        hashlib.sha256,
    ).hexdigest()


def build_payment_captured_payload() -> dict[str, Any]:
    return {
        "entity": "event",
        "account_id": (
            "acc_reconai_test"
        ),
        "event": (
            "payment.captured"
        ),
        "contains": [
            "payment",
        ],
        "payload": {
            "payment": {
                "entity": {
                    "id": (
                        TEST_PAYMENT_ID
                    ),
                    "entity": (
                        "payment"
                    ),
                    "amount": 12000,
                    "currency": "INR",
                    "status": (
                        "captured"
                    ),
                    "order_id": (
                        TEST_ORDER_ID
                    ),
                    "invoice_id": None,
                    "international": False,
                    "method": "upi",
                    "amount_refunded": 0,
                    "refund_status": None,
                    "captured": True,
                    "description": (
                        "ReconAI webhook test"
                    ),
                    "card_id": None,
                    "bank": None,
                    "wallet": None,
                    "vpa": (
                        "success@razorpay"
                    ),
                    "email": (
                        "reconai@example.com"
                    ),
                    "contact": (
                        "9999999999"
                    ),
                    "notes": {
                        "source": (
                            "reconai"
                        ),
                    },
                    "fee": 0,
                    "tax": 0,
                    "error_code": None,
                    "error_description": None,
                    "error_source": None,
                    "error_step": None,
                    "error_reason": None,
                    "acquirer_data": {},
                    "created_at": (
                        1788425424
                    ),
                }
            }
        },
        "created_at": (
            1788425424
        ),
    }


def build_invalid_captured_payload() -> dict[str, Any]:
    payload = (
        build_payment_captured_payload()
    )

    payload[
        "payload"
    ][
        "payment"
    ][
        "entity"
    ][
        "order_id"
    ] = None

    return payload


def serialize_payload(
    payload: dict[str, Any],
) -> bytes:
    return json.dumps(
        payload,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )


def post_signed_webhook(
    *,
    client: TestClient,
    payload: dict[str, Any],
    event_id: str,
) -> Any:
    raw_body = (
        serialize_payload(
            payload
        )
    )

    signature = (
        build_signature(
            raw_body
        )
    )

    return client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "content-type": (
                "application/json"
            ),
            "x-razorpay-signature": (
                signature
            ),
            "x-razorpay-event-id": (
                event_id
            ),
        },
    )


def read_jsonl(
    path: Path,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[
        dict[str, Any]
    ] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            if not line.strip():
                continue

            records.append(
                json.loads(
                    line
                )
            )

    return records


def count_jsonl_records(
    path: Path,
) -> int:
    return len(
        read_jsonl(
            path
        )
    )


def run_tests() -> None:
    print(
        "=" * 72
    )
    print(
        "RECONAI RAZORPAY WEBHOOK RECONCILIATION TEST"
    )
    print(
        "=" * 72
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(
            temp_dir
        )

        event_store_path = (
            temp_path
            / "events.jsonl"
        )

        payment_store_path = (
            temp_path
            / "payments.jsonl"
        )

        recon_audit_path = (
            temp_path
            / "reconciliation_audit.jsonl"
        )

        recon_exception_path = (
            temp_path
            / "reconciliation_exceptions.jsonl"
        )

        os.environ[
            "RAZORPAY_WEBHOOK_SECRET"
        ] = TEST_WEBHOOK_SECRET

        os.environ[
            "RAZORPAY_WEBHOOK_EVENT_STORE_PATH"
        ] = str(
            event_store_path
        )

        os.environ[
            "RAZORPAY_WEBHOOK_PAYMENT_STORE_PATH"
        ] = str(
            payment_store_path
        )

        os.environ[
            "RAZORPAY_WEBHOOK_RECON_AUDIT_PATH"
        ] = str(
            recon_audit_path
        )

        os.environ[
            "RAZORPAY_WEBHOOK_RECON_EXCEPTION_PATH"
        ] = str(
            recon_exception_path
        )

        client = TestClient(
            app
        )

        payload = (
            build_payment_captured_payload()
        )

        # ----------------------------------------------------------
        # 1. Health
        # ----------------------------------------------------------

        health = client.get(
            "/health"
        )

        assert (
            health.status_code
            == 200
        )

        print()
        print(
            "Health endpoint              : PASS"
        )

        # ----------------------------------------------------------
        # 2. Valid captured webhook
        # ----------------------------------------------------------

        response = (
            post_signed_webhook(
                client=client,
                payload=payload,
                event_id=(
                    "evt_reconai_001"
                ),
            )
        )

        assert (
            response.status_code
            == 200
        ), response.text

        body = (
            response.json()
        )

        assert (
            body[
                "success"
            ]
            is True
        )

        assert (
            body[
                "payment_ingested"
            ]
            is True
        )

        assert (
            body[
                "reconai_transaction_id"
            ]
            == TEST_TRANSACTION_ID
        )

        print(
            "Valid captured webhook       : PASS"
        )

        # ----------------------------------------------------------
        # 3. Event-driven reconciliation result
        # ----------------------------------------------------------

        assert (
            body[
                "reconciliation_status"
            ]
            == "MISSING_LEDGER"
        )

        assert (
            body[
                "reconciliation_method"
            ]
            == "NONE"
        )

        assert (
            body[
                "reconciliation_confidence"
            ]
            == 0.0
        )

        print(
            "Webhook reconciliation       : PASS"
        )

        print(
            "Expected MISSING_LEDGER       : PASS"
        )

        # ----------------------------------------------------------
        # 4. Payment/domain persistence
        # ----------------------------------------------------------

        payment_records = (
            read_jsonl(
                payment_store_path
            )
        )

        assert (
            len(
                payment_records
            )
            == 1
        )

        stored_payment = (
            payment_records[
                0
            ][
                "reconai_payment"
            ]
        )

        assert (
            stored_payment[
                "transaction_id"
            ]
            == TEST_TRANSACTION_ID
        )

        assert (
            stored_payment[
                "payment_id"
            ]
            == TEST_PAYMENT_ID
        )

        assert (
            stored_payment[
                "order_id"
            ]
            == TEST_ORDER_ID
        )

        print(
            "ReconAI domain persistence   : PASS"
        )

        # ----------------------------------------------------------
        # 5. Reconciliation audit
        # ----------------------------------------------------------

        audit_records = (
            read_jsonl(
                recon_audit_path
            )
        )

        assert (
            len(
                audit_records
            )
            == 1
        )

        print(
            "Reconciliation audit written : PASS"
        )

        # ----------------------------------------------------------
        # 6. Exception manifest
        # ----------------------------------------------------------

        exception_records = (
            read_jsonl(
                recon_exception_path
            )
        )

        assert (
            len(
                exception_records
            )
            == 1
        )

        print(
            "Exception manifest written   : PASS"
        )

        # ----------------------------------------------------------
        # 7. Duplicate webhook
        # ----------------------------------------------------------

        duplicate = (
            post_signed_webhook(
                client=client,
                payload=payload,
                event_id=(
                    "evt_reconai_001"
                ),
            )
        )

        assert (
            duplicate.status_code
            == 200
        ), duplicate.text

        duplicate_body = (
            duplicate.json()
        )

        assert (
            duplicate_body[
                "duplicate"
            ]
            is True
        )

        assert (
            duplicate_body[
                "payment_ingested"
            ]
            is False
        )

        # Duplicate must not cause another reconciliation.

        assert (
            len(
                read_jsonl(
                    recon_audit_path
                )
            )
            == 1
        )

        assert (
            len(
                read_jsonl(
                    recon_exception_path
                )
            )
            == 1
        )

        print(
            "Duplicate delivery           : PASS"
        )

        print(
            "Duplicate reconciliation blocked: PASS"
        )

        # ----------------------------------------------------------
        # 8. Invalid HMAC
        # ----------------------------------------------------------

        raw_body = (
            serialize_payload(
                payload
            )
        )

        invalid_hmac = (
            client.post(
                "/webhooks/razorpay",
                content=raw_body,
                headers={
                    "content-type": (
                        "application/json"
                    ),
                    "x-razorpay-signature": (
                        "invalid_signature"
                    ),
                    "x-razorpay-event-id": (
                        "evt_reconai_002"
                    ),
                },
            )
        )

        assert (
            invalid_hmac.status_code
            == 401
        )

        print(
            "Invalid HMAC                 : PASS"
        )

        # ----------------------------------------------------------
        # 9. Missing event ID
        # ----------------------------------------------------------

        signature = (
            build_signature(
                raw_body
            )
        )

        missing_event_id = (
            client.post(
                "/webhooks/razorpay",
                content=raw_body,
                headers={
                    "content-type": (
                        "application/json"
                    ),
                    "x-razorpay-signature": (
                        signature
                    ),
                },
            )
        )

        assert (
            missing_event_id.status_code
            == 400
        )

        print(
            "Missing event ID             : PASS"
        )

        # ----------------------------------------------------------
        # 10. Downstream failure remains retryable
        # ----------------------------------------------------------

        invalid_payload = (
            build_invalid_captured_payload()
        )

        retry_event_id = (
            "evt_reconai_retryable"
        )

        failed = (
            post_signed_webhook(
                client=client,
                payload=invalid_payload,
                event_id=retry_event_id,
            )
        )

        assert (
            failed.status_code
            == 422
        ), failed.text

        event_ids = {
            record[
                "event_id"
            ]
            for record
            in read_jsonl(
                event_store_path
            )
        }

        assert (
            retry_event_id
            not in event_ids
        )

        print(
            "Failure remains retryable    : PASS"
        )

        # ----------------------------------------------------------
        # 11. Retry corrected event
        # ----------------------------------------------------------

        retry = (
            post_signed_webhook(
                client=client,
                payload=payload,
                event_id=retry_event_id,
            )
        )

        assert (
            retry.status_code
            == 200
        ), retry.text

        assert (
            retry.json()[
                "duplicate"
            ]
            is False
        )

        assert (
            retry.json()[
                "reconciliation_status"
            ]
            == "MISSING_LEDGER"
        )

        print(
            "Successful retry             : PASS"
        )

        # Two successful webhook deliveries should produce:
        #
        # 2 payment evidence records
        # 2 reconciliation decisions
        # 2 exception events
        # 2 committed event IDs

        assert (
            count_jsonl_records(
                event_store_path
            )
            == 2
        )

        assert (
            count_jsonl_records(
                payment_store_path
            )
            == 2
        )

        assert (
            count_jsonl_records(
                recon_audit_path
            )
            == 2
        )

        assert (
            count_jsonl_records(
                recon_exception_path
            )
            == 2
        )

        print()
        print(
            "Committed webhook events     : 2"
        )

        print(
            "Domain payments persisted    : 2"
        )

        print(
            "Reconciliation decisions     : 2"
        )

        print(
            "Exception events             : 2"
        )

    print()
    print(
        "=" * 72
    )

    print(
        "RAZORPAY WEBHOOK → RECONCILIATION: PASS"
    )

    print(
        "=" * 72
    )


if __name__ == "__main__":
    run_tests()