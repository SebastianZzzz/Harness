from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceRepo:
    name: str
    stars: str
    signal: str


@dataclass(frozen=True)
class RiskFinding:
    title: str
    severity: str
    mitigation: str


SYSTEM_PROMPT_TEMPLATE = """# Agent System Prompt

## Mission
Transform the user's request into a narrow, reviewable code change. Do not infer hidden requirements. Surface ambiguity before generation.

## User Request
{request}

## Retrieved Context
{references}

## Structured Requirements
- Locate the implementation surface before editing.
- Preserve existing public APIs unless a security guard requires an explicit type change.
- Add deterministic regression tests for every risky behavior changed.
- Return a maintainer-readable patch summary and test evidence.

## Acceptance Criteria
- Static checks pass.
- Tests include at least one failure-path assertion.
- The patch remains scoped to the approved request.

## Unknowns To Confirm
- Target repository conventions.
- Existing test runner and CI command.
- Whether the project allows breaking API changes.
"""


def rewrite_request(request: str, references: list[ReferenceRepo]) -> str:
    reference_lines = "\n".join(
        f"- {repo.name} ({repo.stars}): {repo.signal}" for repo in references
    )
    return SYSTEM_PROMPT_TEMPLATE.format(request=request, references=reference_lines)


def append_risk_guide(prompt: str, risks: list[RiskFinding]) -> str:
    risk_lines = "\n".join(
        f"- [{risk.severity.upper()}] {risk.title}: {risk.mitigation}" for risk in risks
    )
    return f"""{prompt}

## Negative Constraints From AI Preflight
{risk_lines}
"""

