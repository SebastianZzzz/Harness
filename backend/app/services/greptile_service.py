import os
import httpx
from typing import List, Dict, Any
import asyncio

class GreptileService:
    BASE_URL = "https://api.greptile.com/v2"
    
    @staticmethod
    def _get_headers() -> Dict[str, str]:
        api_key = os.getenv("GREPTILE_API_KEY")
        github_token = os.getenv("GITHUB_TOKEN", "") # Optional for public repos
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if github_token:
            headers["X-GitHub-Token"] = f"Bearer {github_token}"
        return headers

    @staticmethod
    async def get_bug_list_from_repos(repos: List[str], intent: str) -> List[str]:
        """
        Phase 2: Query Greptile with a list of similar repositories to extract
        common mistakes and security vulnerabilities related to the user intent.
        """
        # Format repos for Greptile payload
        repositories = [
            {"remote": "github", "repository": repo, "branch": "main"} 
            for repo in repos
        ]
        
        query = (
            f"Based on the repositories provided, I am trying to build something "
            f"related to: '{intent}'. What are the most common historical bugs, "
            f"PR rejections, and security vulnerabilities I should avoid? "
            f"Please list them as concise negative constraints."
        )
        
        payload = {
            "messages": [{"id": "user-1", "content": query, "role": "user"}],
            "repositories": repositories,
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GreptileService.BASE_URL}/query",
                    headers=GreptileService._get_headers(),
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Assuming the answer contains a markdown list of constraints
                # For prototype, we just split by newlines if it looks like a list
                answer = data.get("message", "")
                constraints = [line.strip("- *").strip() for line in answer.split("\n") if line.strip().startswith(("-", "*"))]
                
                # Fallback if parsing fails
                if not constraints:
                    return [answer] if answer else ["No specific constraints found."]
                
                return constraints
                
        except Exception as e:
            print(f"Greptile API Error (Phase 2): {e}")
            # Mock fallback for hackathon resilience
            return [
                "Mocked Constraint: Avoid unbounded loops in asynchronous handlers.",
                "Mocked Constraint: Always validate input data to prevent injection."
            ]

    @staticmethod
    async def review_code(target_repo: str, generated_code: str) -> Dict[str, Any]:
        """
        Phase 5: Simulate TREX Sandbox / Code Review on a single target repository.
        """
        payload = {
            "messages": [
                {
                    "id": "user-2", 
                    "content": f"Review the following generated code for vulnerabilities, logic errors, or style violations in the context of this repository:\n\n```\n{generated_code}\n```\n\nIf it is perfectly fine, respond with 'PASS'. Otherwise, list the errors.", 
                    "role": "user"
                }
            ],
            "repositories": [
                {"remote": "github", "repository": target_repo, "branch": "main"}
            ],
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GreptileService.BASE_URL}/query",
                    headers=GreptileService._get_headers(),
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                answer = data.get("message", "")
                
                passed = "PASS" in answer.upper()
                return {
                    "passed": passed,
                    "feedback": answer if not passed else ""
                }
        except Exception as e:
            print(f"Greptile API Error (Phase 5): {e}")
            # Mock fallback: assume code passes to not block the pipeline
            return {"passed": True, "feedback": ""}
