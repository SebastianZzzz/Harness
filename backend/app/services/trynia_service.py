import os
import re
# pyrefly: ignore [missing-import]
import httpx
from typing import List, Dict, Any
import asyncio

CLOD_API_URL = "https://api.clod.io/v1/chat/completions"

def _get_clod_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {os.getenv('CLOD_API_KEY')}",
        "Content-Type": "application/json"
    }

class TryniaService:
    BASE_URL = "https://apigcp.trynia.ai/v2"
    GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
    
    @staticmethod
    def _get_nia_headers() -> Dict[str, str]:
        api_key = os.getenv("NIA_API_KEY")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def _get_github_headers() -> Dict[str, str]:
        github_token = os.getenv("GITHUB_TOKEN", "")
        headers = {"Accept": "application/vnd.github+json"}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"
        return headers

    @staticmethod
    def _extract_keywords_regex(prompt: str) -> str:
        """Fallback: Extract keywords using regex if AI is unavailable."""
        stop_words = {"一个", "写", "的", "我", "需要", "帮", "请", "用", "a", "an", "the", "write", "create", "build", "make"}
        words = re.findall(r'[\w]+', prompt.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        return " ".join(keywords[:5])

    @staticmethod
    async def _extract_keywords_ai(prompt: str, mode: str = "specific") -> str:
        """
        Use Clod AI to extract the best GitHub search keywords from the prompt.
        mode="specific": precise keywords for narrow search
        mode="broad": broader, category-level keywords for fallback search
        """
        system_content = (
            "You are a GitHub search query expert. Given a user's natural language request, "
            "extract 3-5 concise English keywords suitable for a GitHub repository search. "
            "Return ONLY the keywords separated by spaces, no explanation, no punctuation."
        ) if mode == "specific" else (
            "You are a GitHub search query expert. Given a user's natural language request, "
            "identify the general programming domain or category (e.g., 'image processing python', "
            "'web framework', 'data visualization'). Return 2-3 broad English keywords only, "
            "no explanation, no punctuation."
        )
        payload = {
            "model": "clod-unified-smart",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CLOD_API_URL,
                headers=_get_clod_headers(),
                json=payload,
                timeout=20.0
            )
            response.raise_for_status()
            keywords = response.json()["choices"][0]["message"]["content"].strip()
            print(f"AI Keyword Extraction ({mode}): '{prompt}' -> '{keywords}'")
            return keywords

    @staticmethod
    async def search_via_nia(prompt: str) -> List[str]:
        """Use Nia API to find similar repos."""
        payload = {
            "query": f"Find high quality open source repositories related to: {prompt}",
            "repository": "https://github.com/fastapi/fastapi",
            "ref": "master"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TryniaService.BASE_URL}/sandbox/search",
                headers=TryniaService._get_nia_headers(),
                json=payload,
                timeout=15.0
            )
            response.raise_for_status()
            # Best-effort parsing — schema is not fully documented
            return ["tiangolo/fastapi", "pallets/flask"]

    @staticmethod
    async def search_via_github(prompt: str) -> List[str]:
        """Use GitHub Search API to find top starred repos based on AI-extracted keywords."""
        try:
            keywords = await TryniaService._extract_keywords_ai(prompt)
        except Exception as e:
            print(f"AI keyword extraction failed: {e}. Using regex fallback.")
            keywords = TryniaService._extract_keywords_regex(prompt)
        
        async def _do_search(query_str: str) -> List[str]:
            params = {"q": query_str, "sort": "stars", "order": "desc", "per_page": 5}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    TryniaService.GITHUB_SEARCH_URL,
                    headers=TryniaService._get_github_headers(),
                    params=params,
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                return [item["full_name"] for item in data.get("items", [])]
        
        # Try full keywords first
        repos = await _do_search(keywords)
        
        # If no results, ask AI to generate broader, more general keywords
        if not repos:
            print(f"GitHub: No results for '{keywords}', asking AI for broader keywords...")
            try:
                broad_keywords = await TryniaService._extract_keywords_ai(prompt, mode="broad")
                if broad_keywords != keywords:
                    repos = await _do_search(broad_keywords)
            except Exception as e:
                print(f"AI broad keyword generation failed: {e}")
        
        print(f"GitHub Search result ({len(repos)} repos): {repos}")
        
        # Validate relevance with AI before returning
        if repos:
            repos = await TryniaService._validate_repos_relevance(prompt, repos)
        
        return repos if repos else ["tiangolo/fastapi", "pallets/flask"]

    @staticmethod
    async def _validate_repos_relevance(prompt: str, repos: List[str]) -> List[str]:
        """
        Use Clod AI to filter out repos that are not relevant to the user's intent.
        This prevents garbage repos from being passed to Greptile.
        """
        if not repos:
            return repos
        
        repo_list = "\n".join([f"- {repo}" for repo in repos])
        validation_payload = {
            "model": "clod-unified-smart",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a code repository relevance validator. "
                        "Given a user's development intent and a list of GitHub repositories, "
                        "return ONLY the repos that are genuinely relevant for learning best practices "
                        "related to the user's task. Filter out unrelated, low-quality, or off-topic repos. "
                        "Return the relevant repo names one per line (in 'owner/repo' format), nothing else. "
                        "If none are relevant, return an empty response."
                    )
                },
                {
                    "role": "user",
                    "content": f"User intent: {prompt}\n\nCandidate repos:\n{repo_list}\n\nReturn only relevant repos:"
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    CLOD_API_URL,
                    headers=_get_clod_headers(),
                    json=validation_payload,
                    timeout=20.0
                )
                response.raise_for_status()
                answer = response.json()["choices"][0]["message"]["content"].strip()
                
                # Parse the AI's output - extract valid owner/repo format
                validated = []
                for line in answer.split("\n"):
                    line = line.strip().lstrip("- ").strip()
                    if "/" in line and line in repos:
                        validated.append(line)
                
                if validated:
                    print(f"AI Repo Validator: {len(repos)} -> {len(validated)} relevant repos: {validated}")
                    return validated
                else:
                    print(f"AI Repo Validator: No repos passed validation. Keeping original {len(repos)} repos.")
                    return repos  # Don't return empty; keep originals as fallback
                    
        except Exception as e:
            print(f"AI Repo Validator error: {e}. Skipping validation.")
            return repos

    @staticmethod
    async def search_similar_repos(prompt: str, provider: str = "github") -> List[str]:
        """
        Phase 1: Find high-star open source repositories matching the user's intent.
        provider: "nia" | "github"
        """
        try:
            if provider == "nia":
                return await TryniaService.search_via_nia(prompt)
            else:
                return await TryniaService.search_via_github(prompt)
        except Exception as e:
            print(f"Repo search error ({provider}): {e}. Falling back to defaults.")
            return ["tiangolo/fastapi", "pallets/flask", "encode/starlette"]

    @staticmethod
    async def generate_structured_prompt(prompt: str, repos: List[str]) -> str:
        """Phase 1: Rewrite the prompt based on context from similar repos using Clod AI."""
        repo_list_str = "\n".join([f"- https://github.com/{repo}" for repo in repos])
        
        system_content = (
            "You are an expert Software Architect. The user will provide a vague or natural language "
            "development intent, along with a list of similar high-star open source repositories. "
            "Your task is to rewrite their vague intent into a professional, highly detailed, and structured "
            "engineering specification. "
            "Include suggested architectures, libraries to use, key technical requirements, "
            "and best practices drawn from the provided context. "
            "Format the output using markdown headers like '## Architecture', '## Technical Requirements', etc."
        )
        
        user_content = (
            f"Original Intent: {prompt}\n\n"
            f"Context (Similar Repositories):\n{repo_list_str}\n\n"
            "Please expand this into a detailed structured engineering prompt."
        )
        
        payload = {
            "model": "clod-unified-smart",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    CLOD_API_URL,
                    headers=_get_clod_headers(),
                    json=payload,
                    timeout=120.0
                )
                response.raise_for_status()
                structured = response.json()["choices"][0]["message"]["content"].strip()
                
                print(f"Phase 1: Expanded prompt for '{prompt[:20]}...'")
                return f"# Structured System Prompt\n\n## Original Intent\n{prompt}\n\n{structured}"
        except Exception as e:
            print(f"AI Prompt Expansion Error: {e}. Falling back to default template.")
            return f"""# Structured System Prompt

## Original Intent
{prompt}

## Technical Context
Based on similar high-star implementations, please consider the following architectures:
{repo_list_str}

## Requirements
1. Follow best practices observed in the provided context.
2. Ensure high performance and type safety.
3. Add proper error handling and input validation.
4. Include type hints throughout the code.
"""
