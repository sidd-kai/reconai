from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from backend.app.agent.agent import (
    FinanceAgent,
    ToolExecutionResult,
)
from backend.app.agent.provider import (
    LLMProvider,
    LLMProviderError,
    ModelResponse,
)
from backend.app.agent.intent_router import FinanceIntentRouter


SYSTEM_PROMPT = """
You are ReconAI, an AI Finance Controller.

Your job is to help finance operations teams investigate
reconciliation batches across Payments, Merchant Ledger,
and Settlements.

CRITICAL FINANCE SAFETY RULES:

1. Never invent financial facts.
2. Never infer a financial value that is not present in
   deterministic tool output.
3. Use registered tools whenever financial evidence is required.
4. Treat deterministic reconciliation results as authoritative.
5. Never claim an exception is resolved unless a trusted
   deterministic tool explicitly reports it as resolved.
6. Never modify financial records.
7. Never modify or delete audit records.
8. If evidence is insufficient, explicitly say so.
9. When discussing metrics, state the denominator clearly.
10. Distinguish between:
    - operational resolution rate
    - benchmark match/accuracy
    - precision
    - recall
11. For exception investigations, explain the evidence and
    recommend an action rather than silently resolving the issue.
12. Audit-chain status must come from the audit verification tool.

You are an investigation and reasoning layer over trusted
finance tools, not the reconciliation engine itself.
""".strip()


@dataclass(frozen=True)
class AgentResponse:
    """
    Final response produced by the finance agent.

    tool_executions contains the exact deterministic tool
    execution records produced during this interaction.
    """

    content: str
    tool_calls_executed: int
    tool_executions: tuple[ToolExecutionResult, ...] = ()


