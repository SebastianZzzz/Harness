"""Tests for backend/app models — state enums and Pydantic schemas."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.state import (
    ApprovalRequest,
    CodeTask,
    SearchProvider,
    TaskPhase,
)


class TestSearchProvider:
    def test_nia_value(self):
        assert SearchProvider.NIA == "nia"

    def test_github_value(self):
        assert SearchProvider.GITHUB == "github"

    def test_from_string(self):
        assert SearchProvider("github") == SearchProvider.GITHUB
        assert SearchProvider("nia") == SearchProvider.NIA

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            SearchProvider("unknown")


class TestTaskPhase:
    def test_all_phases_defined(self):
        phases = [p.value for p in TaskPhase]
        assert "1_INTENT_PARSING" in phases
        assert "2_PRECHECK_GREPTILE" in phases
        assert "3_HUMAN_IN_THE_LOOP" in phases
        assert "4_COMPUTE_ROUTING" in phases
        assert "5_SANDBOX_TESTING" in phases
        assert "FINISHED" in phases
        assert "FAILED" in phases

    def test_from_string(self):
        assert TaskPhase("FINISHED") == TaskPhase.FINISHED
        assert TaskPhase("FAILED") == TaskPhase.FAILED


class TestCodeTask:
    def _minimal(self, **kwargs):
        defaults = dict(
            id="test-id-123",
            original_prompt="Build a wallet",
        )
        defaults.update(kwargs)
        return CodeTask(**defaults)

    def test_defaults(self):
        task = self._minimal()
        assert task.current_phase == TaskPhase.PHASE_1_INTENT
        assert task.search_provider == SearchProvider.GITHUB
        assert task.bug_list_constraints == []
        assert task.sandbox_iterations == 0
        assert task.max_iterations == 3

    def test_optional_fields_none(self):
        task = self._minimal()
        assert task.structured_prompt is None
        assert task.difficulty_score is None
        assert task.selected_model is None
        assert task.generated_code is None

    def test_custom_values(self):
        task = self._minimal(
            structured_prompt="## Structured",
            difficulty_score=4,
            selected_model="gpt-4o",
            generated_code="def foo(): pass",
            sandbox_iterations=2,
            max_iterations=5,
        )
        assert task.structured_prompt == "## Structured"
        assert task.difficulty_score == 4
        assert task.selected_model == "gpt-4o"
        assert task.generated_code == "def foo(): pass"
        assert task.sandbox_iterations == 2
        assert task.max_iterations == 5

    def test_bug_list_constraints_list(self):
        task = self._minimal(bug_list_constraints=["no SQL injection", "validate inputs"])
        assert len(task.bug_list_constraints) == 2


class TestApprovalRequest:
    def test_approved_true(self):
        req = ApprovalRequest(approved=True)
        assert req.approved is True
        assert req.edited_prompt is None

    def test_approved_false(self):
        req = ApprovalRequest(approved=False)
        assert req.approved is False

    def test_with_edited_prompt(self):
        req = ApprovalRequest(approved=True, edited_prompt="## New prompt")
        assert req.edited_prompt == "## New prompt"

    def test_missing_approved_raises(self):
        with pytest.raises((TypeError, Exception)):
            ApprovalRequest()  # type: ignore[call-arg]
