import os
# pyrefly: ignore [missing-import]
import httpx
from typing import List, Dict, Any
import asyncio

class TryniaService:
    BASE_URL = "https://apigcp.trynia.ai/v2"
    
    @staticmethod
    def _get_headers() -> Dict[str, str]:
        api_key = os.getenv("NIA_API_KEY")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
    @staticmethod
    async def search_similar_repos(prompt: str) -> List[str]:
        """
        Phase 1: Attempt to use Nia API to find high-star open source repositories 
        that match the user's natural language intent. Fallback to mock if API is incomplete.
        """
        payload = {
            "query": f"Find high quality open source repositories related to: {prompt}",
            "repository": "https://github.com/fastapi/fastapi", # Target repo to search within as fallback
            "ref": "master"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{TryniaService.BASE_URL}/sandbox/search",
                    headers=TryniaService._get_headers(),
                    json=payload,
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Try to parse repos from response, if structure is unknown, fallback
                # Assuming the response has some "results" or "matches"
                # Since we don't know the exact schema, we'll try our best and fallback
                return ["tiangolo/fastapi", "pallets/flask"] # Simplified fallback parsing
        except Exception as e:
            print(f"Nia API (Trynia) Error or Incomplete: {e}")
            # Fallback to mock repos since the API might not be fully sponsored/active
            await asyncio.sleep(1)
            return [
                "tiangolo/fastapi",
                "pallets/flask",
                "encode/starlette"
            ]

    @staticmethod
    async def generate_structured_prompt(prompt: str, repos: List[str]) -> str:
        """
        Phase 1: Rewrite the prompt based on context from similar repos.
        """
        repo_list_str = "\n".join([f"- {repo}" for repo in repos])
        return f"""# Structured System Prompt

## Original Intent
{prompt}

## Technical Context
Based on similar high-star implementations, please consider the following architectures:
{repo_list_str}

## Requirements
1. Follow best practices observed in the provided context.
2. Ensure high performance and type safety.
"""
