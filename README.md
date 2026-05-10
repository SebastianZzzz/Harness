# AegisHarness

AegisHarness is an agentic compiler and guardrail console for safer AI coding. It turns a natural-language request into a structured agent brief, pauses for human approval, routes compute by difficulty, and runs generated code through a bounded sandbox repair loop.

This MVP follows the simplified five-phase architecture with live server-side AI calls. Gemini is used first when configured, with Clod as fallback.

## Current Scope

- Frontend MVP: Vite + React + TypeScript
- Python backend core: standard library only, conda-runnable
- Person C assets: prompt template, difficulty rubric, demo cases, pitch notes, integration test
- API mode: Gemini-first AI calls with Clod fallback
- Terminal state: `FINISHED` after sandbox verification

## Five Phases

1. Intent parsing and zero-hallucination context building
   - Gemini is used first for context and prompt rewriting when `GEMINI_API_KEY` is set.
   - Clod is used as fallback when Gemini is not configured.
   - Person C prompt template rewrites vague input into a structured Markdown system prompt.

2. Preflight warning and bug-list generation
   - The active AI provider returns common implementation and security risks.
   - Risks are appended as negative constraints in the HITL brief.

3. Human-in-the-loop confirmation
   - State machine pauses at `PENDING_APPROVAL`.
   - User can edit, approve, reject, or clarify the Markdown brief.

4. Compute estimation and dynamic routing
   - The backend scores task difficulty from 1 to 5.
   - The route records the active AI provider/model, preferring Gemini before Clod.

5. Sandboxed testing and self-repair
   - The active AI provider reviews the generated artifact in the current MVP.
   - `/greploop` repair is bounded by `max_iterations = 3`.
   - Passing sandbox results move the task to `FINISHED`.

## Run The Frontend

```bash
npm install
npm run dev
```

Build and lint:

```bash
npm run lint
npm run build
```

## API Keys

Use [.env.example](/Users/yaolonghu/Desktop/Harness/.env.example) as the template:

```bash
cp .env.example .env.local
```

Then fill in:

```text
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-pro
CLOD_API_KEY=...
CLOD_MODEL=GPT OSS 120B
```

Provider priority is Gemini first, then Clod. Keep `CLOD_API_KEY` available as a fallback.

## Run Python Integration Tests With Conda

Create the environment:

```bash
conda env create -f environment.yml
```

Run the backend integration test:

```bash
conda run -n aegis-harness python -m unittest discover -s backend/tests
```

## Repository Layout

```text
src/                         # Frontend workflow console
backend/aegis_harness/       # Conda-runnable backend core
backend/tests/               # Person C integration test
docs/person-c-playbook.md    # Prompt, routing, demos, pitch notes
docs/architecture.md         # Five-phase architecture contract
docs/ide-agent-system-prompt.md
environment.yml
```

## Demo Path

1. Choose the wallet signing audit demo case.
2. Click `Build Agent Brief`.
3. Review the Markdown prompt and risk guide at `PENDING_APPROVAL`.
4. Click `Approve and Execute`.
5. Watch routing, generation, sandbox failure, one greploop repair, sandbox pass, and `FINISHED`.
