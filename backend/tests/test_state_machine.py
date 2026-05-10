"""Tests for aegis_harness.state_machine — mock backend state transitions."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_harness.state_machine import AegisHarnessMockBackend, Task, TaskStatus


SHORT_REQUEST = "fix bug"
LONG_REQUEST = "Audit a TypeScript wallet integration for unsafe transaction signing and add regression tests for replay attack prevention."


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------

class TestMockBackendStart:
    def setup_method(self):
        self.backend = AegisHarnessMockBackend()

    def test_task_registered(self):
        task = self.backend.start(SHORT_REQUEST)
        assert task.id in self.backend.tasks

    def test_status_pending_approval(self):
        task = self.backend.start(SHORT_REQUEST)
        assert task.status == TaskStatus.PENDING_APPROVAL

    def test_prompt_contains_negative_constraints(self):
        task = self.backend.start(LONG_REQUEST)
        assert "Negative Constraints From AI Preflight" in task.prompt

    def test_references_populated(self):
        task = self.backend.start(SHORT_REQUEST)
        assert len(task.references) > 0

    def test_risks_populated(self):
        task = self.backend.start(SHORT_REQUEST)
        assert len(task.risks) > 0

    def test_confidence_short_request(self):
        task = self.backend.start(SHORT_REQUEST)
        assert task.confidence == 64

    def test_confidence_long_request(self):
        task = self.backend.start(LONG_REQUEST)
        assert task.confidence == 88

    def test_events_recorded(self):
        task = self.backend.start(SHORT_REQUEST)
        event_types = {e.type for e in task.events}
        assert "task.received" in event_types
        assert "risk.preflight.completed" in event_types
        assert "hitl.approval.requested" in event_types

    def test_multiple_tasks_get_unique_ids(self):
        t1 = self.backend.start(SHORT_REQUEST)
        t2 = self.backend.start(SHORT_REQUEST)
        assert t1.id != t2.id

    def test_returns_task_instance(self):
        assert isinstance(self.backend.start(SHORT_REQUEST), Task)


# ---------------------------------------------------------------------------
# approve()
# ---------------------------------------------------------------------------

class TestMockBackendApprove:
    def setup_method(self):
        self.backend = AegisHarnessMockBackend()
        self.task = self.backend.start(LONG_REQUEST)

    def test_finished_status(self):
        finished = self.backend.approve(self.task.id)
        assert finished.status == TaskStatus.FINISHED

    def test_repair_attempts_bounded(self):
        finished = self.backend.approve(self.task.id)
        assert finished.repair_attempts <= finished.max_iterations

    def test_sandbox_review_passed(self):
        finished = self.backend.approve(self.task.id)
        assert finished.review.status == "passed"

    def test_code_artifact_present(self):
        finished = self.backend.approve(self.task.id)
        assert finished.code is not None
        assert finished.code.patch

    def test_route_present(self):
        finished = self.backend.approve(self.task.id)
        assert finished.route is not None

    def test_route_difficulty_for_security_task(self):
        finished = self.backend.approve(self.task.id)
        assert finished.route.difficulty >= 4

    def test_approved_prompt_override(self):
        custom_prompt = "## Custom Override Prompt\nDo exactly this."
        finished = self.backend.approve(self.task.id, approved_prompt=custom_prompt)
        assert finished.prompt == custom_prompt

    def test_workflow_finished_event(self):
        finished = self.backend.approve(self.task.id)
        event_types = [e.type for e in finished.events]
        assert "workflow.finished" in event_types

    def test_hitl_approved_event(self):
        finished = self.backend.approve(self.task.id)
        event_types = [e.type for e in finished.events]
        assert "hitl.approved" in event_types

    def test_approve_wrong_status_raises(self):
        self.backend.approve(self.task.id)  # advance to FINISHED
        with pytest.raises(ValueError, match="not awaiting approval"):
            self.backend.approve(self.task.id)

    def test_generation_completed_event(self):
        finished = self.backend.approve(self.task.id)
        event_types = [e.type for e in finished.events]
        assert "generation.completed" in event_types


# ---------------------------------------------------------------------------
# reject()
# ---------------------------------------------------------------------------

class TestMockBackendReject:
    def setup_method(self):
        self.backend = AegisHarnessMockBackend()
        self.task = self.backend.start(SHORT_REQUEST)

    def test_rejected_status(self):
        rejected = self.backend.reject(self.task.id)
        assert rejected.status == TaskStatus.REJECTED

    def test_rejected_event_recorded(self):
        rejected = self.backend.reject(self.task.id)
        event_types = [e.type for e in rejected.events]
        assert "hitl.rejected" in event_types

    def test_cannot_approve_after_rejection(self):
        self.backend.reject(self.task.id)
        with pytest.raises(ValueError):
            self.backend.approve(self.task.id)


# ---------------------------------------------------------------------------
# to_dict()
# ---------------------------------------------------------------------------

class TestTaskToDict:
    def test_to_dict_has_status_string(self):
        backend = AegisHarnessMockBackend()
        task = backend.start(SHORT_REQUEST)
        d = task.to_dict()
        assert isinstance(d["status"], str)
        assert d["status"] == "PENDING_APPROVAL"

    def test_to_dict_serialisable_keys(self):
        import json
        backend = AegisHarnessMockBackend()
        task = backend.start(SHORT_REQUEST)
        # Should not raise
        json.dumps(task.to_dict(), default=str)
