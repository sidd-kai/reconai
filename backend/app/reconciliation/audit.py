from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """
    Append-only, hash-chained JSONL audit logger.

    Every event contains:

        timestamp
        event_type
        previous_hash
        payload
        record_hash

    The first record starts from the GENESIS hash.
    """

    GENESIS_HASH = "GENESIS"

    def __init__(self, path: Path) -> None:
        self.path = path

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._previous_hash = (
            self._get_last_hash()
        )

    def _get_last_hash(self) -> str:
        """
        Recover the hash of the last valid record.

        If the file does not exist or contains no valid
        records, start a new chain from GENESIS.
        """

        if not self.path.exists():
            return self.GENESIS_HASH

        last_hash = self.GENESIS_HASH

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line in file:
                line = line.strip()

                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                record_hash = record.get(
                    "record_hash"
                )

                if isinstance(record_hash, str):
                    last_hash = record_hash

        return last_hash

    def append(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Append one hash-chained audit record.
        """

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        record: dict[str, Any] = {
            "timestamp": timestamp,
            "event_type": event_type,
            "previous_hash": self._previous_hash,
            "payload": payload,
        }

        canonical_record = json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
        )

        record_hash = hashlib.sha256(
            canonical_record.encode("utf-8")
        ).hexdigest()

        record["record_hash"] = record_hash

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                json.dumps(
                    record,
                    sort_keys=True,
                )
                + "\n"
            )

        self._previous_hash = record_hash