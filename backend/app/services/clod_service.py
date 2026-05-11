import os
import httpx
import re
from typing import Dict, Any, Tuple, Optional

from app.services.gemini_service import GeminiService

CLOD_BASE_URL = "https://api.clod.io/v1"

SYSTEM_PROMPT = (
    "You are AegisHarness yaolong, an expert Agentic Compiler. "
    "Output high-quality, secure code that strictly adheres to constraints. "
    "NEVER output markdown fences, ONLY the raw python code."
)

class ClodService:
    @staticmethod
    def _get_headers() -> dict:
        return {
            "Authorization": f"Bearer {os.getenv('CLOD_API_KEY', '')}",
            "Content-Type": "application/json",
        }

    @staticmethod
    async def evaluate_and_generate(prompt: str, constraints: list[str], iteration: int = 0, previous_code: Optional[str] = None) -> Tuple[str, str]:
        """
        Phase 4 / Phase 6: Uses Clod.io to generate or rewrite code.
        If iteration > 0, escalates to a more powerful model to fix stubborn bugs.
        If previous_code is provided, the model refactors it instead of generating from scratch.
        Returns: (selected_model_name, generated_code)
        """
        constraints_str = "\n".join([f"- {c}" for c in constraints])
        
        if previous_code:
            full_prompt = (
                f"You are refactoring/fixing the following code based on reviewer feedback.\n\n"
                f"ORIGINAL INTENT:\n{prompt}\n\n"
                f"CURRENT CODE:\n```python\n{previous_code}\n```\n\n"
                f"CRITICAL CONSTRAINTS & FEEDBACK TO FIX:\n{constraints_str}\n\n"
                f"Please output ONLY the complete fixed raw python code. Do not omit any parts."
            )
        else:
            full_prompt = (
                f"{prompt}\n\n"
                f"CRITICAL CONSTRAINTS TO AVOID BUGS:\n"
                f"{constraints_str}\n\n"
                f"Please output ONLY the raw code."
            )
        
        # --- Model Escalation Logic ---
        # 0: fast/cheap model. >0: clod-unified-max (strongest available)
        selected_model = "clod-unified-smart" if iteration == 0 else "clod-unified-max"
        
        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt}
            ]
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
                    raw_code = data["choices"][0]["message"]["content"]
                    
                    # Clean up markdown fences just in case
                    raw_code = re.sub(r"^```[a-z]*\n", "", raw_code)
                    raw_code = re.sub(r"```$", "", raw_code.strip())
                    
                    actual_model = data.get("model", selected_model)
                    return actual_model, raw_code

                clod_error = f"Clod API {response.status_code}: {response.text[:300]}"
                print(f"[ClodService] {clod_error} — falling back to Gemini")

        except Exception as exc:
            clod_error = str(exc)
            print(f"[ClodService] connection error: {clod_error} — falling back to Gemini")

        # Gemini fallback
        try:
            code = await GeminiService.complete(system=SYSTEM_PROMPT, user=full_prompt, max_tokens=4096)
            
            # Clean up markdown fences from fallback too
            code = re.sub(r"^```[a-z]*\n", "", code)
            code = re.sub(r"```$", "", code.strip())
            
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            print(f"[ClodService] Gemini fallback succeeded ({gemini_model})")
            return f"gemini-fallback/{gemini_model}", code
        except Exception as exc:
            raise RuntimeError(
                f"Both providers failed.\nClod: {clod_error}\nGemini: {exc}"
            ) from exc
