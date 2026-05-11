from __future__ import annotations

from .prompts import ReferenceRepo, RiskFinding


def clod_context_search_mock() -> list[ReferenceRepo]:
    return [
        ReferenceRepo(
            name="safe-global/safe-smart-account",
            stars="2.4k",
            signal="High-signal multisig transaction validation patterns",
        ),
        ReferenceRepo(
            name="OpenZeppelin/openzeppelin-contracts",
            stars="25k",
            signal="Battle-tested access control and security test conventions",
        ),
        ReferenceRepo(
            name="wevm/wagmi",
            stars="9.8k",
            signal="Typed wallet interaction and connector ergonomics",
        ),
    ]


def risk_preflight_mock() -> list[RiskFinding]:
    return [
        RiskFinding(
            title="Silent chain mismatch",
            severity="high",
            mitigation="Require explicit chain ID checks before signing or broadcasting.",
        ),
        RiskFinding(
            title="Overbroad token approvals",
            severity="critical",
            mitigation="Reject unlimited approvals unless the user explicitly approved that policy.",
        ),
        RiskFinding(
            title="Mock-only regression tests",
            severity="medium",
            mitigation="Test both payload validation and user-facing failure states.",
        ),
        RiskFinding(
            title="Hidden retry loop",
            severity="medium",
            mitigation="Cap repair attempts and persist each failure reason.",
        ),
    ]


def trex_sandbox_mock(attempt: int) -> tuple[str, list[str]]:
    if attempt == 0:
        return (
            "failed",
            ["typecheck: passed", "unit: failed", "security-regression: failed"],
        )
    return (
        "passed",
        ["typecheck: passed", "unit: passed", "security-regression: passed"],
    )
