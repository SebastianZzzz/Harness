import os
import re
import base64
import asyncio
import httpx
from typing import Dict, Any, Optional

SANDBOX_REPO = "SebastianZzzz/Harness"
BASE_URL = "https://api.github.com"
CLOD_API_URL = "https://api.clod.io/v1/chat/completions"


def _get_github_headers(token: Optional[str] = None) -> Dict[str, str]:
    """Build GitHub API headers, using user-supplied token if provided (BYOK)."""
    resolved_token = token or os.getenv("GITHUB_TOKEN", "")
    return {
        "Authorization": f"Bearer {resolved_token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28"
    }



def _get_clod_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {os.getenv('CLOD_API_KEY')}",
        "Content-Type": "application/json"
    }


async def _generate_git_metadata(prompt: str) -> Dict[str, str]:
    """
    Use Clod to convert a natural-language prompt into:
    - branch: e.g. "feat/image-object-detection"
    - title:  e.g. "feat: Implement Image Object Detection CLI"
    - commit: a concise one-liner for the commit message
    Falls back to a sanitized slug if the Clod call fails.
    """
    payload = {
        "model": "clod-unified-smart",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Git commit message expert. Given a natural language description of a task, "
                    "output ONLY a JSON object with exactly three keys:\n"
                    "  branch: a kebab-case git branch name starting with 'feat/' (max 40 chars)\n"
                    "  title:  a PR title following Conventional Commits format (max 72 chars)\n"
                    "  commit: a one-line commit message following Conventional Commits (max 72 chars)\n"
                    "Return ONLY the JSON object, no markdown fences, no explanation."
                )
            },
            {"role": "user", "content": f"Task: {prompt}"}
        ]
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                CLOD_API_URL, headers=_get_clod_headers(), json=payload, timeout=30.0
            )
            resp.raise_for_status()
            import json
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown fences if model added them
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
            meta = json.loads(raw)
            # Sanitize branch name just in case
            branch = re.sub(r"[^a-z0-9/_-]", "-", meta.get("branch", "feat/ai-generated").lower())
            return {
                "branch": branch[:50],
                "title": meta.get("title", f"feat: {prompt[:60]}"),
                "commit": meta.get("commit", f"feat: {prompt[:60]} (AI generated)")
            }
    except Exception as e:
        print(f"GitHub: Clod metadata generation failed ({e}), using slug fallback.")
        slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())[:35].strip("-")
        return {
            "branch": f"feat/{slug}",
            "title": f"feat: {prompt[:60]}",
            "commit": f"feat: {prompt[:60]} (AI generated)"
        }


