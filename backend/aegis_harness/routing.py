from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RouteDecision:
    difficulty: int
    model: str
    provider: str
    budget: str
    latency: str
    rationale: str


SECURITY_PATTERN = re.compile(r"wallet|auth|payment|permission|security|audit|transaction", re.I)
MIGRATION_PATTERN = re.compile(r"migration|refactor|schema|compatibility|legacy", re.I)


def calculate_difficulty(confidence: int, risk_count: int, request: str) -> int:
    security_weight = 1 if SECURITY_PATTERN.search(request) else 0
    migration_weight = 1 if MIGRATION_PATTERN.search(request) else 0
    ambiguity_penalty = 1 if confidence < 75 else 0
    return min(5, max(1, 1 + ((risk_count + 1) // 2) + security_weight + migration_weight + ambiguity_penalty))


def route_for_task(
    confidence: int,
    risk_count: int,
    request: str,
    *,
    model: str,
    provider: str,
) -> RouteDecision:
    difficulty = calculate_difficulty(confidence, risk_count, request)
    high_difficulty = difficulty >= 4
    return RouteDecision(
        difficulty=difficulty,
        model=model,
        provider=provider,
        budget="$4.80 cap" if high_difficulty else "$1.20 cap",
        latency="balanced reasoning window" if high_difficulty else "fast coding lane",
        rationale=(
            f"Security-sensitive or compatibility-heavy work runs through {model} with a stricter budget cap."
            if high_difficulty
            else f"Moderate implementation risk uses {model} through the faster provider lane."
        ),
    )
