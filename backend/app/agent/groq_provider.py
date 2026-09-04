from __future__ import annotations

import json
import os
import random
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from backend.app.agent.provider import (
    LLMProvider,
    LLMProviderError,
    ModelResponse,
    ToolCall,
)


class GroqProvider(LLMProvider):
    """Groq implementation of the provider-neutral ReconAI contract."""

    DEFAULT_MODEL = "openai/gpt-oss-20b"
    _semaphore = threading.BoundedSemaphore(
        max(1, int(os.getenv("GROQ_MAX_CONCURRENCY", "2")))
    )

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured.")

        self.model = model or os.getenv("GROQ_MODEL", self.DEFAULT_MODEL)
        self.timeout_seconds = float(os.getenv("GROQ_TIMEOUT_SECONDS", "45"))
        self.max_retries = max(0, int(os.getenv("GROQ_MAX_RETRIES", "3")))
        self.backoff_seconds = max(0.0, float(os.getenv("GROQ_BACKOFF_SECONDS", "1")))
        self.client = httpx.Client(
            base_url="https://api.groq.com/openai/v1",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout_seconds,
        )

    def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._messages(messages),
            "temperature": 0,
            "max_completion_tokens": int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", "1024")),
        }
        if tools:
            payload["tools"] = [
                {"type": "function", "function": tool}
                for tool in tools
            ]
            payload["tool_choice"] = "auto"
            payload["parallel_tool_calls"] = False

        try:
            response = self._post_with_retries(payload)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                code = "GROQ_QUOTA_EXCEEDED"
                message = "Groq API rate limit or quota has been exceeded."
            elif status in {503, 504}:
                code = "GROQ_SERVICE_UNAVAILABLE"
                message = "Groq is temporarily unavailable."
            else:
                code = "GROQ_PROVIDER_ERROR"
                message = "Groq provider request failed."
            raise LLMProviderError(message, code=code) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                "Groq provider request failed.",
                code="GROQ_PROVIDER_ERROR",
            ) from exc

        message = response.json()["choices"][0]["message"]
        calls = tuple(
            ToolCall(
                tool_name=call["function"]["name"],
                arguments=json.loads(call["function"].get("arguments") or "{}"),
                call_id=call.get("id"),
            )
            for call in (message.get("tool_calls") or [])
        )
        return ModelResponse(content=message.get("content"), tool_calls=calls)

    @staticmethod
    def _messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for index, message in enumerate(messages):
            role = message.get("role")
            if role == "assistant" and message.get("function_call"):
                call = message["function_call"]
                result.append({
                    "role": "assistant",
                    "content": message.get("content") or None,
                    "tool_calls": [{
                        "id": call.get("call_id") or f"call_{index}",
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call.get("arguments") or {}),
                        },
                    }],
                })
            elif role == "tool":
                result.append({
                    "role": "tool",
                    "tool_call_id": message.get("call_id") or f"call_{index - 1}",
                    "name": message.get("name"),
                    "content": str(message.get("content", "{}")),
                })
            else:
                result.append({"role": role, "content": str(message.get("content", ""))})
        return result

    def _post_with_retries(self, payload: dict[str, Any]) -> httpx.Response:
        with self._semaphore:
            for attempt in range(self.max_retries + 1):
                try:
                    response = self.client.post("/chat/completions", json=payload)
                    response.raise_for_status()
                    return response
                except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                    status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                    if attempt >= self.max_retries or (status is not None and status not in {429, 503, 504}):
                        raise
                    retry_after = self._retry_after(exc.response) if status == 429 else None
                    ceiling = min(30.0, self.backoff_seconds * (2**attempt))
                    time.sleep(retry_after if retry_after is not None else random.uniform(0.0, ceiling))
        raise RuntimeError("Groq retry loop terminated unexpectedly.")

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None
