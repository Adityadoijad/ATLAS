"""Centralized LLM provider for ATLAS.

Every AI call in the app goes through this module — the chatbot, the trip
planner, and destination discovery. Agents never talk to the provider SDK
directly, so swapping providers again later is a change to this file alone.

Provider: Groq (OpenAI-compatible chat completions), model configured via
GROQ_MODEL so it is never hardcoded at call sites.
"""
import asyncio
import json
import logging
import re
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class AIConfigurationError(RuntimeError):
    """The provider is unusable as configured (missing key/SDK, invalid key).
    Not retryable."""


class AIQuotaExceededError(RuntimeError):
    """The provider's own rate limit/quota is exhausted (HTTP 429). Distinct
    from ATLAS's app-level limiter so callers can return a clean 429."""


class AIGenerationError(RuntimeError):
    """Upstream failure that isn't configuration or quota (5xx, network,
    empty response)."""


# Retry only failures that a retry can actually fix. An invalid key or a
# malformed request will fail identically every time.
_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 0.5


def _client():
    try:
        from groq import AsyncGroq
    except ImportError as exc:  # pragma: no cover - dependency is in requirements
        raise AIConfigurationError("The Groq SDK is not installed.") from exc
    if not settings.GROQ_API_KEY:
        raise AIConfigurationError("GROQ_API_KEY is not set.")
    return AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=60.0)


def _classify(exc: Exception) -> Exception:
    """Map provider SDK errors onto ATLAS's provider-neutral error types."""
    try:
        from groq import APIConnectionError, APIStatusError, APITimeoutError
    except ImportError:  # pragma: no cover
        return AIGenerationError(str(exc))

    if isinstance(exc, APIStatusError):
        status = exc.status_code
        if status == 429:
            return AIQuotaExceededError("The AI provider's rate limit is exhausted right now.")
        if status in (401, 403):
            return AIConfigurationError("The AI provider rejected the configured API key.")
        if status == 404:
            # Almost always an unknown/decommissioned GROQ_MODEL. Retrying
            # can't fix it, so fail fast and name the cause.
            return AIConfigurationError(
                f"The AI provider does not recognise model '{settings.GROQ_MODEL}'. "
                "Check GROQ_MODEL against the provider's available models."
            )
        if status == 400:
            return AIGenerationError("The AI provider rejected the request.")
        return AIGenerationError(f"The AI provider returned HTTP {status}.")
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return AIGenerationError("Could not reach the AI provider.")
    return AIGenerationError(str(exc))


def _is_retryable(exc: Exception) -> bool:
    # Quota is retryable in principle, but not on the sub-second timescale of
    # this loop — callers surface it as a 429 instead of burning attempts.
    return isinstance(exc, AIGenerationError)


async def generate(
    prompt: str,
    *,
    system_instruction: str | None = None,
    json_mode: bool = False,
    max_tokens: int = 4000,
    temperature: float = 0.7,
) -> str:
    """Run one completion and return the raw text.

    json_mode asks the provider to guarantee syntactically valid JSON — note
    the provider requires a JSON *object* at the root, so callers wanting a
    list should request an object with a single array key and unwrap it.
    """
    messages: list[dict[str, str]] = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    client = _client()
    model = settings.GROQ_MODEL
    last_error: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        started = time.monotonic()
        try:
            kwargs: dict[str, object] = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = await client.chat.completions.create(**kwargs)
            text = (response.choices[0].message.content or "").strip()
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if not text:
                raise AIGenerationError("The AI provider returned an empty response.")
            logger.info("AI call ok | provider=groq model=%s json=%s latency_ms=%d", model, json_mode, elapsed_ms)
            return text
        except Exception as exc:
            mapped = exc if isinstance(exc, (AIConfigurationError, AIQuotaExceededError, AIGenerationError)) else _classify(exc)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "AI call failed | provider=groq model=%s attempt=%d/%d latency_ms=%d error=%s",
                model, attempt, _MAX_ATTEMPTS, elapsed_ms, type(mapped).__name__,
            )
            if not _is_retryable(mapped) or attempt == _MAX_ATTEMPTS:
                raise mapped from exc
            last_error = mapped
            await asyncio.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    raise last_error or AIGenerationError("The AI provider is temporarily unavailable.")


def extract_json(text: str) -> Any:
    """Parse JSON out of a model response defensively.

    json_mode makes clean JSON the normal case, but models can still wrap it
    in ```json fences or bracket it with prose, so handle those rather than
    letting a stray character fail an otherwise-good plan.

    Raises ValueError when nothing parseable is present — callers must treat
    that as a genuine failure, never substitute fabricated content.
    """
    candidate = (text or "").strip()
    if not candidate:
        raise ValueError("Empty response from the AI provider.")

    fenced = _FENCE_RE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost {...} or [...] span, covering responses that
    # lead with an explanatory sentence.
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = candidate.find(opener), candidate.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start:end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError("The AI provider returned a response that was not valid JSON.")
