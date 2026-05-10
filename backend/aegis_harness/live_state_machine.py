from __future__ import annotations

import json
from json import JSONDecodeError
import re

from .clod_client import ClodClient
from .config import Settings
from .gemini_client import GeminiClient
from .prompts import ReferenceRepo, RiskFinding, append_risk_guide, rewrite_request
from .routing import route_for_task
from .state_machine import AegisHarnessMockBackend, CodeArtifact, ReviewResult, Task, TaskStatus


JSON_SYSTEM = "Return valid compact JSON only. Do not wrap it in markdown."


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.S)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


class AegisHarnessLiveBackend(AegisHarnessMockBackend):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.ai = GeminiClient(settings) if settings.gemini_api_key else ClodClient(settings)

    def start(self, request: str) -> Task:
        task = Task(
            id=next(self._ids),
            request=request,
            max_iterations=self.settings.max_iterations,
        )
        self.tasks[task.id] = task
        self._event(task, "task.received", "Natural-language request received.")

        task.status = TaskStatus.CONTEXT
        context = self._ai_context_and_prompt(request)
        task.references = context["references"]
        task.confidence = context["confidence"]
        task.prompt = context["prompt"]
        self._event(task, "context.search.completed", f"{self.ai.model_name} returned repository context.")
        self._event(task, "prompt.expanded", f"{self.ai.model_name} generated the Markdown brief.")

        task.status = TaskStatus.RISK
        task.risks = self._ai_risk_guide(request, task.prompt)
        task.prompt = append_risk_guide(task.prompt, task.risks)
        self._event(task, "risk.preflight.completed", f"{self.ai.model_name} generated negative constraints.")

        task.status = TaskStatus.PENDING_APPROVAL
        self._event(task, "hitl.approval.requested", "Paused before execution.")
        return task

    def approve(self, task_id: int, approved_prompt: str | None = None) -> Task:
        task = self.tasks[task_id]
        if task.status != TaskStatus.PENDING_APPROVAL:
            raise ValueError(f"Task {task_id} is not awaiting approval.")

        if approved_prompt:
            task.prompt = approved_prompt

        task.status = TaskStatus.EXECUTION
        self._event(task, "hitl.approved", "Human approval captured.")
        task.route = route_for_task(
            task.confidence,
            len(task.risks),
            task.request,
            model=self.ai.model_name,
            provider=self.ai.provider_label,
        )
        self._event(task, "compute.route.selected", f"Selected {task.route.model}.")
        self._event(task, "generation.started", f"{self.ai.model_name} code generation started.")

        task.code = self._ai_generate_code(task.prompt)
        self._event(task, "generation.completed", task.code.summary)

        task.status = TaskStatus.SANDBOX
        self._run_live_review_until_done(task)
        return task

    def _ai_context_and_prompt(self, request: str) -> dict:
        schema = (
            '{"confidence": 0, "references": [{"name": "owner/repo", "stars": "n/a", '
            '"signal": "why it matters"}], "prompt": "markdown brief"}'
        )
        response = self.ai.complete(
            system=JSON_SYSTEM,
            user=(
                "You are AegisHarness Phase 1. Create repository context and an agent-ready brief.\n"
                "Return JSON with keys: confidence integer 0-100, references array of "
                "{name, stars, signal}, prompt markdown string.\n"
                f"User request: {request}"
            ),
            temperature=0.2,
            max_tokens=1100,
        )
        try:
            data = self._json_or_repair(response, schema)
        except (JSONDecodeError, ValueError):
            data = {"references": [], "prompt": "", "confidence": 70}
        references = [
            ReferenceRepo(
                name=str(item.get("name", "unknown/repository")),
                stars=str(item.get("stars", "n/a")),
                signal=str(item.get("signal", "Relevant implementation context")),
            )
            for item in data.get("references", [])[:4]
        ]
        if not references:
            references = [ReferenceRepo("ai/context", "n/a", f"{self.ai.model_name} contextual analysis")]
        prompt = str(data.get("prompt") or rewrite_request(request, references))
        confidence = int(data.get("confidence", 75))
        return {"references": references, "prompt": prompt, "confidence": max(0, min(100, confidence))}

    def _ai_risk_guide(self, request: str, prompt: str) -> list[RiskFinding]:
        schema = (
            '{"risks": [{"title": "risk title", "severity": "medium", '
            '"mitigation": "specific mitigation"}]}'
        )
        response = self.ai.complete(
            system=JSON_SYSTEM,
            user=(
                "You are AegisHarness Phase 2. Generate a preflight bug list for this coding task.\n"
                "Return JSON with key risks: array of {title, severity, mitigation}. "
                "Severity must be one of critical, high, medium, low.\n"
                f"Request: {request}\n\nPrompt:\n{prompt}"
            ),
            temperature=0.15,
            max_tokens=700,
        )
        try:
            data = self._json_or_repair(response, schema)
        except (JSONDecodeError, ValueError):
            return []
        risks = []
        for item in data.get("risks", [])[:6]:
            severity = str(item.get("severity", "medium")).lower()
            if severity not in {"critical", "high", "medium", "low"}:
                severity = "medium"
            risks.append(
                RiskFinding(
                    title=str(item.get("title", "Unspecified implementation risk")),
                    severity=severity,
                    mitigation=str(item.get("mitigation", "Add a regression test and surface uncertainty.")),
                )
            )
        return risks

    def _ai_generate_code(self, approved_prompt: str) -> CodeArtifact:
        schema = '{"title": "file.ts", "language": "ts", "summary": "summary", "patch": "code"}'
        response = self.ai.complete(
            system=JSON_SYSTEM,
            user=(
                f"You are AegisHarness Phase 4 using {self.ai.model_name}. Generate a small, reviewable code artifact.\n"
                "Return JSON with keys: title, language, summary, patch. The patch should be concise.\n"
                f"Approved prompt:\n{approved_prompt}"
            ),
            temperature=0.2,
            max_tokens=900,
        )
        try:
            data = self._json_or_repair(response, schema)
        except (JSONDecodeError, ValueError):
            first_line = next((line.strip() for line in response.splitlines() if line.strip()), "")
            return CodeArtifact(
                title="ai-generated-output.md",
                language="md",
                summary=first_line[:180] or f"{self.ai.model_name} generated an artifact.",
                patch=response,
            )
        return CodeArtifact(
            title=str(data.get("title", "generated_patch.ts")),
            language=str(data.get("language", "ts")),
            summary=str(data.get("summary", f"{self.ai.model_name} generated a reviewable code artifact.")),
            patch=str(data.get("patch", "")),
        )

    def _ai_review(self, task: Task) -> ReviewResult:
        schema = '{"status": "passed", "summary": "review summary", "tests": ["test: passed"]}'
        response = self.ai.complete(
            system=JSON_SYSTEM,
            user=(
                "You are AegisHarness Phase 5 sandbox reviewer. Review the generated artifact against the prompt.\n"
                "Return JSON with keys: status ('passed' or 'failed'), summary, tests array of strings. "
                "Only fail for concrete issues that can be repaired.\n"
                f"Attempt: {task.repair_attempts}\nPrompt:\n{task.prompt}\n\nPatch:\n{task.code.patch if task.code else ''}"
            ),
            temperature=0.1,
            max_tokens=650,
        )
        try:
            data = self._json_or_repair(response, schema)
        except (JSONDecodeError, ValueError):
            lower = response.lower()
            status = "failed" if "fail" in lower and "pass" not in lower else "passed"
            return ReviewResult(
                status=status,
                tests=[line.strip() for line in response.splitlines() if line.strip()][:8],
                summary=response[:500] or f"{self.ai.model_name} review returned an empty response.",
            )
        status = str(data.get("status", "failed")).lower()
        if status not in {"passed", "failed"}:
            status = "failed"
        tests = [str(item) for item in data.get("tests", [])[:8]]
        return ReviewResult(
            status=status,
            tests=tests,
            summary=str(data.get("summary", f"{self.ai.model_name} review completed.")),
        )

    def _ai_repair(self, task: Task) -> None:
        schema = '{"summary": "repair summary", "patch": "code"}'
        response = self.ai.complete(
            system=JSON_SYSTEM,
            user=(
                f"You are AegisHarness greploop repair using {self.ai.model_name}. Repair only the review failure.\n"
                "Return JSON with keys: summary, patch. Keep the patch concise.\n"
                f"Prompt:\n{task.prompt}\n\nCurrent patch:\n{task.code.patch if task.code else ''}\n\nReview failure:\n{task.review.summary}"
            ),
            temperature=0.15,
            max_tokens=900,
        )
        try:
            data = self._json_or_repair(response, schema)
        except (JSONDecodeError, ValueError):
            data = {"summary": response[:180] or f"{self.ai.model_name} repair completed.", "patch": response}
        if task.code:
            task.code.patch = str(data.get("patch", task.code.patch))
            task.code.summary = str(data.get("summary", task.code.summary))

    def _run_live_review_until_done(self, task: Task) -> None:
        while True:
            task.review = self._ai_review(task)
            self._event(task, "sandbox.review.completed", task.review.summary)

            if task.review.status == "passed":
                task.status = TaskStatus.FINISHED
                self._event(task, "workflow.finished", f"FINISHED with {self.ai.model_name}-generated code and review.")
                return

            if task.repair_attempts >= task.max_iterations:
                task.status = TaskStatus.FAILED
                self._event(task, "workflow.failed", "Max greploop iterations reached.")
                return

            task.repair_attempts += 1
            task.status = TaskStatus.REPAIR
            self._event(task, "repair.started", f"{self.ai.model_name} repair {task.repair_attempts} started.")
            self._ai_repair(task)
            self._event(task, "repair.completed", f"{self.ai.model_name} repair {task.repair_attempts} completed.")
            task.status = TaskStatus.SANDBOX

    def _json_or_repair(self, response: str, schema: str) -> dict:
        try:
            return _extract_json_object(response)
        except (JSONDecodeError, ValueError):
            repaired = self.ai.complete(
                system=JSON_SYSTEM,
                user=(
                    "Convert this model response into valid compact JSON matching this schema. "
                    "Preserve useful content. Escape all newlines inside string values.\n\n"
                    f"Schema example:\n{schema}\n\nResponse:\n{response}"
                ),
                temperature=0,
                max_tokens=1400,
            )
            return _extract_json_object(repaired)
