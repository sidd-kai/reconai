from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolExecution:
    tool_name: str
    arguments: dict[str, Any]
    result: Any


@dataclass(frozen=True)
class AIControllerResponse:
    answer: str
    tool_executions: tuple[ToolExecution, ...]


class AIController:
    """
    AI orchestration layer for ReconAI.

    Gemini is responsible for reasoning and tool selection.

    ReconAI tools remain the authoritative source of financial
    evidence.
    """

    SYSTEM_PROMPT = """
You are ReconAI, an AI Finance Controller.

Your job is to help finance teams understand reconciliation
results using authoritative deterministic tools.

CRITICAL RULES:

1. Never invent financial numbers.
2. Never claim a reconciliation result without tool evidence.
3. Use the available tools when financial evidence is required.
4. Treat tool results as authoritative.
5. Never modify financial records.
6. Never mark an exception as resolved.
7. If evidence is insufficient, explicitly say so.
8. Explain results clearly for a finance operations user.
9. When discussing exceptions, prioritize financial impact.
10. Preserve the distinction between matched records and
    unresolved exceptions.

You are an orchestration and explanation layer, not the
financial system of record.
"""

    def __init__(
        self,
        provider: Any,
        tool_registry: Any,
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry

    def ask(
        self,
        question: str,
    ) -> AIControllerResponse:
        """
        Process one natural-language finance-controller query.
        """

        if not question.strip():
            raise ValueError(
                "Question cannot be empty."
            )

        tools = self._get_tool_definitions()

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": self.SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": question.strip(),
            },
        ]

        executions: list[ToolExecution] = []

        for _ in range(5):
            response = self.provider.generate(
                messages=messages,
                tools=tools,
            )

            if not response.tool_calls:
                return AIControllerResponse(
                    answer=(
                        response.content
                        or "I could not produce an answer."
                    ),
                    tool_executions=tuple(
                        executions
                    ),
                )

            for tool_call in response.tool_calls:
                result = self._execute_tool(
                    tool_call.tool_name,
                    tool_call.arguments,
                )

                executions.append(
                    ToolExecution(
                        tool_name=tool_call.tool_name,
                        arguments=tool_call.arguments,
                        result=result,
                    )
                )

                messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            "Requested tool: "
                            f"{tool_call.tool_name}"
                        ),
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "name": tool_call.tool_name,
                        "content": json.dumps(
                            result,
                            default=str,
                        ),
                    }
                )

        return AIControllerResponse(
            answer=(
                "I could not complete the requested "
                "finance investigation within the allowed "
                "tool execution limit."
            ),
            tool_executions=tuple(
                executions
            ),
        )

    def _get_tool_definitions(
        self,
    ) -> list[dict[str, Any]]:
        """
        Obtain tool schemas from the existing ReconAI registry.
        """

        return self.tool_registry.get_tool_definitions()

    def _execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """
        Execute a registered ReconAI tool.

        Unknown tools are rejected rather than executed.
        """

        tool: Callable[..., Any] | None = (
            self.tool_registry.get_tool(
                tool_name
            )
        )

        if tool is None:
            raise ValueError(
                f"Unknown ReconAI tool: {tool_name}"
            )

        return tool(
            **arguments
        )