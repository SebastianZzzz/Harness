import os
import httpx
from typing import Dict, Any, Tuple

class ClodService:
    BASE_URL = "https://api.clod.io/v1"
    
    @staticmethod
    def _get_headers() -> Dict[str, str]:
        api_key = os.getenv("CLOD_API_KEY")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    @staticmethod
    async def evaluate_and_generate(prompt: str, constraints: list[str]) -> Tuple[str, str]:
        """
        Phase 4: Uses Clod.io for smart routing based on energy/cost
        and generates the code.
        Returns: (selected_model_name, generated_code)
        """
        # Build the final prompt with constraints
        constraints_str = "\n".join([f"- {c}" for c in constraints])
        full_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL CONSTRAINTS TO AVOID BUGS:\n"
            f"{constraints_str}\n\n"
            f"Please output ONLY the raw code."
        )
        
        payload = {
            "model": "clod-unified-smart", # Let Clod handle the intelligent routing!
            "messages": [
                {"role": "system", "content": "You are AegisHarness, an expert Agentic Compiler. Output high-quality, secure code that strictly adheres to constraints."},
                {"role": "user", "content": full_prompt}
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{ClodService.BASE_URL}/chat/completions",
                    headers=ClodService._get_headers(),
                    json=payload,
                    timeout=120.0
                )
                if response.status_code != 200:
                    print(f"Clod API Error Details: {response.text}")
                response.raise_for_status()
                data = response.json()
                
                generated_code = data["choices"][0]["message"]["content"]
                # Clod API often returns the actual routed model in the response metadata
                actual_model = data.get("model", "clod-unified-smart")
                
                return actual_model, generated_code
                
        except httpx.HTTPStatusError as e:
            print(f"Clod API HTTP Error (Phase 4): {e.response.status_code} - {e.response.text}")
            return "mocked-claude-3-haiku", "def mocked_function():\n    pass # Network error with Clod"
        except Exception as e:
            print(f"Clod API Error (Phase 4): {e}")
            # Mock fallback
            return "mocked-claude-3-haiku", "def mocked_function():\n    pass # Network error with Clod"
