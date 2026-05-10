"""Tests for aegis_harness.routing — difficulty calculation and route decisions."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_harness.routing import RouteDecision, calculate_difficulty, route_for_task


# ---------------------------------------------------------------------------
# calculate_difficulty
# ---------------------------------------------------------------------------

class TestCalculateDifficulty:
    def test_minimum_is_1(self):
        assert calculate_difficulty(100, 0, "simple task") >= 1

    def test_maximum_is_5(self):
        # Pile on everything: low confidence, many risks, security + migration keyword
        score = calculate_difficulty(10, 20, "wallet migration schema security audit")
        assert score <= 5

    def test_security_keyword_raises_difficulty(self):
        base = calculate_difficulty(80, 2, "refactor code")
        with_security = calculate_difficulty(80, 2, "audit wallet security")
        assert with_security >= base

    def test_migration_keyword_raises_difficulty(self):
        base = calculate_difficulty(80, 2, "add a feature")
        with_migration = calculate_difficulty(80, 2, "schema migration refactor")
        assert with_migration >= base

    def test_low_confidence_adds_penalty(self):
        high_conf = calculate_difficulty(90, 2, "add logging")
        low_conf = calculate_difficulty(70, 2, "add logging")
        assert low_conf >= high_conf

    def test_more_risks_increases_difficulty(self):
        few = calculate_difficulty(80, 1, "task")
        many = calculate_difficulty(80, 6, "task")
        assert many >= few

    def test_returns_int(self):
        assert isinstance(calculate_difficulty(80, 2, "task"), int)

    @pytest.mark.parametrize("keyword", ["wallet", "auth", "payment", "permission", "security", "audit", "transaction"])
    def test_all_security_keywords_detected(self, keyword):
        base = calculate_difficulty(80, 2, "mundane task")
        with_kw = calculate_difficulty(80, 2, f"{keyword} task")
        assert with_kw >= base

    @pytest.mark.parametrize("keyword", ["migration", "refactor", "schema", "compatibility", "legacy"])
    def test_all_migration_keywords_detected(self, keyword):
        base = calculate_difficulty(80, 2, "mundane task")
        with_kw = calculate_difficulty(80, 2, f"{keyword} task")
        assert with_kw >= base


# ---------------------------------------------------------------------------
# route_for_task
# ---------------------------------------------------------------------------

class TestRouteForTask:
    MODEL = "TestModel-XL"
    PROVIDER = "test-provider"

    def _route(self, confidence=80, risk_count=2, request="add logging"):
        return route_for_task(
            confidence, risk_count, request,
            model=self.MODEL, provider=self.PROVIDER,
        )

    def test_returns_route_decision(self):
        assert isinstance(self._route(), RouteDecision)

    def test_model_and_provider_passed_through(self):
        r = self._route()
        assert r.model == self.MODEL
        assert r.provider == self.PROVIDER

    def test_high_difficulty_budget_cap(self):
        # wallet + many risks → difficulty >= 4 → $4.80 cap
        r = route_for_task(80, 6, "wallet security audit", model=self.MODEL, provider=self.PROVIDER)
        assert r.budget == "$4.80 cap"

    def test_low_difficulty_budget_cap(self):
        # plain task, high confidence, few risks → fast lane
        r = route_for_task(90, 0, "add a comment", model=self.MODEL, provider=self.PROVIDER)
        assert r.budget == "$1.20 cap"

    def test_high_difficulty_latency_label(self):
        r = route_for_task(80, 6, "wallet security audit", model=self.MODEL, provider=self.PROVIDER)
        assert "balanced reasoning window" in r.latency

    def test_low_difficulty_latency_label(self):
        r = route_for_task(90, 0, "add a comment", model=self.MODEL, provider=self.PROVIDER)
        assert "fast coding lane" in r.latency

    def test_rationale_contains_model_name(self):
        r = self._route()
        assert self.MODEL in r.rationale

    def test_difficulty_in_range(self):
        r = self._route()
        assert 1 <= r.difficulty <= 5
