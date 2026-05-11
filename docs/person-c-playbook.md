# Person C Playbook

Person C owns prompt quality, routing standards, integration tests, demo cases, and pitch logic. The live backend should call Gemini before Clod while keeping deterministic tests for the workflow contract.

## Prompt Rewrite Template

Every vague request becomes a Markdown system prompt with:

- Mission
- User request
- Retrieved repository context
- Structured requirements
- Acceptance criteria
- Unknowns to confirm
- Negative constraints from AI preflight

Hard rule: do not allow execution before the user approves or edits this prompt.

## Negative Constraint Format

```text
- [SEVERITY] Known issue: mitigation that the agent must obey.
```

Examples:

- `[CRITICAL] Overbroad token approvals: reject unlimited approvals unless explicitly approved.`
- `[HIGH] Silent chain mismatch: require explicit chain ID checks before signing.`
- `[MEDIUM] Mock-only regression tests: test payload validation and user-facing failure states.`

## Difficulty Scoring Rubric

Start at `1`, then add:

- `+ceil(risk_count / 2)` for AI preflight risk density
- `+1` for security, wallet, auth, payment, or permission work
- `+1` for migration, schema, refactor, compatibility, or legacy work
- `+1` when confidence is below `75`

Clamp to `1-5`.

Routing rule:

- All AI calls use Gemini first, then Clod fallback.
- `1-3`: fast provider lane with lower budget cap
- `4-5`: stricter provider lane with larger budget cap and longer reasoning window

## Demo Cases

1. Wallet signing audit
   - Shows security risk, HITL approval, stronger route, sandbox failure, one repair, and `FINISHED`.

2. CI flake stabilizer
   - Shows that vague debugging can become deterministic test-helper work.

3. API schema migration
   - Shows compatibility risk and why route difficulty increases.

## Integration Test Contract

The end-to-end test must assert:

- Task pauses at `PENDING_APPROVAL`.
- Prompt contains AI preflight negative constraints.
- Approval is required before routing.
- Route decision includes difficulty and model.
- Sandbox failure triggers repair.
- Repair attempts never exceed `max_iterations = 3`.
- Final status is `FINISHED`.
- No settlement/payment event exists in the simplified architecture.

## Pitch Logic

Use this framing:

- AegisHarness is not an auto-coder; it is a compiler pipeline for agent work.
- HITL prevents silent failure before expensive execution.
- Difficulty routing prevents compute waste.
- AI preflight converts historical failure patterns into negative constraints.
- Bounded greploop makes repair useful without becoming an API-budget black hole.

## Environment Variables

Copy the root template before adding real keys:

```bash
cp .env.example .env.local
```

Required once real adapters are enabled:

- `GEMINI_API_KEY`
- `GEMINI_MODEL=gemini-2.5-pro`
- `CLOD_API_KEY`
- `CLOD_MODEL=GPT OSS 120B`

Provider priority is Gemini first, then Clod fallback.
