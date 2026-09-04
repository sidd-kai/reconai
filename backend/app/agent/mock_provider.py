from __future__ import annotations

from typing import Any

from backend.app.agent.provider import (
    LLMProvider,
    ModelResponse,
    ToolCall,
)


class MockFinanceProvider(LLMProvider):
    """
    Deterministic provider used for agent integration tests.

    This simulates an LLM requesting a finance tool.
    """

    def __init__(self) -> None:
        self._tool_called = False

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:

        if not self._tool_called:
            self._tool_called = True

            return ModelResponse(
                content=None,
                tool_calls=(
                    ToolCall(
                        tool_name="verify_audit_chain",
                        arguments={},
                    ),
                ),
            )

        tool_messages = [
            message
            for message in messages
            if message.get("role") == "tool"
        ]

        if not tool_messages:
            return ModelResponse(
                content=(
                    "I was unable to obtain audit evidence."
                ),
                tool_calls=(),
            )

        latest_result = tool_messages[-1]["content"]

        return ModelResponse(
            content=(
                "The immutable audit chain was verified "
                "using the deterministic audit verification "
                f"tool. Evidence: {latest_result}"
            ),
            tool_calls=(),
        )
