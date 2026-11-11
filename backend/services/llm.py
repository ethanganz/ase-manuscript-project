"""Ask a large language model (Gemini) a question, and report limits clearly.

Everything else in the app talks to the small ``LLM`` interface, never to Gemini
directly. That keeps the rest of the code simple and lets tests use ``FakeLLM``.

Two kinds of failure are reported, so the API can answer each one properly:

* ``LLMRateLimited``: Gemini said the usage limit is reached. It carries how many
  seconds to wait. The limit belongs to our one API key, so it is shared by all users.
* ``LLMUnavailable``: anything else (not configured, key refused, server error,
  timeout, empty answer). Its message is safe to show to a user. The technical
  detail is written to the log only.

Manual check with a real key (run from the ``backend`` folder)::

    python -m services.llm "Say hello in Latin"
"""
from __future__ import annotations

import logging
import math
import re
import sys
import threading
import time
from functools import lru_cache
from typing import Any, Callable, Protocol

from google import genai
from google.genai import errors, types

import config

logger = logging.getLogger(__name__)

_RATE_LIMIT_STATUS = 429
_RETRY_IN_TEXT = re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.IGNORECASE)
_DURATION = re.compile(r"^(\d+(?:\.\d+)?)s$")


class LLMError(Exception):
    """Base class for all errors raised by this module."""


class LLMRateLimited(LLMError):
    """The usage limit is reached. Try again after ``retry_after_seconds``."""

    def __init__(self, retry_after_seconds: int, daily: bool = False) -> None:
        super().__init__(f"LLM rate limit reached; retry in {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds
        self.daily = daily  # True when the daily allowance, not the per-minute one, is used up


class LLMUnavailable(LLMError):
    """The model could not answer. ``str(error)`` is safe to show to a user."""


class LLM(Protocol):
    def generate(self, system: str, prompt: str) -> str:
        """Return the model's answer to ``prompt``, guided by the ``system`` instruction."""


def _error_items(details: Any) -> list[dict]:
    """The list of extra error records inside Gemini's error response, if present."""
    if not isinstance(details, dict):
        return []
    items = (details.get("error") or {}).get("details")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def parse_retry_after(error: errors.APIError) -> int | None:
    """Seconds to wait according to Gemini, rounded up, or None when it does not say."""
    for item in _error_items(error.details):
        if str(item.get("@type", "")).endswith("RetryInfo"):
            match = _DURATION.match(str(item.get("retryDelay", "")))
            if match:
                return max(1, math.ceil(float(match.group(1))))
    match = _RETRY_IN_TEXT.search(str(error.message or ""))  # e.g. "Please retry in 12.3s."
    if match:
        return max(1, math.ceil(float(match.group(1))))
    return None


def is_daily_limit(error: errors.APIError) -> bool:
    """Best guess whether the per-day allowance (not the per-minute one) is used up.

    This reads the quota name in the error, for example "...PerDay...". If Gemini
    changes the wording the guess is False, and the user simply sees a wait time.
    """
    for item in _error_items(error.details):
        for violation in item.get("violations", []) or []:
            if isinstance(violation, dict) and "perday" in str(violation.get("quotaId", "")).lower():
                return True
    return False


class GeminiLLM:
    """``LLM`` backed by the Gemini API."""

    def __init__(self, api_key: str, model: str, timeout_seconds: int = 30,
                 default_retry_seconds: int = 60, client: Any = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._model = model
        self._default_retry = default_retry_seconds
        self._clock = clock
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000,  # milliseconds
                # One attempt only. The library would otherwise retry on its own,
                # which wastes the limited number of requests.
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        # While Gemini says "wait", do not even ask it again.
        self._lock = threading.Lock()
        self._blocked_until = 0.0
        self._blocked_daily = False

    def generate(self, system: str, prompt: str) -> str:
        self._raise_if_blocked()
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system, temperature=0),
            )
        except errors.APIError as error:
            if error.code == _RATE_LIMIT_STATUS:
                raise self._start_block(error) from error
            logger.error("Gemini request failed: %s %s %s", error.code, error.status, error.message)
            raise LLMUnavailable("The AI service is not available right now.") from error
        except Exception as error:  # network problems, timeouts, anything unexpected
            logger.exception("Gemini request failed unexpectedly")
            raise LLMUnavailable("The AI service is not available right now.") from error

        text = (response.text or "").strip()
        if not text:
            logger.error("Gemini returned no text (blocked or empty answer)")
            raise LLMUnavailable("The AI service gave no answer. Try rephrasing the question.")
        return text

    def _start_block(self, error: errors.APIError) -> LLMRateLimited:
        seconds = parse_retry_after(error) or self._default_retry
        daily = is_daily_limit(error)
        with self._lock:
            self._blocked_until = self._clock() + seconds
            self._blocked_daily = daily
        logger.warning("Gemini rate limit reached; waiting %ss (daily=%s)", seconds, daily)
        return LLMRateLimited(seconds, daily)

    def _raise_if_blocked(self) -> None:
        with self._lock:
            remaining = self._blocked_until - self._clock()
            daily = self._blocked_daily
        if remaining > 0:
            raise LLMRateLimited(max(1, math.ceil(remaining)), daily)


class FakeLLM:
    """Stand-in for tests: returns ``reply`` or raises ``error`` and records the calls."""

    def __init__(self, reply: str = "fake answer", error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        if self.error is not None:
            raise self.error
        return self.reply


@lru_cache(maxsize=1)
def default_llm() -> LLM:
    """The one shared Gemini client. It must be shared so the "wait" window is shared too."""
    if not config.GEMINI_API_KEY or not config.GEMINI_MODEL:
        logger.error("GEMINI_API_KEY or GEMINI_MODEL is not set")
        raise LLMUnavailable("The AI service is not configured.")
    return GeminiLLM(
        api_key=config.GEMINI_API_KEY,
        model=config.GEMINI_MODEL,
        timeout_seconds=config.LLM_TIMEOUT_SECONDS,
        default_retry_seconds=config.LLM_DEFAULT_RETRY_SECONDS,
    )


def main(argv: list[str] | None = None) -> int:
    """Send one prompt to the real model. For checking the key and model name by hand."""
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print('usage: python -m services.llm "your prompt"')
        return 2
    try:
        print(default_llm().generate("Answer briefly.", " ".join(args)))
    except LLMRateLimited as error:
        print(f"Limit reached. Wait {error.retry_after_seconds} seconds."
              + (" (daily limit)" if error.daily else ""))
        return 3
    except LLMUnavailable as error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())