class GitHubService:

    @staticmethod
    async def _get_default_branch_sha(repo: str = SANDBOX_REPO, token: Optional[str] = None) -> str:
        """Get the SHA of the latest commit on the default branch."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BASE_URL}/repos/{repo}/git/ref/heads/main",
                headers=_get_github_headers(token),
                timeout=10.0
            )
            r.raise_for_status()
            return r.json()["object"]["sha"]

    @staticmethod
    async def create_branch(branch_name: str, repo: str = SANDBOX_REPO,
                            token: Optional[str] = None) -> bool:
        """Create a new branch from main."""
        sha = await GitHubService._get_default_branch_sha(repo, token)
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/repos/{repo}/git/refs",
                headers=_get_github_headers(token),
                json={"ref": f"refs/heads/{branch_name}", "sha": sha},
                timeout=10.0
            )
            print(f"GitHub: Created branch '{branch_name}' -> {r.status_code}")
            return r.status_code in (201, 422)

    @staticmethod
    async def commit_code(branch_name: str, code: str,
                          filename: str = "generated_code.py",
                          commit_message: str = "feat: AI-generated code",
                          repo: str = SANDBOX_REPO,
                          token: Optional[str] = None) -> str:
        """Commit generated code to a branch and return the commit SHA."""
        encoded = base64.b64encode(code.encode("utf-8")).decode("utf-8")

        # Check if file already exists (needed to get SHA for update)
        existing_sha: Optional[str] = None
        async with httpx.AsyncClient() as client:
            check = await client.get(
                f"{BASE_URL}/repos/{repo}/contents/{filename}?ref={branch_name}",
                headers=_get_github_headers(token),
                timeout=10.0
            )
            if check.status_code == 200:
                existing_sha = check.json().get("sha")

        payload: Dict[str, Any] = {
            "message": commit_message,
            "content": encoded,
            "branch": branch_name
        }
        if existing_sha:
            payload["sha"] = existing_sha

        async with httpx.AsyncClient() as client:
            r = await client.put(
                f"{BASE_URL}/repos/{repo}/contents/{filename}",
                headers=_get_github_headers(token),
                json=payload,
                timeout=15.0
            )
            r.raise_for_status()
            commit_sha = r.json()["commit"]["sha"]
            print(f"GitHub: Committed '{filename}' to '{branch_name}' -> {commit_sha[:8]}")
            return commit_sha

    @staticmethod
    async def create_pr(branch_name: str, task_id: str, prompt: str,
                        pr_title: str = "",
                        repo: str = SANDBOX_REPO,
                        token: Optional[str] = None) -> int:
        """Open a Pull Request and return its number."""
        title = pr_title or f"feat: {prompt[:60]}"
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE_URL}/repos/{repo}/pulls",
                headers=_get_github_headers(token),
                json={
                    "title": title,
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
            print(f"GitHub: Created PR #{pr_number} '{title}' -> {pr_url}")
            return pr_number

    @staticmethod
    async def wait_for_greptile_review(pr_number: int, commit_sha: str,
                                       repo: str = SANDBOX_REPO,
                                       token: Optional[str] = None,
                                       timeout_seconds: int = 180) -> Dict[str, Any]:
        """
        Poll the PR for Greptile's review comment for a SPECIFIC commit.
        """
        pr_url = f"https://github.com/{repo}/pull/{pr_number}"
        deadline = asyncio.get_event_loop().time() + timeout_seconds

        print(f"GitHub: Waiting for Greptile review on PR #{pr_number} for commit {commit_sha[:8]}...")

        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(15)

            async with httpx.AsyncClient() as client:
                # 1. Fetch top-level Issue Comments (Summary, Flowchart)
                r_issue_comments = await client.get(
                    f"{BASE_URL}/repos/{repo}/issues/{pr_number}/comments",
                    headers=_get_github_headers(token),
                    timeout=10.0
                )

                # 2. Fetch Line-level Review Comments (Exact fixes)
                r_review_comments = await client.get(
                    f"{BASE_URL}/repos/{repo}/pulls/{pr_number}/comments",
                    headers=_get_github_headers(token),
                    timeout=10.0
                )

                if r_issue_comments.status_code == 200:
                    summary_comment = ""
                    for comment in r_issue_comments.json():
                        login = comment.get("user", {}).get("login", "")
                        if "greptile" not in login.lower():
                            continue
                        body = comment.get("body", "")
                        if commit_sha and commit_sha not in body:
                            continue
                        summary_comment = body
                        break
                    
                    if summary_comment:
                        # Fetch all detailed line comments from Greptile
                        detail_comments = []
                        if r_review_comments.status_code == 200:
                            for c in r_review_comments.json():
                                if "greptile" in c.get("user", {}).get("login", "").lower():
                                    path = c.get("path", "")
                                    line = c.get("line") or c.get("original_line", "unknown")
                                    body = c.get("body", "")
                                    detail_comments.append(f"[{path} L{line}]: {body}")
                        
                        full_feedback = summary_comment
                        if detail_comments:
                            full_feedback += "\n\n### Detailed Line-by-Line Feedback:\n" + "\n".join(detail_comments)

                        # --- Parse numeric Confidence Score ---
                        score: Optional[int] = None
                        m = re.search(r"confidence score[:\s]+([1-5])(?:[/\s]|$)",
                                      summary_comment, re.IGNORECASE)
                        if m:
                            score = int(m.group(1))

                        if score is not None:
                            passed = score >= 4
                            needs_warning = score == 4
                        else:
                            failed_kw = any(kw in summary_comment.lower() for kw in [
                                "not safe to merge", "p0 blocker", "p0 bug"
                            ])
                            passed = not failed_kw
                            needs_warning = False

                        print(f"GitHub: Greptile review — score={score}, passed={passed}, details={len(detail_comments)}")
                        return {
                            "confidence_score": score,
                            "passed": passed,
                            "needs_warning": needs_warning,
                            "feedback": full_feedback,
                            "pr_url": pr_url
                        }

            print(f"GitHub: Greptile not reviewed yet, waiting...")

        print(f"GitHub: Timeout waiting for Greptile review on PR #{pr_number}.")
        return {
            "confidence_score": None,
            "passed": True,
            "needs_warning": False,
            "feedback": "Greptile review timed out — proceeding.",
            "pr_url": pr_url
        }

    @staticmethod
    async def close_pr(pr_number: int, repo: str = SANDBOX_REPO,
                       token: Optional[str] = None):
        """Close the PR after a failed sandbox iteration."""
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{BASE_URL}/repos/{repo}/pulls/{pr_number}",
                headers=_get_github_headers(token),
                json={"state": "closed"},
                timeout=10.0
            )

    @staticmethod
    async def merge_pr(pr_number: int, commit_title: str = "",
                       prompt: str = "",
                       repo: str = SANDBOX_REPO,
                       token: Optional[str] = None) -> bool:
        """Squash-merge the PR into main after Greptile approval."""
        title = commit_title or f"feat: {prompt[:60]} (auto-merged by AegisHarness)"
        async with httpx.AsyncClient() as client:
            r = await client.put(
                f"{BASE_URL}/repos/{repo}/pulls/{pr_number}/merge",
                headers=_get_github_headers(token),
                json={
                    "commit_title": title,
                    "commit_message": (
                        f"Auto-merged by AegisHarness after Greptile sandbox review passed.\n\n"
                        f"Original intent: {prompt}"
                    ),
                    "merge_method": "squash"
                },
                timeout=15.0
            )
            merged = r.status_code == 200
            print(f"GitHub: Merge PR #{pr_number} -> {'SUCCESS' if merged else f'FAILED ({r.status_code})'}")
            return merged

    @staticmethod
    async def run_sandbox(task_id: str, prompt: str, code: str,
                          branch_name: str,
                          pr_title: str,
                          commit_message: str,
                          github_token: Optional[str] = None,
                          target_repo: Optional[str] = None) -> Dict[str, Any]:
        """
        Full Phase 5 flow:
        1. Create branch (or reuse) & commit generated code
        2. Open NEW PR for the branch
        3. Wait for Greptile review on the exact commit
        4. If passed → squash merge to main; else → close PR
        """
        repo = target_repo or SANDBOX_REPO
        token = github_token or None  # will fall back to env inside _get_github_headers
        filename = f"src/task_{task_id[:8]}.py"

        print(f"GitHub: Using branch='{branch_name}', repo='{repo}'")

        try:
            await GitHubService.create_branch(branch_name, repo=repo, token=token)
            commit_sha = await GitHubService.commit_code(
                branch_name, code,
                filename=filename,
                commit_message=commit_message,
                repo=repo, token=token
            )
            
            pr_number = await GitHubService.create_pr(
                branch_name, task_id, prompt,
                pr_title=pr_title,
                repo=repo, token=token
            )
                
            result = await GitHubService.wait_for_greptile_review(
                pr_number, commit_sha=commit_sha, repo=repo, token=token
            )
            result["pr_number"] = pr_number

            if result["passed"]:
                merged = await GitHubService.merge_pr(
                    pr_number,
                    commit_title=pr_title,
                    prompt=prompt,
                    repo=repo, token=token
                )
                result["merged"] = merged
                if merged:
                    print(f"GitHub: ✅ Code merged to main! Task {task_id[:8]} complete.")
            else:
                # Close PR if failed, as per user requirement, but branch remains.
                await GitHubService.close_pr(pr_number, repo=repo, token=token)
                result["merged"] = False

            return result
        except Exception as e:
            print(f"GitHub Sandbox Error: {e}")
            return {"passed": True, "feedback": str(e), "pr_url": "", "pr_number": None, "merged": False}
