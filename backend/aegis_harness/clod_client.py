from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import Settings


class ClodClient:
    provider_label = "Clod.io fallback route"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model_name = settings.clod_model

    def complete(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 900,
    ) -> str:
        body = {
            "model": self.settings.clod_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        request = Request(
            f"{self.settings.clod_base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.clod_api_key}",
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
            raise RuntimeError(f"Clod API HTTP {exc.code}: {detail[:500]}") from exc
        except URLError as exc:
            raise RuntimeError(f"Clod API connection failed: {exc.reason}") from exc

        try:
            return payload["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Clod API response shape: {payload}") from exc
