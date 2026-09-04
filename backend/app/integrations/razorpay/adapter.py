from __future__ import annotations

from datetime import UTC, datetime

from backend.app.reconciliation.models import Payment

from .schemas import RazorpayPaymentRecord


class RazorpayAdapterError(
    ValueError,
):
    """
    Raised when a Razorpay record cannot be safely converted
    into a ReconAI domain model.
    """


def build_transaction_id(
    *,
    payment_id: str,
) -> str:
    """
    Build a unique ReconAI transaction ID for a Razorpay payment.

    IMPORTANT:

    Razorpay allows multiple payment attempts against the same order.

    Example:

        order_ABC
            pay_001 -> failed
            pay_002 -> failed
            pay_003 -> captured

    Therefore order_id MUST NOT be used as ReconAI transaction_id.

    payment_id uniquely identifies the payment attempt.

    order_id remains the shared business reference used for
    payment <-> ledger reconciliation.
    """

    normalized_payment_id = (
        payment_id.strip()
    )

    if not normalized_payment_id:
        raise RazorpayAdapterError(
            "Cannot build transaction_id "
            "from an empty Razorpay payment_id."
        )

    return (
        f"rzp_{normalized_payment_id}"
    )


def razorpay_payment_to_reconai(
    payment: RazorpayPaymentRecord,
) -> Payment:
    """
    Convert a normalized Razorpay payment into ReconAI's
    deterministic Payment model.

    Mapping:

        Razorpay payment.id
            -> Payment.payment_id

        Razorpay payment.id
            -> unique internal transaction_id

        Razorpay order_id
            -> Payment.order_id

        Razorpay amount
            -> Payment.amount

        Razorpay currency
            -> Payment.currency

        Razorpay status
            -> Payment.status

    No LLM-generated values are introduced.
    """

    payment_id = (
        payment.payment_id.strip()
    )

    if not payment_id:
        raise RazorpayAdapterError(
            "Razorpay payment is missing payment_id."
        )

    if payment.order_id is None:
        raise RazorpayAdapterError(
            "Razorpay payment "
            f"{payment_id} "
            "has no order_id and cannot be safely "
            "linked to merchant ledger evidence."
        )

    order_id = (
        payment.order_id.strip()
    )

    if not order_id:
        raise RazorpayAdapterError(
            "Razorpay payment "
            f"{payment_id} "
            "contains an empty order_id."
        )

    transaction_id = (
        build_transaction_id(
            payment_id=payment_id,
        )
    )

    created_at = (
        datetime.fromtimestamp(
            payment.created_at,
            tz=UTC,
        )
    )

    return Payment(
        transaction_id=transaction_id,
        payment_id=payment_id,
        order_id=order_id,
        amount=payment.amount,
        currency=payment.currency.upper(),
        status=payment.status.lower(),
        created_at=created_at,
    )


def razorpay_payments_to_reconai(
    payments: list[
        RazorpayPaymentRecord
    ],
) -> tuple[
    list[Payment],
    list[dict[str, str]],
]:
    """
    Convert a batch of normalized Razorpay payments.

    Records that cannot be converted are quarantined rather
    than silently discarded.

    Failed payments are still converted here because this adapter
    represents ingestion.

    Filtering financial states such as CAPTURED happens separately
    before reconciliation.
    """

    valid_payments: list[
        Payment
    ] = []

    quarantined_records: list[
        dict[str, str]
    ] = []

    for payment in payments:
        try:
            converted = (
                razorpay_payment_to_reconai(
                    payment
                )
            )

        except RazorpayAdapterError as exc:
            quarantined_records.append(
                {
                    "payment_id": (
                        payment.payment_id
                    ),
                    "reason": str(
                        exc
                    ),
                }
            )

            continue

        valid_payments.append(
            converted
        )

    return (
        valid_payments,
        quarantined_records,
    )


def select_reconcilable_payments(
    payments: list[Payment],
) -> tuple[
    list[Payment],
    list[Payment],
]:
    """
    Split ingested Razorpay payments into:

        reconcilable payments
        non-financial payment attempts

    For the current ReconAI payment reconciliation flow,
    only captured payments are treated as successful financial
    evidence.

    Failed payment attempts remain visible to ingestion/audit
    but do not participate in ledger reconciliation.
    """

    reconcilable: list[
        Payment
    ] = []

    excluded: list[
        Payment
    ] = []

    for payment in payments:
        status = (
            payment.status
            .strip()
            .lower()
        )

        if status == "captured":
            reconcilable.append(
                payment
            )
        else:
            excluded.append(
                payment
            )

    return (
        reconcilable,
        excluded,
    )