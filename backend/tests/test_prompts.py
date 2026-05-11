"""Tests for aegis_harness.prompts — template rendering and risk injection."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_harness.prompts import (
    ReferenceRepo,
    RiskFinding,
    append_risk_guide,
    rewrite_request,
)


# ---------------------------------------------------------------------------
# rewrite_request
# ---------------------------------------------------------------------------

class TestRewriteRequest:
    def test_contains_user_request(self):
        refs = [ReferenceRepo("owner/repo", "1k", "some signal")]
        result = rewrite_request("build a wallet", refs)
        assert "build a wallet" in result

    def test_contains_reference_name(self):
        refs = [ReferenceRepo("my/repo", "500", "relevant")]
        result = rewrite_request("anything", refs)
        assert "my/repo" in result

    def test_contains_signal(self):
        refs = [ReferenceRepo("a/b", "n/a", "unique-signal-xyz")]
        result = rewrite_request("anything", refs)
        assert "unique-signal-xyz" in result

    def test_multiple_references_all_included(self):
        refs = [
            ReferenceRepo("a/one", "1k", "signal-one"),
            ReferenceRepo("b/two", "2k", "signal-two"),
        ]
        result = rewrite_request("task", refs)
        assert "a/one" in result
        assert "b/two" in result

    def test_empty_references_does_not_crash(self):
        result = rewrite_request("task", [])
        assert "task" in result

    def test_returns_string(self):
        result = rewrite_request("task", [])
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# append_risk_guide
# ---------------------------------------------------------------------------

class TestAppendRiskGuide:
    BASE_PROMPT = "## System Prompt\nDo stuff."

    def test_header_present(self):
        risks = [RiskFinding("Bad thing", "high", "Fix it")]
        result = append_risk_guide(self.BASE_PROMPT, risks)
        assert "## Negative Constraints From AI Preflight" in result

    def test_risk_title_present(self):
        risks = [RiskFinding("UniqueRiskTitle", "critical", "Do X")]
        result = append_risk_guide(self.BASE_PROMPT, risks)
        assert "UniqueRiskTitle" in result

    def test_severity_uppercased_in_output(self):
        risks = [RiskFinding("A risk", "medium", "Mitigate it")]
        result = append_risk_guide(self.BASE_PROMPT, risks)
        assert "[MEDIUM]" in result

    def test_mitigation_included(self):
        risks = [RiskFinding("Risk", "low", "unique-mitigation-string")]
        result = append_risk_guide(self.BASE_PROMPT, risks)
        assert "unique-mitigation-string" in result

    def test_original_prompt_preserved(self):
        risks = [RiskFinding("R", "low", "M")]
        result = append_risk_guide(self.BASE_PROMPT, risks)
        assert self.BASE_PROMPT in result

    def test_empty_risks_preserves_prompt(self):
        result = append_risk_guide(self.BASE_PROMPT, [])
        assert self.BASE_PROMPT in result

    def test_multiple_risks_all_included(self):
        risks = [
            RiskFinding("Risk Alpha", "critical", "Fix A"),
            RiskFinding("Risk Beta", "high", "Fix B"),
            RiskFinding("Risk Gamma", "low", "Fix C"),
        ]
        result = append_risk_guide(self.BASE_PROMPT, risks)
        for r in risks:
            assert r.title in result
            assert r.mitigation in result

    def test_all_severities_uppercase(self):
        for sev in ("critical", "high", "medium", "low"):
            risks = [RiskFinding("T", sev, "M")]
            result = append_risk_guide(self.BASE_PROMPT, risks)
            assert f"[{sev.upper()}]" in result


# ---------------------------------------------------------------------------
# ReferenceRepo / RiskFinding dataclasses
# ---------------------------------------------------------------------------

class TestDataclasses:
    def test_reference_repo_frozen(self):
        repo = ReferenceRepo("owner/repo", "1k", "signal")
        with pytest.raises((AttributeError, TypeError)):
            repo.name = "changed"  # type: ignore[misc]

    def test_risk_finding_frozen(self):
        risk = RiskFinding("title", "high", "mitigation")
        with pytest.raises((AttributeError, TypeError)):
            risk.severity = "low"  # type: ignore[misc]
