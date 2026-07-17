from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any

import litellm
from redis import asyncio as redis_asyncio

from app.ai.guardrails import SAFETY_PREAMBLE
from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Provider errors are handled explicitly per-candidate (fallback chain) —
# don't let litellm raise on a param one provider doesn't support.
litellm.drop_params = True
litellm.suppress_debug_info = True


class LLMUnavailableError(Exception):
    """No configured/reachable provider could complete the request."""


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    model: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int
    cached: bool = False


@dataclass(frozen=True)
class _ProviderConfig:
    provider: str
    model: str
    litellm_model: str
    api_key: str | None
    api_base: str | None


def _provider_configs(settings: Settings) -> list[_ProviderConfig]:
    """Free-first fallback chain: NVIDIA NIM -> Groq -> OpenRouter -> Ollama.
    Cloud providers are only attempted if a key is configured; Ollama has no
    key requirement and is attempted last, failing over to the next (none)
    on a connection error if no local daemon/model is available."""
    configs = []
    if settings.nvidia_nim_api_key:
        configs.append(
            _ProviderConfig(
                provider="nvidia_nim",
                model=settings.nvidia_nim_model,
                # NIM is OpenAI-compatible — proxy through litellm's generic
                # "openai" provider with a custom base rather than depending
                # on a litellm-version-specific "nvidia_nim" provider name.
                litellm_model=f"openai/{settings.nvidia_nim_model}",
                api_key=settings.nvidia_nim_api_key,
                api_base="https://integrate.api.nvidia.com/v1",
            )
        )
    if settings.groq_api_key:
        configs.append(
            _ProviderConfig(
                provider="groq",
                model=settings.groq_model,
                litellm_model=f"groq/{settings.groq_model}",
                api_key=settings.groq_api_key,
                api_base=None,
            )
        )
    if settings.openrouter_api_key:
        configs.append(
            _ProviderConfig(
                provider="openrouter",
                model=settings.openrouter_model,
                litellm_model=f"openrouter/{settings.openrouter_model}",
                api_key=settings.openrouter_api_key,
                api_base=None,
            )
        )
    configs.append(
        _ProviderConfig(
            provider="ollama",
            model=settings.ollama_model,
            litellm_model=f"ollama/{settings.ollama_model}",
            api_key=None,
            api_base=settings.ollama_base_url,
        )
    )
    return configs


class AIRouter:
    """Provider-agnostic LLM entrypoint. Tries each configured free provider
    in order and falls back to the next on any failure (missing key,
    timeout, rate limit, connection refused), so one flaky/unset provider
    never breaks an AI feature — it just degrades to the next-best option,
    or raises LLMUnavailableError if every option is exhausted."""

    def __init__(self) -> None:
        self._redis: redis_asyncio.Redis | None = None

    async def _cache(self) -> redis_asyncio.Redis:
        if self._redis is None:
            self._redis = redis_asyncio.from_url(
                get_settings().redis_url, decode_responses=True
            )
        return self._redis

    @staticmethod
    def _cache_key(system: str, user: str, json_mode: bool) -> str:
        digest = hashlib.sha256(f"{system}|{user}|{json_mode}".encode()).hexdigest()
        return f"ai:completion:{digest}"

    @staticmethod
    async def _complete_with_retry(provider: str, kwargs: dict[str, Any]) -> Any:
        """One immediate retry on the same provider before giving up on it —
        free-tier providers occasionally blip (a fast-failing timeout/connection
        error unrelated to actual reachability), and a single retry is enough
        to ride those out without falling through to a lower-priority provider."""
        try:
            return await litellm.acompletion(**kwargs)
        except Exception as exc:
            logger.warning("ai.provider_retry", provider=provider, error=str(exc))
            await asyncio.sleep(0.5)
            return await litellm.acompletion(**kwargs)

    async def complete(
        self,
        *,
        user: str,
        system: str = SAFETY_PREAMBLE,
        json_mode: bool = False,
        max_tokens: int = 900,
    ) -> LLMResponse:
        settings = get_settings()
        cache = await self._cache()
        cache_key = self._cache_key(system, user, json_mode)

        cached_raw = await cache.get(cache_key)
        if cached_raw:
            data = json.loads(cached_raw)
            return LLMResponse(**data, cached=True)

        errors: list[str] = []
        for cfg in _provider_configs(settings):
            started = time.monotonic()
            try:
                kwargs: dict[str, Any] = {
                    "model": cfg.litellm_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "timeout": settings.ai_request_timeout_seconds,
                }
                if cfg.api_key:
                    kwargs["api_key"] = cfg.api_key
                if cfg.api_base:
                    kwargs["api_base"] = cfg.api_base
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = await self._complete_with_retry(cfg.provider, kwargs)
            except Exception as exc:  # noqa: BLE001 — any provider failure falls through
                errors.append(f"{cfg.provider}: {exc}")
                logger.warning("ai.provider_failed", provider=cfg.provider, error=str(exc))
                continue

            latency_ms = int((time.monotonic() - started) * 1000)
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            result = LLMResponse(
                content=content,
                provider=cfg.provider,
                model=cfg.model,
                tokens_in=getattr(usage, "prompt_tokens", None),
                tokens_out=getattr(usage, "completion_tokens", None),
                latency_ms=latency_ms,
            )
            await cache.set(
                cache_key,
                json.dumps({k: v for k, v in asdict(result).items() if k != "cached"}),
                ex=settings.ai_cache_ttl_seconds,
            )
            return result

        raise LLMUnavailableError(
            "No AI provider available — configure a free NVIDIA NIM/Groq/OpenRouter key "
            f"or run Ollama locally. Attempts: {'; '.join(errors)}"
        )


_router: AIRouter | None = None


def get_ai_router() -> AIRouter:
    global _router
    if _router is None:
        _router = AIRouter()
    return _router
