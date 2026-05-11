"""Tests for aegis_harness.adapters — mock data contract."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_harness.adapters import clod_context_search_mock, risk_preflight_mock, trex_sandbox_mock
from aegis_harness.prompts import ReferenceRepo, RiskFinding


class TestClodContextSearchMock:
    def test_returns_list(self):
        result = clod_context_search_mock()
        assert isinstance(result, list)

    def test_returns_reference_repos(self):
        for item in clod_context_search_mock():
            assert isinstance(item, ReferenceRepo)

    def test_nonempty(self):
        assert len(clod_context_search_mock()) > 0

    def test_all_have_names(self):
        for r in clod_context_search_mock():
            assert r.name and "/" in r.name

    def test_all_have_signals(self):
        for r in clod_context_search_mock():
            assert r.signal


class TestRiskPreflightMock:
    def test_returns_list(self):
        assert isinstance(risk_preflight_mock(), list)

    def test_returns_risk_findings(self):
        for item in risk_preflight_mock():
            assert isinstance(item, RiskFinding)

    def test_nonempty(self):
        assert len(risk_preflight_mock()) > 0

    def test_severities_are_valid(self):
        valid = {"critical", "high", "medium", "low"}
        for r in risk_preflight_mock():
            assert r.severity in valid, f"Invalid severity: {r.severity!r}"

    def test_all_have_titles_and_mitigations(self):
        for r in risk_preflight_mock():
            assert r.title
            assert r.mitigation


class TestTrexSandboxMock:
    def test_first_attempt_fails(self):
        status, tests = trex_sandbox_mock(0)
        assert status == "failed"

    def test_second_attempt_passes(self):
        status, tests = trex_sandbox_mock(1)
        assert status == "passed"

    def test_returns_test_list(self):
        _, tests = trex_sandbox_mock(0)
        assert isinstance(tests, list)
        assert len(tests) > 0

    def test_passed_tests_all_pass(self):
        _, tests = trex_sandbox_mock(1)
        for t in tests:
            assert "passed" in t

    def test_failed_tests_include_failures(self):
        _, tests = trex_sandbox_mock(0)
        has_failure = any("failed" in t for t in tests)
        assert has_failure
