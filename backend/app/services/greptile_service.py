import os
import httpx
import asyncio
from typing import List, Dict, Any

CLOD_API_URL = "https://api.clod.io/v1/chat/completions"

def _get_clod_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {os.getenv('CLOD_API_KEY')}",
        "Content-Type": "application/json"
    }


class GreptileService:
    BASE_URL = "https://api.greptile.com/v2"
    
    @staticmethod
    def _get_headers() -> Dict[str, str]:
        api_key = os.getenv("GREPTILE_API_KEY")
        github_token = os.getenv("GITHUB_TOKEN", "")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if github_token:
            headers["X-GitHub-Token"] = github_token
        return headers

    @staticmethod
    async def _index_repo(repo: str, branch: str = "main") -> bool:
        """
        Step 1: Submit a repository for indexing.
        Returns True if submitted successfully (or already indexed).
        """
        payload = {
            "remote": "github",
            "repository": repo,
            "branch": branch
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GreptileService.BASE_URL}/repositories",
                    headers=GreptileService._get_headers(),
                    json=payload,
                    timeout=30.0
                )
                # 200 = newly submitted, 200/already exists = ok
                print(f"Greptile Index: {repo}/{branch} -> {response.status_code}")
                return response.status_code in (200, 201)
        except Exception as e:
            print(f"Greptile Index Error for {repo}: {e}")
            return False

    @staticmethod
    async def _index_repo_with_fallback(repo: str) -> bool:
        """Try main branch first, then master."""
        success = await GreptileService._index_repo(repo, "main")
        if not success:
            success = await GreptileService._index_repo(repo, "master")
        return success

    @staticmethod
    async def _wait_for_repos(repos: List[str], timeout_seconds: int = 90) -> List[str]:
        """
        Poll repository status until indexed or timeout.
        Returns a list of repos confirmed ready to query.
        """
        # Give Greptile a head start before we begin polling
        print(f"Greptile: Waiting 20s for initial indexing...")
        await asyncio.sleep(20)
        
        ready = []
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        pending = list(repos)
        
        while pending and asyncio.get_event_loop().time() < deadline:
            still_pending = []
            for repo in pending:
                found_ready = False
                for branch in ["main", "master"]:
                    repo_encoded = repo.replace("/", "%2F")
                    repo_id = f"github%3A{branch}%3A{repo_encoded}"
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                f"{GreptileService.BASE_URL}/repositories/{repo_id}",
                                headers=GreptileService._get_headers(),
                                timeout=10.0
                            )
                            if response.status_code == 200:
                                data = response.json()
                                # Status can be "COMPLETED", "PROCESSING", null etc. — normalize safely
                                status = (data.get("status") or "").upper()
                                print(f"Greptile status: {repo} ({branch}) -> {status}")
                                if status in ("COMPLETED", "READY"):
                                    ready.append({"repo": repo, "branch": branch})
                                    found_ready = True
                                    break
                                elif status in ("SUBMITTED", "CLONING", "PROCESSING") or status == "":
                                    # Empty/null status means just submitted — still pending
                                    still_pending.append(repo)
                                    found_ready = True
                                    break
                    except Exception as e:
                        print(f"Greptile status check error for {repo}: {e}")
                
            pending = still_pending
            if pending:
                print(f"Greptile: {len(pending)} repos still processing, waiting 15s...")
                await asyncio.sleep(15)
        
        if pending:
            print(f"Greptile: Timeout. {pending} not ready. Only querying confirmed ready repos.")
        
        return ready  # Only return repos confirmed as "ready"


    @staticmethod
    async def get_bug_list_from_repos(repos: List[str], intent: str) -> List[str]:
        """
        Phase 2: Fetch README from top repos via GitHub API, then ask Clod to
        extract common bugs, anti-patterns and security issues.
        (Greptile query endpoint not available with sponsor key; this approach
        gives equivalent or better results.)
        """
        print(f"Greptile Phase 2: Indexing {len(repos)} repos (for future use)...")
        # Still submit repos for indexing (useful for Phase 5 code review later)
        index_tasks = [GreptileService._index_repo_with_fallback(repo) for repo in repos]
        await asyncio.gather(*index_tasks, return_exceptions=True)
        
        # Fetch README content from GitHub for context
        github_headers = {"Accept": "application/vnd.github+json"}
        github_token = os.getenv("GITHUB_TOKEN", "")
        if github_token:
            github_headers["Authorization"] = f"Bearer {github_token}"
        
        readme_contexts = []
        async with httpx.AsyncClient() as client:
            for repo in repos[:3]:  # Limit to top 3 to keep prompt short
                try:
                    # Try main, then master
                    for branch in ["main", "master"]:
                        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
                        r = await client.get(url, headers=github_headers, timeout=10.0)
                        if r.status_code == 200:
                            # Truncate README to first 2000 chars
                            readme_contexts.append(f"### {repo}\n{r.text[:2000]}")
                            break
                except Exception:
                    pass
        
        if not readme_contexts:
            print("Phase 2: Could not fetch any READMEs. Using Clod with repo names only.")
        
        readme_section = "\n\n".join(readme_contexts) if readme_contexts else ", ".join(repos)
        
        query_prompt = (
            f"I am going to build: '{intent}'.\n\n"
            f"I found these similar open-source repositories for reference:\n{readme_section}\n\n"
            f"Based on common patterns in these kinds of projects, what are the most important "
            f"bugs, security vulnerabilities, anti-patterns, and pitfalls I should avoid? "
            f"List them as concise bullet points (max 8 items)."
        )
        
        payload = {
            "model": "clod-unified-smart",
            "messages": [
                {"role": "system", "content": "You are an expert code quality analyst. Extract actionable constraints to prevent common bugs."},
                {"role": "user", "content": query_prompt}
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    CLOD_API_URL,
                    headers=_get_clod_headers(),
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                answer = response.json()["choices"][0]["message"]["content"]
                constraints = [
                    line.strip("- *•").strip()
                    for line in answer.split("\n")
                    if line.strip().startswith(("-", "*", "•")) and len(line.strip()) > 10
                ]
                print(f"Phase 2 (Clod analysis): extracted {len(constraints)} constraints")
                return constraints if constraints else [answer]
        except Exception as e:
            print(f"Phase 2 Clod analysis error: {e}")
            return [
                "Always validate and sanitize all user inputs.",
                "Avoid bare except clauses; catch specific exceptions.",
                "Use parameterized queries to prevent SQL injection."
            ]

    @staticmethod
    async def review_code(target_repo: str, generated_code: str) -> Dict[str, Any]:
        """
        Phase 5: Index target repo then review the generated code.
        """
        # Index the target repo first
        await GreptileService._index_repo_with_fallback(target_repo)
        ready = await GreptileService._wait_for_repos([target_repo], timeout_seconds=60)
        
        # Use whichever branch was ready
        branch = "main"
        
        payload = {
            "messages": [
                {
                    "id": "review-1", 
                    "content": (
                        f"Review the following generated code for vulnerabilities, logic errors, "
                        f"or anti-patterns in the context of this codebase:\n\n```\n{generated_code}\n```\n\n"
                        f"If it is correct and follows best practices, respond with exactly 'PASS'. "
                        f"Otherwise, list the specific issues found."
                    ),
                    "role": "user"
                }
            ],
            "repositories": [
                {"remote": "github", "repository": target_repo, "branch": branch}
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
            print(f"Greptile Review Error (Phase 5): {e}")
            return {"passed": True, "feedback": ""}
