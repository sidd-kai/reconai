from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    """
    Model-requested tool invocation.
    """

    tool_name: str
    arguments: dict[str, Any]
    call_id: str | None = None


@dataclass(frozen=True)
class ModelResponse:
    """
    Provider-independent model response.

    The model may either return normal text or request
    one or more registered tools.
    """

    content: str | None
    tool_calls: tuple[ToolCall, ...]


class LLMProvider(ABC):
    """
    Provider-independent interface for the finance agent.

    Implementations may use OpenAI, Gemini, Anthropic, or
    another model provider without changing the finance logic.
    """

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        """
        Generate a model response using the supplied messages
        and tool definitions.
        """
        raise NotImplementedError


class LLMProviderError(RuntimeError):
    """
    Controlled error raised when an LLM provider cannot
    complete a request.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "LLM_PROVIDER_ERROR",
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)

        self.code = code
        self.retry_after_seconds = retry_after_seconds
