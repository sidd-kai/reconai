from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


AUDIT_FILE = Path("data/results/audit.jsonl")


@dataclass(frozen=True)
class AuditVerificationResult:
    verified: bool
    records_verified: int
    error: str | None = None


def calculate_hash(record: dict) -> str:
    """
    Recalculate the hash from the canonical record
    excluding record_hash itself.
    """
    unsigned_record = {
        key: value
        for key, value in record.items()
        if key != "record_hash"
    }

    canonical = json.dumps(
        unsigned_record,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def verify_audit_chain(
    audit_file: Path = AUDIT_FILE,
) -> AuditVerificationResult:
    """
    Verify the complete immutable audit chain.

    Checks:
    1. Audit file exists.
    2. Every non-empty line contains valid JSON.
    3. previous_hash links correctly to the preceding record.
    4. record_hash matches the canonical record contents.
    """
    if not audit_file.exists():
        return AuditVerificationResult(
            verified=False,
            records_verified=0,
            error="Audit file does not exist.",
        )

    records: list[dict] = []

    try:
        with audit_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line_number, line in enumerate(
                file,
                start=1,
            ):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    return AuditVerificationResult(
                        verified=False,
                        records_verified=len(records),
                        error=(
                            f"Invalid JSON at line "
                            f"{line_number}: {exc}"
                        ),
                    )

                if not isinstance(record, dict):
                    return AuditVerificationResult(
                        verified=False,
                        records_verified=len(records),
                        error=(
                            f"Invalid audit record at line "
                            f"{line_number}: expected object."
                        ),
                    )

                records.append(record)

    except OSError as exc:
        return AuditVerificationResult(
            verified=False,
            records_verified=0,
            error=f"Unable to read audit file: {exc}",
        )

    if not records:
        return AuditVerificationResult(
            verified=False,
            records_verified=0,
            error="Audit file contains no records.",
        )

    expected_previous_hash = "GENESIS"

    for index, record in enumerate(
        records,
        start=1,
    ):
        actual_previous_hash = record.get(
            "previous_hash"
        )

        if actual_previous_hash != expected_previous_hash:
            return AuditVerificationResult(
                verified=False,
                records_verified=index - 1,
                error=(
                    f"CHAIN FAILURE at record {index}: "
                    f"expected previous_hash="
                    f"{expected_previous_hash}, "
                    f"got={actual_previous_hash}"
                ),
            )

        stored_hash = record.get(
            "record_hash"
        )

        if not isinstance(stored_hash, str):
            return AuditVerificationResult(
                verified=False,
                records_verified=index - 1,
                error=(
                    f"HASH FAILURE at record {index}: "
                    f"record_hash missing."
                ),
            )

        calculated_hash = calculate_hash(record)

        if stored_hash != calculated_hash:
            return AuditVerificationResult(
                verified=False,
                records_verified=index - 1,
                error=(
                    f"HASH FAILURE at record {index}: "
                    f"stored hash does not match "
                    f"calculated hash."
                ),
            )

        expected_previous_hash = stored_hash

    return AuditVerificationResult(
        verified=True,
        records_verified=len(records),
    )


def main() -> None:
    result = verify_audit_chain()

    if not result.verified:
        raise SystemExit(result.error)

    print("AUDIT CHAIN: PASS")
    print(
        f"Records verified: "
        f"{result.records_verified}"
    )


if __name__ == "__main__":
    main()