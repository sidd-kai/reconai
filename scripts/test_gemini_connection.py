from __future__ import annotations

import os

from google import genai


def main() -> None:
    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise SystemExit(
            "GEMINI_API_KEY is not configured."
        )

    client = genai.Client(
        api_key=api_key
    )

    response = client.models.generate_content(
        model="gemini-3.7-flash",
        contents=(
            "Respond with exactly: "
            "RECONAI GEMINI CONNECTION OK"
        ),
    )

    print(
        response.text
    )

    assert (
        "RECONAI GEMINI CONNECTION OK"
        in response.text
    )

    print(
        "GEMINI CONNECTION: PASS"
    )


if __name__ == "__main__":
    main()