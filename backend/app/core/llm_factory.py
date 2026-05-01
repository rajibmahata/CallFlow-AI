"""
LLM factory — returns a configured LangChain ChatOpenAI instance
for either OpenAI GPT-4o or DeepSeek (OpenAI-compatible API).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from langchain_openai import ChatOpenAI

from app.config import settings

LLMProviderLiteral = Literal["openai", "deepseek"]


def get_llm(
    provider: LLMProviderLiteral | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> ChatOpenAI:
    """
    Return a configured ChatOpenAI-compatible LLM instance.

    Args:
        provider: "openai" or "deepseek". Defaults to settings.DEFAULT_LLM_PROVIDER.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens.

    Returns:
        ChatOpenAI instance usable by LangChain/CrewAI.
    """
    resolved = provider or settings.default_llm_provider

    if resolved == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. Add it to your .env file."
            )
        return ChatOpenAI(
            api_key=settings.deepseek_api_key,  # type: ignore[arg-type]
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # Default: OpenAI
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to your .env file."
        )
    return ChatOpenAI(
        api_key=settings.openai_api_key,  # type: ignore[arg-type]
        model=settings.openai_model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


@lru_cache(maxsize=4)
def get_cached_llm(provider: str, temperature_x10: int = 3) -> ChatOpenAI:
    """
    Cached LLM instance (avoids re-instantiating per request).
    temperature_x10 = int(temperature * 10) — hashable for lru_cache.
    """
    return get_llm(provider=provider, temperature=temperature_x10 / 10)  # type: ignore[arg-type]
