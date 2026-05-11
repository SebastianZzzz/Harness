from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from itertools import count
from time import strftime

from .adapters import clod_context_search_mock, risk_preflight_mock, trex_sandbox_mock
from .prompts import ReferenceRepo, RiskFinding, append_risk_guide, rewrite_request
from .routing import RouteDecision, route_for_task


class TaskStatus(StrEnum):
    IDLE = "IDLE"
    CONTEXT = "CONTEXT"
    RISK = "RISK"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    EXECUTION = "EXECUTION"
    SANDBOX = "SANDBOX"
    REPAIR = "REPAIR"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


@dataclass
class WorkflowEvent:
    id: int
    type: str
    detail: str
    timestamp: str


@dataclass
class ReviewResult:
    status: str = "pending"
    tests: list[str] = field(default_factory=list)
    summary: str = "No sandbox review has run yet."


@dataclass
class CodeArtifact:
    title: str
    language: str
    summary: str
    patch: str


@dataclass
class Task:
    id: int
    request: str
    status: TaskStatus = TaskStatus.IDLE
    confidence: int = 0
    prompt: str = ""
    references: list[ReferenceRepo] = field(default_factory=list)
    risks: list[RiskFinding] = field(default_factory=list)
    route: RouteDecision | None = None
    code: CodeArtifact | None = None
    repair_attempts: int = 0
    max_iterations: int = 3
    review: ReviewResult = field(default_factory=ReviewResult)
    events: list[WorkflowEvent] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class AegisHarnessMockBackend:
    def __init__(self) -> None:
        self._ids = count(1)
        self.tasks: dict[int, Task] = {}

    def start(self, request: str) -> Task:
        task = Task(id=next(self._ids), request=request)
        self.tasks[task.id] = task
        self._event(task, "task.received", "Natural-language request received.")

        task.status = TaskStatus.CONTEXT
        task.references = clod_context_search_mock()
        task.confidence = 88 if len(request) > 80 else 64
        task.prompt = rewrite_request(request, task.references)
        self._event(task, "context.search.completed", "Clod context mock returned reference repositories.")
        self._event(task, "prompt.expanded", "Person C prompt template generated Markdown brief.")

        task.status = TaskStatus.RISK
        task.risks = risk_preflight_mock()
        task.prompt = append_risk_guide(task.prompt, task.risks)
        self._event(task, "risk.preflight.completed", "AI preflight appended negative constraints.")

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
            model="GPT OSS 120B",
            provider="Clod.io fallback route",
        )
        self._event(task, "compute.route.selected", f"Selected {task.route.model}.")
        self._event(task, "generation.started", "Mock execution workspace started.")
        task.code = CodeArtifact(
            title="transactionSigningGuard.ts",
            language="ts",
            summary="Generated transaction signing guard and regression-test target.",
            patch=(
                "export function assertSafeTransaction(tx: PreparedTransaction) {\n"
                "  if (!tx.chainId) throw new Error('Missing chainId');\n"
                "  if (tx.approval === 'unbounded') throw new Error('Unbounded approval requires explicit user approval');\n"
                "  if (tx.chainId !== tx.expectedChainId) throw new Error('Cross-chain replay risk');\n"
                "  return tx;\n"
                "}"
            ),
        )
        self._event(task, "generation.completed", task.code.summary)

        task.status = TaskStatus.SANDBOX
        self._run_sandbox_until_done(task)
        return task

    def reject(self, task_id: int) -> Task:
        task = self.tasks[task_id]
        task.status = TaskStatus.REJECTED
        self._event(task, "hitl.rejected", "Human reviewer rejected task before execution.")
        return task

    def _run_sandbox_until_done(self, task: Task) -> None:
        while True:
            status, tests = trex_sandbox_mock(task.repair_attempts)
            task.review = ReviewResult(
                status=status,
                tests=tests,
                summary=(
                    "TREX sandbox found one missing rejection test for cross-chain payload replay."
                    if status == "failed"
                    else "Sandbox checks passed after greploop repair."
                ),
            )
            self._event(task, "sandbox.review.completed", task.review.summary)

            if status == "passed":
                task.status = TaskStatus.FINISHED
                self._event(task, "workflow.finished", "FINISHED with code, tests, and repair log.")
                return

            if task.repair_attempts >= task.max_iterations:
                task.status = TaskStatus.FAILED
                self._event(task, "workflow.failed", "Max greploop iterations reached.")
                return

            task.repair_attempts += 1
            task.status = TaskStatus.REPAIR
            self._event(task, "repair.started", f"Greploop repair {task.repair_attempts} started.")
            self._event(task, "repair.completed", f"Greploop repair {task.repair_attempts} completed.")
            task.status = TaskStatus.SANDBOX

    def _event(self, task: Task, event_type: str, detail: str) -> None:
        task.events.insert(
            0,
            WorkflowEvent(
                id=len(task.events) + 1,
                type=event_type,
                detail=detail,
                timestamp=strftime("%H:%M:%S"),
            ),
        )
