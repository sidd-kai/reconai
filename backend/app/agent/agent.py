from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.agent.registry import (
    AgentToolRegistry,
    build_default_registry,
)


@dataclass(frozen=True)
class ToolExecutionResult:
    """
    Result returned after executing an agent tool.
    """

    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None


class FinanceAgent:
    """
    Deterministic finance-controller agent runtime.

    This is intentionally LLM-independent.

    The future LLM will decide which tool to call, but all
    financial facts will continue to come from this registry.
    """

    def __init__(
        self,
        registry: AgentToolRegistry | None = None,
    ) -> None:
        self.registry = (
            registry
            if registry is not None
            else build_default_registry()
        )

    def list_tools(self) -> list[dict[str, str]]:
        """
        Return tool metadata suitable for an LLM tool schema.
        """

        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self.registry.list_tools()
        ]

    def execute_tool(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolExecutionResult:
        """
        Execute one approved finance-controller tool.

        The tool name is always preserved in the execution result so
        callers can audit exactly which deterministic tool was invoked.
        """

        try:
            result = self.registry.execute(
                tool_name,
                **kwargs,
            )

            return ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                result=result,
            )

        except Exception as exc:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=str(exc),
            )