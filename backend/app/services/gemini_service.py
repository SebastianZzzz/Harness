"""
GeminiService: wraps the existing GeminiClient for use inside the FastAPI app.
Includes exponential backoff for 429 rate-limit errors.
"""
from __future__ import annotations

import asyncio
import functools
import sys
import time
from pathlib import Path


def _get_gemini_client():
    """Lazily build a GeminiClient from environment variables."""
    backend_dir = Path(__file__).resolve().parents[2]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from aegis_harness.config import Settings
    from aegis_harness.gemini_client import GeminiClient

    settings = Settings.from_env(backend_dir.parent)
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not set — cannot use GeminiService")
    return GeminiClient(settings)


class GeminiService:
    """Async wrapper around the stdlib-based GeminiClient with 429 backoff."""

    # Max retries and base delay (doubles each attempt)
    _MAX_RETRIES = 3
    _BASE_DELAY = 5  # seconds

    @staticmethod
    def _client():
        return _get_gemini_client()

    @staticmethod
    async def complete(system: str, user: str, max_tokens: int = 1200) -> str:
        """
        Run a Gemini call with exponential backoff on 429 rate-limit errors.
        Offloads the synchronous urllib call to a thread pool.
        """
        client = GeminiService._client()
        loop = asyncio.get_event_loop()
        call = functools.partial(
            client.complete,
            system=system,
            user=user,
            temperature=0.2,
            max_tokens=max_tokens,
        )

        last_error: Exception = RuntimeError("No attempts made")
        for attempt in range(GeminiService._MAX_RETRIES):
            try:
                return await loop.run_in_executor(None, call)
            except RuntimeError as exc:
                last_error = exc
                msg = str(exc)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
                    # Extract the suggested retry delay if present
                    delay = GeminiService._BASE_DELAY * (2 ** attempt)
                    import re
                    m = re.search(r"retry in ([\d.]+)s", msg)
                    if m:
                        delay = max(delay, float(m.group(1)) + 1)
                    print(f"GeminiService: 429 rate limit on attempt {attempt + 1}, waiting {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    # Non-rate-limit error — don't retry
                    raise

        raise last_error
