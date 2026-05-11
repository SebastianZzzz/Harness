import os
import httpx
from typing import Tuple

from app.services.gemini_service import GeminiService

CLOD_BASE_URL = "https://api.clod.io/v1"

SYSTEM_PROMPT = (
    "You are AegisHarness, an expert Agentic Compiler. "
    "Output high-quality, secure code that strictly adheres to constraints."
)


class ClodService:
    @staticmethod
    def _get_headers() -> dict:
        return {
            "Authorization": f"Bearer {os.getenv('CLOD_API_KEY', '')}",
            "Content-Type": "application/json",
        }

    @staticmethod
    async def evaluate_and_generate(prompt: str, constraints: list[str]) -> Tuple[str, str]:
        """
        Phase 4: Generate code via Clod.io, with Gemini as automatic fallback.
        Returns (model_name, generated_code). Raises RuntimeError if both providers fail.
        """
        constraints_str = "\n".join(f"- {c}" for c in constraints)
        full_prompt = (
            f"{prompt}\n\nCRITICAL CONSTRAINTS TO AVOID BUGS:\n{constraints_str}\n\n"
            "Please output ONLY the raw code."
        )
        payload = {
            "model": "clod-unified-smart",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt},
            ],
        }

        clod_error: str | None = None
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{CLOD_BASE_URL}/chat/completions",
                    headers=ClodService._get_headers(),
                    json=payload,
                    timeout=120.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    code = data["choices"][0]["message"]["content"]
                    actual_model = data.get("model", "clod-unified-smart")
                    return actual_model, code

                clod_error = f"Clod API {response.status_code}: {response.text[:300]}"
                print(f"[ClodService] {clod_error} — falling back to Gemini")

        except Exception as exc:
            clod_error = str(exc)
            print(f"[ClodService] connection error: {clod_error} — falling back to Gemini")

        # Gemini fallback
        try:
            code = await GeminiService.complete(system=SYSTEM_PROMPT, user=full_prompt, max_tokens=4096)
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            print(f"[ClodService] Gemini fallback succeeded ({gemini_model})")
            return f"gemini-fallback/{gemini_model}", code
        except Exception as exc:
            raise RuntimeError(
                f"Both providers failed.\nClod: {clod_error}\nGemini: {exc}"
            ) from exc