class FinanceAgentRuntime:
    """
    LLM-backed runtime for ReconAI.

    Gemini is used only for:
        - understanding the user's request
        - selecting an approved deterministic tool
        - optionally explaining the returned evidence

    Financial truth remains entirely inside the deterministic
    FinanceAgent / AgentToolRegistry layer.

    The runtime is deliberately designed to minimize LLM usage:
        - one Gemini request is normally enough for tool selection
        - tool execution never calls Gemini
        - evaluation-style workflows can stop after tool selection
        - multi-round reasoning is bounded
    """

    def __init__(
        self,
        provider: LLMProvider,
        agent: FinanceAgent | None = None,
        max_tool_rounds: int = 2,
        generate_final_answer: bool = False,
    ) -> None:
        if max_tool_rounds <= 0:
            raise ValueError(
                "max_tool_rounds must be greater than zero."
            )

        self.provider = provider
        self.agent = (
            agent
            if agent is not None
            else FinanceAgent()
        )
        self.max_tool_rounds = max_tool_rounds
        self.generate_final_answer = generate_final_answer

    def _build_tool_schemas(
        self,
    ) -> list[dict[str, Any]]:
        """
        Convert registry metadata into provider-neutral
        tool definitions.

        Argument schemas are intentionally conservative.
        """

        schemas: list[dict[str, Any]] = []

        for tool in self.agent.registry.list_tools():
            parameters: dict[str, Any] = {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            }

            if tool.name == "investigate_exception":
                parameters["properties"] = {
                    "transaction_id": {
                        "type": "string",
                        "description": (
                            "Transaction identifier to investigate."
                        ),
                    },
                }

                parameters["required"] = [
                    "transaction_id"
                ]

            elif tool.name == "get_high_value_exceptions":
                parameters["properties"] = {
                    "limit": {
                        "type": "integer",
                        "description": (
                            "Maximum number of exceptions to return."
                        ),
                        "minimum": 1,
                        "maximum": 100,
                    },
                }

            schemas.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters,
                }
            )

        return schemas

    def _execute_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolExecutionResult:
        """
        Execute exactly one model-requested tool.

        The model never executes financial logic directly.
        Everything passes through the deterministic registry.
        """

        execution = self.agent.execute_tool(
            tool_name,
            **arguments,
        )

        return execution

    def _serialize_tool_result(
        self,
        execution: ToolExecutionResult,
    ) -> dict[str, Any]:
        """
        Convert a ToolExecutionResult into JSON-safe data.
        """

        if not execution.success:
            return {
                "success": False,
                "tool_name": execution.tool_name,
                "error": execution.error,
            }

        payload = execution.result

        if hasattr(payload, "__dataclass_fields__"):
            payload = asdict(payload)

        return {
            "success": True,
            "tool_name": execution.tool_name,
            "result": payload,
        }

    def _build_initial_messages(
        self,
        user_message: str,
    ) -> list[dict[str, Any]]:
        """
        Build the minimal initial prompt.

        Keeping this context small is important for both
        latency and quota consumption.
        """

        return [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

    def _build_tool_result_message(
        self,
        execution: ToolExecutionResult,
        call_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Build a provider-neutral tool-result message.
        """

        tool_result = self._serialize_tool_result(
            execution
        )

        return {
            "role": "tool",
            "name": execution.tool_name,
            "call_id": call_id,
            "content": json.dumps(
                tool_result,
                default=str,
            ),
        }

    def _format_deterministic_answer(
        self,
        execution: ToolExecutionResult,
    ) -> str:
        """
        Produce a safe fallback answer without another LLM call.

        This is intentionally generic. It never interprets or
        invents financial facts.
        """

        if not execution.success:
            return (
                "The requested deterministic finance tool "
                "could not complete successfully. "
                f"Error: {execution.error}"
            )

        payload = execution.result

        if hasattr(payload, "__dataclass_fields__"):
            payload = asdict(payload)

        return (
            "The deterministic finance tool "
            f"'{execution.tool_name}' completed successfully. "
            "Authoritative evidence:\n"
            f"{json.dumps(payload, indent=2, default=str)}"
        )

    def run(
        self,
        user_message: str,
    ) -> AgentResponse:
        """
        Run one finance-controller interaction.

        Default behavior is intentionally quota-efficient:

            Gemini request
                ↓
            tool selection
                ↓
            deterministic execution
                ↓
            return result

        A second Gemini request is only made when
        generate_final_answer=True.
        """

        if not user_message.strip():
            raise ValueError(
                "user_message cannot be empty."
            )

        messages = self._build_initial_messages(
            user_message.strip()
        )

        tool_schemas = self._build_tool_schemas()

        # Resolve obvious finance intents locally. This preserves an LLM
        # explanation while avoiding a separate Gemini call just to choose
        # a tool, which is especially important on request-limited tiers.
        routed_intent = FinanceIntentRouter().route(user_message)

        if (
            routed_intent is not None
            and self.generate_final_answer
        ):
            execution = self._execute_tool_call(
                tool_name=routed_intent.tool_name,
                arguments=routed_intent.arguments,
            )

            evidence = self._serialize_tool_result(execution)
            explanation_messages = [
                {
                    "role": "system",
                    "content": (
                        f"{SYSTEM_PROMPT}\n\n"
                        "Explain the supplied deterministic evidence "
                        "concisely. Do not request another tool and do "
                        "not introduce facts absent from the evidence."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User request:\n{user_message}\n\n"
                        "Authoritative deterministic evidence:\n"
                        f"{json.dumps(evidence, default=str)}"
                    ),
                },
            ]

            try:
                explanation = self.provider.generate(
                    messages=explanation_messages,
                    tools=[],
                )
            except LLMProviderError as exc:
                return AgentResponse(
                    content=(
                        "AI reasoning is temporarily unavailable. "
                        "The deterministic finance tool still completed. "
                        f"{exc.code}: {exc}"
                    ),
                    tool_calls_executed=1,
                    tool_executions=(execution,),
                )

            return AgentResponse(
                content=(
                    explanation.content
                    or self._format_deterministic_answer(execution)
                ),
                tool_calls_executed=1,
                tool_executions=(execution,),
            )

        executed_tool_calls = 0

        tool_executions: list[
            ToolExecutionResult
        ] = []

        for round_number in range(
            self.max_tool_rounds
        ):
            try:
                response: ModelResponse = (
                    self.provider.generate(
                        messages=messages,
                        tools=tool_schemas,
                    )
                )

            except LLMProviderError as exc:
                return AgentResponse(
                    content=(
                        "AI reasoning is temporarily unavailable. "
                        "No financial conclusion was generated. "
                        f"{exc.code}: {exc}"
                    ),
                    tool_calls_executed=executed_tool_calls,
                    tool_executions=tuple(
                        tool_executions
                    ),
                )

            # ---------------------------------------------------------
            # CASE 1:
            # The model answered without requesting a tool.
            # ---------------------------------------------------------

            if not response.tool_calls:
                return AgentResponse(
                    content=(
                        response.content
                        or "The model returned no response."
                    ),
                    tool_calls_executed=executed_tool_calls,
                    tool_executions=tuple(
                        tool_executions
                    ),
                )

            # ---------------------------------------------------------
            # CASE 2:
            # Execute every requested tool deterministically.
            # ---------------------------------------------------------

            for tool_call in response.tool_calls:
                executed_tool_calls += 1

                execution = self._execute_tool_call(
                    tool_name=tool_call.tool_name,
                    arguments=tool_call.arguments,
                )

                tool_executions.append(
                    execution
                )

                # -----------------------------------------------------
                # IMPORTANT QUOTA OPTIMIZATION
                #
                # In normal operation we do NOT immediately call Gemini
                # again after a successful deterministic tool.
                #
                # The tool result itself is authoritative and can be
                # returned directly. This prevents every user question
                # from becoming a two-request Gemini interaction.
                # -----------------------------------------------------

                if not self.generate_final_answer:
                    continue

                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or "",
                        "function_call": {
                            "name": tool_call.tool_name,
                            "arguments": tool_call.arguments,
                            "call_id": tool_call.call_id,
                        },
                    }
                )

                messages.append(
                    self._build_tool_result_message(
                        execution,
                        call_id=tool_call.call_id,
                    )
                )

            # ---------------------------------------------------------
            # Default mode:
            # stop immediately after deterministic execution.
            #
            # This means one Gemini request per user interaction.
            # ---------------------------------------------------------

            if not self.generate_final_answer:
                if len(tool_executions) == 1:
                    execution = tool_executions[0]

                    return AgentResponse(
                        content=(
                            self._format_deterministic_answer(
                                execution
                            )
                        ),
                        tool_calls_executed=(
                            executed_tool_calls
                        ),
                        tool_executions=tuple(
                            tool_executions
                        ),
                    )

                return AgentResponse(
                    content=(
                        "The requested deterministic finance tools "
                        "completed successfully."
                    ),
                    tool_calls_executed=(
                        executed_tool_calls
                    ),
                    tool_executions=tuple(
                        tool_executions
                    ),
                )

            # ---------------------------------------------------------
            # Optional final-answer mode.
            #
            # Only enabled when the application explicitly wants
            # Gemini to convert deterministic evidence into natural
            # language.
            # ---------------------------------------------------------

            if round_number + 1 >= self.max_tool_rounds:
                break

        return AgentResponse(
            content=(
                "The investigation exceeded the maximum "
                "number of allowed tool rounds."
            ),
            tool_calls_executed=executed_tool_calls,
            tool_executions=tuple(
                tool_executions
            ),
        )
