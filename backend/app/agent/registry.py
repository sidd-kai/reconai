from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class AgentTool:
    """
    Registered tool available to the finance-controller agent.
    """

    name: str
    description: str
    function: Callable[..., Any]


class AgentToolRegistry:
    """
    Central registry for deterministic finance-controller tools.

    Only explicitly registered functions can be executed by
    the agent.
    """

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(
        self,
        tool: AgentTool,
    ) -> None:
        """
        Register one approved agent tool.
        """
        if tool.name in self._tools:
            raise ValueError(
                f"Tool already registered: {tool.name}"
            )

        self._tools[tool.name] = tool

    def get(
        self,
        name: str,
    ) -> AgentTool:
        """
        Retrieve a registered tool by name.
        """
        try:
            return self._tools[name]

        except KeyError as exc:
            raise ValueError(
                f"Unknown agent tool: {name}"
            ) from exc

    def list_tools(self) -> tuple[AgentTool, ...]:
        """
        Return all registered tools.
        """
        return tuple(
            self._tools.values()
        )

    def execute(
        self,
        name: str,
        **kwargs: Any,
    ) -> Any:
        """
        Execute an approved registered tool.
        """
        tool = self.get(name)

        return tool.function(
            **kwargs
        )

    def has(
        self,
        name: str,
    ) -> bool:
        """
        Check whether a tool is registered.
        """
        return name in self._tools


def build_default_registry() -> AgentToolRegistry:
    """
    Build the approved finance-controller tool registry.
    """

    from backend.app.agent.tools import (
        get_audit_record_count,
        get_batch_summary,
        get_exception_manifest,
        get_finance_ops_summary,
        get_high_value_exceptions,
        investigate_exception,
        reconcile_batch,
        verify_audit_chain_tool,
    )

    registry = AgentToolRegistry()

    registry.register(
        AgentTool(
            name="reconcile_batch",
            description=(
                "Inspect the current reconciliation batch "
                "and return deterministic reconciliation "
                "counts and status breakdown."
            ),
            function=reconcile_batch,
        )
    )

    registry.register(
        AgentTool(
            name="get_batch_summary",
            description=(
                "Return the current finance-controller "
                "batch summary including match rate, "
                "exception rate, exception breakdown, "
                "and audit verification."
            ),
            function=get_batch_summary,
        )
    )

    registry.register(
        AgentTool(
            name="get_exception_manifest",
            description=(
                "Return the current exception manifest. "
                "Historical duplicate exception events "
                "are reduced to the latest state for "
                "each transaction."
            ),
            function=get_exception_manifest,
        )
    )

    registry.register(
        AgentTool(
            name="investigate_exception",
            description=(
                "Investigate one transaction using "
                "deterministic reconciliation evidence. "
                "Requires transaction_id."
            ),
            function=investigate_exception,
        )
    )

    registry.register(
        AgentTool(
            name="get_finance_ops_summary",
            description=(
                "Return a deterministic finance-operations "
                "attention summary including match rate, "
                "exception rate, audit verification, and "
                "the highest-value unresolved exceptions. "
                "Accepts an optional limit."
            ),
            function=get_finance_ops_summary,
        )
    )

    registry.register(
        AgentTool(
            name="get_high_value_exceptions",
            description=(
                "Return current exceptions ordered by "
                "absolute financial amount difference. "
                "Accepts an optional limit."
            ),
            function=get_high_value_exceptions,
        )
    )

    registry.register(
        AgentTool(
            name="get_audit_record_count",
            description=(
                "Return the number of non-empty immutable "
                "audit records currently stored."
            ),
            function=get_audit_record_count,
        )
    )

    registry.register(
        AgentTool(
            name="verify_audit_chain",
            description=(
                "Cryptographically verify the immutable "
                "audit hash chain and return verification "
                "status."
            ),
            function=verify_audit_chain_tool,
        )
    )

    return registry