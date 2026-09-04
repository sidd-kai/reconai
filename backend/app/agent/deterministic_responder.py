from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from backend.app.agent.agent import ToolExecutionResult


def build_deterministic_answer(
    execution: ToolExecutionResult,
) -> str:
    """
    Convert deterministic tool evidence into a concise user-facing
    response without invoking an LLM.

    Financial values originate exclusively from the tool result.
    """

    if not execution.success:
        return (
            "I could not complete the requested finance operation. "
            f"Tool: {execution.tool_name}. "
            f"Error: {execution.error}"
        )

    result = execution.result

    if is_dataclass(result):
        payload: Any = asdict(result)
    else:
        payload = result

    if execution.tool_name == "get_batch_summary":
        return _batch_summary(payload)

    if execution.tool_name == "get_high_value_exceptions":
        return _high_value_exceptions(payload)

    if execution.tool_name == "investigate_exception":
        return _investigation(payload)

    if execution.tool_name == "verify_audit_chain":
        return _audit_result(payload)

    return (
        f"{execution.tool_name} completed successfully. "
        f"Evidence: {payload}"
    )


def _batch_summary(
    payload: dict[str, Any],
) -> str:
    records = payload.get(
        "records_processed",
        0,
    )
    matched = payload.get(
        "matched",
        0,
    )
    exceptions = payload.get(
        "exceptions",
        0,
    )
    match_rate = float(
        payload.get(
            "match_rate",
            0.0,
        )
    )

    breakdown = payload.get(
        "exception_breakdown",
        [],
    )

    lines = [
        (
            f"Current reconciliation batch: "
            f"{matched}/{records} records matched "
            f"({match_rate:.2%} match rate)."
        ),
        (
            f"Unresolved exceptions: {exceptions} "
            f"out of {records} records."
        ),
    ]

    if breakdown:
        lines.append("Exception categories:")

        for category in breakdown:
            status = category.get(
                "status",
                "UNKNOWN",
            )
            count = category.get(
                "count",
                0,
            )

            lines.append(
                f"- {status}: {count}"
            )

    audit_verified = payload.get(
        "audit_chain_verified"
    )

    if audit_verified is not None:
        lines.append(
            "Audit chain: "
            + (
                "verified."
                if audit_verified
                else "verification failed."
            )
        )

    return "\n".join(lines)


def _high_value_exceptions(
    payload: list[dict[str, Any]],
) -> str:
    if not payload:
        return "There are currently no exceptions in the manifest."

    lines = [
        f"Top {len(payload)} exceptions by absolute amount difference:"
    ]

    for index, exception in enumerate(
        payload,
        start=1,
    ):
        transaction_id = exception.get(
            "transaction_id",
            "UNKNOWN",
        )

        difference = exception.get(
            "amount_difference",
            0,
        )

        status = exception.get(
            "status",
            "UNKNOWN",
        )

        lines.append(
            f"{index}. {transaction_id} — "
            f"{status} — amount difference: {difference}"
        )

    return "\n".join(lines)


def _investigation(
    payload: dict[str, Any],
) -> str:
    transaction_id = payload.get(
        "transaction_id",
        "UNKNOWN",
    )

    status = payload.get(
        "status",
        "UNKNOWN",
    )

    reason = payload.get(
        "reason",
        "No reason provided.",
    )

    confidence = payload.get(
        "confidence",
        0.0,
    )

    difference = payload.get(
        "amount_difference",
        0.0,
    )

    candidate_count = payload.get(
        "candidate_count",
        0,
    )

    return "\n".join(
        [
            f"Transaction: {transaction_id}",
            f"Status: {status}",
            f"Reason: {reason}",
            f"Confidence: {confidence}",
            f"Amount difference: {difference}",
            f"Candidates evaluated: {candidate_count}",
            "",
            "This is deterministic reconciliation evidence. "
            "The transaction has not been automatically resolved.",
        ]
    )


def _audit_result(
    payload: dict[str, Any],
) -> str:
    verified = payload.get(
        "verified",
        False,
    )

    records_verified = payload.get(
        "records_verified",
        0,
    )

    error = payload.get(
        "error"
    )

    answer = (
        "Immutable audit chain verification: "
        + (
            "VALID."
            if verified
            else "FAILED."
        )
        + f" Records verified: {records_verified}."
    )

    if error:
        answer += f" Error: {error}"

    return answer