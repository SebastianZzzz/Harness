from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config import Settings


class GeminiClient:
    provider_label = "Gemini API primary route"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model_name = settings.gemini_model

    def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 900,
    ) -> str:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        model = quote(f"models/{self.settings.gemini_model}", safe="/")
        request = Request(
            f"{self.settings.gemini_base_url}/{model}:generateContent",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "x-goog-api-key": self.settings.gemini_api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "AegisHarness/0.1",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail[:500]}") from exc
        except URLError as exc:
            raise RuntimeError(f"Gemini API connection failed: {exc.reason}") from exc

        try:
            parts = payload["candidates"][0]["content"]["parts"]
            return "".join(str(part.get("text", "")) for part in parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Gemini API response shape: {payload}") from exc
