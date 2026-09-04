from __future__ import annotations

from backend.app.agent.tools import (
    verify_audit_chain_tool,
)


def main() -> None:
    result = verify_audit_chain_tool()

    print(
        f"Verified        : {result['verified']}"
    )
    print(
        f"Records verified: "
        f"{result['records_verified']}"
    )
    print(
        f"Error           : "
        f"{result['error']}"
    )

    assert result["verified"] is True
    assert result["records_verified"] > 0
    assert result["error"] is None

    print("AUDIT TOOL TEST: PASS")


if __name__ == "__main__":
    main()