from __future__ import annotations

import json
import os
import random
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from google import genai
from google.genai import types

from backend.app.agent.provider import (
    LLMProvider,
    LLMProviderError,
    ModelResponse,
    ToolCall,
)


class GeminiProvider(LLMProvider):
    """
    Google Gemini implementation of the provider abstraction.

    Gemini is responsible for:
        - understanding the user's question
        - selecting approved tools
        - generating the final explanation

    ReconAI remains responsible for:
        - reconciliation
        - financial evidence
        - exception classification
        - audit verification

    Automatic Function Calling (AFC) is deliberately disabled.

    Tool execution must always happen inside ReconAI's deterministic
    FinanceAgent / AgentToolRegistry.
    """

    DEFAULT_MODEL = "gemini-3.6-flash"
    DEFAULT_MAX_OUTPUT_TOKENS = 1024
    DEFAULT_TIMEOUT_MS = 45_000
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_SECONDS = 1.0
    DEFAULT_MAX_BACKOFF_SECONDS = 30.0
    DEFAULT_MAX_CONCURRENCY = 2

    _request_semaphore = threading.BoundedSemaphore(
        max(
            1,
            int(
                os.getenv(
                    "GEMINI_MAX_CONCURRENCY",
                    str(DEFAULT_MAX_CONCURRENCY),
                )
            ),
        )
    )

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        resolved_api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
        )

        if not resolved_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )

        self.timeout_ms = int(
            os.getenv(
                "GEMINI_TIMEOUT_MS",
                str(self.DEFAULT_TIMEOUT_MS),
            )
        )

        self.max_retries = max(
            0,
            int(
                os.getenv(
                    "GEMINI_MAX_RETRIES",
                    str(self.DEFAULT_MAX_RETRIES),
                )
            ),
        )

        self.backoff_seconds = max(
            0.0,
            float(
                os.getenv(
                    "GEMINI_BACKOFF_SECONDS",
                    str(self.DEFAULT_BACKOFF_SECONDS),
                )
            ),
        )

        self.client = genai.Client(
            api_key=resolved_api_key,
            http_options=types.HttpOptions(
                timeout=self.timeout_ms,
            ),
        )

        self.model = (
            model
            or os.getenv(
                "GEMINI_MODEL",
                self.DEFAULT_MODEL,
            )
        )

        self.max_output_tokens = int(
            os.getenv(
                "GEMINI_MAX_OUTPUT_TOKENS",
                str(self.DEFAULT_MAX_OUTPUT_TOKENS),
            )
        )

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        """
        Generate one provider-independent response.

        Automatic function calling is disabled deliberately.

        Gemini may request a function, but ReconAI executes the
        requested function through its deterministic registry.
        """

        system_instruction = ""

        contents: list[types.Content] = []

        for message in messages:
            role = message.get("role")

            if role == "system":
                system_instruction = str(
                    message.get("content", "")
                )
                continue

            if role == "user":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(
                                text=str(
                                    message.get(
                                        "content",
                                        "",
                                    )
                                )
                            )
                        ],
                    )
                )
                continue

            if role == "assistant":
                contents.append(
                    self._build_model_message(
                        message
                    )
                )
                continue

            if role == "tool":
                contents.append(
                    self._build_tool_response_message(
                        message
                    )
                )
                continue

        function_declarations = [
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters_json_schema=tool.get(
                    "parameters",
                    {
                        "type": "object",
                        "properties": {},
                    },
                ),
            )
            for tool in tools
        ]

        tool_config = (
            types.Tool(
                function_declarations=function_declarations
            )
            if function_declarations
            else None
        )

        try:
            response = self._generate_with_retries(
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=(
                        [tool_config]
                        if tool_config is not None
                        else None
                    ),
                    temperature=0.0,
                    max_output_tokens=self.max_output_tokens,
                    automatic_function_calling=(
                        types.AutomaticFunctionCallingConfig(
                            disable=True
                        )
                    ),
                ),
            )

        except Exception as exc:
            status_code = getattr(
                exc,
                "status_code",
                getattr(exc, "code", None),
            )

            error_text = str(exc).upper()
            status_text = str(status_code)

            if (
                status_code == 429
                or "429" in status_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "QUOTA" in error_text
            ):
                raise LLMProviderError(
                    "Gemini API quota has been exceeded.",
                    code="GEMINI_QUOTA_EXCEEDED",
                ) from exc

            if (
                status_code in {503, 504}
                or "UNAVAILABLE" in error_text
                or "GATEWAY_TIMEOUT" in error_text
            ):
                raise LLMProviderError(
                    "Gemini service is temporarily unavailable.",
                    code="GEMINI_SERVICE_UNAVAILABLE",
                ) from exc

            if (
                status_code == 404
                or "NOT_FOUND" in error_text
            ):
                raise LLMProviderError(
                    f"Gemini model '{self.model}' is unavailable.",
                    code="GEMINI_MODEL_NOT_FOUND",
                ) from exc

            raise LLMProviderError(
                "Gemini provider request failed.",
                code="GEMINI_PROVIDER_ERROR",
            ) from exc

        return self._parse_response(response)

    def _generate_with_retries(
        self,
        *,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> Any:
        """Call Gemini with bounded concurrency and transient retries."""

        with self._request_semaphore:
            for attempt in range(self.max_retries + 1):
                try:
                    return self.client.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=config,
                    )
                except Exception as exc:
                    if (
                        attempt >= self.max_retries
                        or not self._is_retryable(exc)
                    ):
                        raise

                    retry_after = self._retry_after_seconds(exc)

                    if retry_after is not None:
                        delay = retry_after
                    else:
                        ceiling = min(
                            self.DEFAULT_MAX_BACKOFF_SECONDS,
                            self.backoff_seconds * (2**attempt),
                        )
                        delay = random.uniform(0.0, ceiling)

                    time.sleep(delay)

        raise RuntimeError("Gemini retry loop terminated unexpectedly.")

    @staticmethod
    def _status_code(exc: Exception) -> int | None:
        raw_status = getattr(
            exc,
            "status_code",
            getattr(exc, "code", None),
        )

        try:
            return int(raw_status)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _is_retryable(cls, exc: Exception) -> bool:
        status_code = cls._status_code(exc)

        if status_code in {429, 503, 504}:
            return True

        error_name = type(exc).__name__.lower()
        error_text = str(exc).lower()

        return (
            "timeout" in error_name
            or "connection" in error_name
            or "timed out" in error_text
            or "temporarily unavailable" in error_text
        )

    @staticmethod
    def _retry_after_seconds(exc: Exception) -> float | None:
        if GeminiProvider._status_code(exc) != 429:
            return None

        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", None)

        if headers is None:
            return None

        value = headers.get("Retry-After")

        if not value:
            return None

        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            pass

        try:
            retry_at = parsedate_to_datetime(str(value))

            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)

            return max(
                0.0,
                (retry_at - datetime.now(timezone.utc)).total_seconds(),
            )
        except (TypeError, ValueError, OverflowError):
            return None

    def _build_model_message(
        self,
        message: dict[str, Any],
    ) -> types.Content:
        """
        Reconstruct a previous Gemini model response.

        The runtime may provide either normal model text or an
        explicit function call payload.
        """

        parts: list[types.Part] = []

        content = message.get("content")

        if content:
            parts.append(
                types.Part.from_text(
                    text=str(content)
                )
            )

        function_call = message.get(
            "function_call"
        )

        if function_call:
            name = function_call.get("name")

            arguments = function_call.get(
                "arguments",
                {},
            )

            if name:
                parts.append(
                    types.Part.from_function_call(
                        name=name,
                        args=arguments,
                    )
                )

        return types.Content(
            role="model",
            parts=parts,
        )

    def _build_tool_response_message(
        self,
        message: dict[str, Any],
    ) -> types.Content:
        """
        Convert a ReconAI tool result into Gemini's structured
        function-response format.

        This prevents tool output from being represented as
        ordinary user text.
        """

        tool_name = str(
            message.get(
                "name",
                "unknown_tool",
            )
        )

        raw_content = message.get(
            "content",
            "{}",
        )

        try:
            response_payload = json.loads(
                raw_content
            )
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            response_payload = {
                "raw": str(raw_content)
            }

        return types.Content(
            role="user",
            parts=[
                types.Part.from_function_response(
                    name=tool_name,
                    response=response_payload,
                )
            ],
        )

    def _parse_response(
        self,
        response: Any,
    ) -> ModelResponse:
        """
        Convert Gemini's response into the provider-neutral
        ModelResponse contract.

        Function calls are extracted explicitly rather than
        relying on response.text, which may emit warnings when
        non-text parts are present.
        """

        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []

        candidates = getattr(
            response,
            "candidates",
            None,
        ) or []

        for candidate in candidates:
            content = getattr(
                candidate,
                "content",
                None,
            )

            if content is None:
                continue

            parts = getattr(
                content,
                "parts",
                None,
            ) or []

            for part in parts:
                function_call = getattr(
                    part,
                    "function_call",
                    None,
                )

                if function_call is not None:
                    name = getattr(
                        function_call,
                        "name",
                        None,
                    )

                    arguments = getattr(
                        function_call,
                        "args",
                        None,
                    )

                    if name:
                        tool_calls.append(
                            ToolCall(
                                tool_name=name,
                                arguments=dict(
                                    arguments or {}
                                ),
                            )
                        )

                    continue

                text = getattr(
                    part,
                    "text",
                    None,
                )

                if text:
                    text_parts.append(text)

        return ModelResponse(
            content=(
                "\n".join(
                    text_parts
                ).strip()
                or None
            ),
            tool_calls=tuple(
                tool_calls
            ),
        )
