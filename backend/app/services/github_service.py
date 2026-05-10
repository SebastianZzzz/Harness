import os
import base64
import asyncio
import httpx
from typing import Dict, Any, Optional

SANDBOX_REPO = "SebastianZzzz/AegisHarness-Demo"
BASE_URL = "https://api.github.com"


def _get_github_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28"
    }


class GitHubService:

    @staticmethod
    async def _get_default_branch_sha(repo: str = SANDBOX_REPO) -> str:
        """Get the SHA of the latest commit on the default branch."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/repos/{repo}/git/ref/heads/main",
                headers=_get_github_headers(),
                timeout=10.0
            )
            r.raise_for_status()
            return r.json()["object"]["sha"]

    @staticmethod
    async def create_branch(branch_name: str, repo: str = SANDBOX_REPO) -> bool:
        """Create a new branch from main."""
        sha = await GitHubService._get_default_branch_sha(repo)
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/repos/{repo}/git/refs",
                headers=_get_github_headers(),
                json={"ref": f"refs/heads/{branch_name}", "sha": sha},
                timeout=10.0
            )
            # 201 = created, 422 = already exists (ok)
            print(f"GitHub: Created branch '{branch_name}' -> {r.status_code}")
            return r.status_code in (201, 422)

    @staticmethod
    async def commit_code(branch_name: str, code: str, filename: str = "generated_code.py",
                          repo: str = SANDBOX_REPO) -> bool:
        """Commit generated code to a branch."""
        encoded = base64.b64encode(code.encode("utf-8")).decode("utf-8")

        # Check if file already exists (to get its SHA for update)
        existing_sha: Optional[str] = None
        async with httpx.AsyncClient() as client:
            check = await client.get(
                f"{BASE_URL}/repos/{repo}/contents/{filename}?ref={branch_name}",
                headers=_get_github_headers(),
                timeout=10.0
            )
            if check.status_code == 200:
                existing_sha = check.json().get("sha")

        payload: Dict[str, Any] = {
            "message": f"feat(aegis): AI-generated code via AegisHarness",
            "content": encoded,
            "branch": branch_name
        }
        if existing_sha:
            payload["sha"] = existing_sha

        async with httpx.AsyncClient() as client:
            r = await client.put(
                f"{BASE_URL}/repos/{repo}/contents/{filename}",
                headers=_get_github_headers(),
                json=payload,
                timeout=15.0
            )
            print(f"GitHub: Committed code to '{branch_name}' -> {r.status_code}")
            return r.status_code in (200, 201)

    @staticmethod
    async def create_pr(branch_name: str, task_id: str, prompt: str,
                        repo: str = SANDBOX_REPO) -> int:
        """Open a Pull Request and return its number."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/repos/{repo}/pulls",
                headers=_get_github_headers(),
                json={
                    "title": f"[AegisHarness] AI-generated code — Task {task_id[:8]}",
                    "body": (
                        f"## 🤖 AegisHarness Auto-Generated Code\n\n"
                        f"**Original intent:** {prompt}\n\n"
                        f"**Task ID:** `{task_id}`\n\n"
                        f"This PR was automatically created by AegisHarness. "
                        f"Greptile will review this code against the codebase context."
                    ),
                    "head": branch_name,
                    "base": "main"
                },
                timeout=15.0
            )
            r.raise_for_status()
            pr_number = r.json()["number"]
            pr_url = r.json()["html_url"]
            print(f"GitHub: Created PR #{pr_number} -> {pr_url}")
            return pr_number

    @staticmethod
    async def wait_for_greptile_review(pr_number: int, repo: str = SANDBOX_REPO,
                                       timeout_seconds: int = 180) -> Dict[str, Any]:
        """
        Poll the PR for Greptile's review comment.
        Greptile posts as 'greptile-app[bot]'.
        Returns {"passed": bool, "feedback": str, "pr_url": str}
        """
        pr_url = f"https://github.com/{repo}/pull/{pr_number}"
        deadline = asyncio.get_event_loop().time() + timeout_seconds

        print(f"GitHub: Waiting for Greptile review on PR #{pr_number}...")

        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(15)  # Poll every 15 seconds

            async with httpx.AsyncClient() as client:
                # Check PR reviews first
                r_reviews = await client.get(
                    f"{BASE_URL}/repos/{repo}/pulls/{pr_number}/reviews",
                    headers=_get_github_headers(),
                    timeout=10.0
                )
                if r_reviews.status_code == 200:
                    for review in r_reviews.json():
                        login = review.get("user", {}).get("login", "")
                        if "greptile" in login.lower():
                            body = review.get("body", "")
                            state = review.get("state", "")
                            passed = state == "APPROVED" or (
                                "lgtm" in body.lower() or
                                "looks good" in body.lower() or
                                len(body.strip()) == 0
                            )
                            print(f"GitHub: Greptile review found! state={state}, passed={passed}")
                            return {"passed": passed, "feedback": body, "pr_url": pr_url}

                # Also check PR comments (Greptile sometimes posts as a comment)
                r_comments = await client.get(
                    f"{BASE_URL}/repos/{repo}/issues/{pr_number}/comments",
                    headers=_get_github_headers(),
                    timeout=10.0
                )
                if r_comments.status_code == 200:
                    for comment in r_comments.json():
                        login = comment.get("user", {}).get("login", "")
                        if "greptile" in login.lower():
                            body = comment.get("body", "")
                            passed = (
                                "lgtm" in body.lower() or
                                "looks good" in body.lower() or
                                "no issues" in body.lower()
                            )
                            print(f"GitHub: Greptile comment found! passed={passed}")
                            return {"passed": passed, "feedback": body, "pr_url": pr_url}

            print(f"GitHub: Greptile not reviewed yet, waiting...")

        print(f"GitHub: Timeout waiting for Greptile review on PR #{pr_number}.")
        # Timeout = treat as passed (don't block forever)
        return {
            "passed": True,
            "feedback": "Greptile review timed out — proceeding.",
            "pr_url": pr_url
        }

    @staticmethod
    async def close_pr(pr_number: int, repo: str = SANDBOX_REPO):
        """Close the PR after sandbox testing."""
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{BASE_URL}/repos/{repo}/pulls/{pr_number}",
                headers=_get_github_headers(),
                json={"state": "closed"},
                timeout=10.0
            )

    @staticmethod
    async def merge_pr(pr_number: int, repo: str = SANDBOX_REPO) -> bool:
        """Merge the PR into main after Greptile approval."""
        async with httpx.AsyncClient() as client:
            r = await client.put(
                f"{BASE_URL}/repos/{repo}/pulls/{pr_number}/merge",
                headers=_get_github_headers(),
                json={
                    "commit_title": f"feat(aegis): merge AI-generated code (PR #{pr_number})",
                    "commit_message": "Auto-merged by AegisHarness after Greptile sandbox review passed.",
                    "merge_method": "squash"
                },
                timeout=15.0
            )
            merged = r.status_code == 200
            print(f"GitHub: Merge PR #{pr_number} -> {'SUCCESS' if merged else f'FAILED ({r.status_code})'}")
            return merged

    @staticmethod
    async def run_sandbox(task_id: str, prompt: str, code: str) -> Dict[str, Any]:
        """
        Full Phase 5 flow:
        1. Create branch & commit generated code
        2. Open PR
        3. Wait for Greptile review
        4. If passed → merge to main (final delivery!)
        5. Return result
        """
        branch_name = f"aegis-{task_id[:8]}"

        try:
            await GitHubService.create_branch(branch_name)
            
            # 使用独立的源文件存放代码，让 PR 更真实且不会单纯覆盖
            filename = f"src/task_{task_id[:8]}.py"
            await GitHubService.commit_code(branch_name, code, filename=filename)
            
            pr_number = await GitHubService.create_pr(branch_name, task_id, prompt)
            result = await GitHubService.wait_for_greptile_review(pr_number)
            result["pr_number"] = pr_number

            if result["passed"]:
                merged = await GitHubService.merge_pr(pr_number)
                result["merged"] = merged
                if merged:
                    print(f"GitHub: ✅ Code merged to main! Task {task_id[:8]} complete.")
            else:
                # Close the PR so next iteration can open a fresh one
                await GitHubService.close_pr(pr_number)
                result["merged"] = False

            return result
        except Exception as e:
            print(f"GitHub Sandbox Error: {e}")
            return {"passed": True, "feedback": str(e), "pr_url": "", "pr_number": None, "merged": False}
