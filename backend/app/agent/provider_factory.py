from __future__ import annotations

import os

from backend.app.agent.gemini_provider import GeminiProvider
from backend.app.agent.groq_provider import GroqProvider
from backend.app.agent.provider import LLMProvider


def configured_provider_name() -> str | None:
    requested = os.getenv("LLM_PROVIDER", "").strip().lower()
    if requested == "groq" and os.getenv("GROQ_API_KEY"):
        return "groq"
    if requested == "gemini" and os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return None


def create_llm_provider() -> LLMProvider:
    provider_name = configured_provider_name()
    if provider_name == "groq":
        return GroqProvider()
    if provider_name == "gemini":
        return GeminiProvider()
    raise ValueError("No supported LLM provider is configured.")
