# AegisHarness

AegisHarness is an agentic compiler and guardrail console for safer AI coding. It turns a natural-language request into a structured agent brief, parses real-world open-source context, pauses for human approval, and runs generated code through a real GitHub sandbox with automated bot reviews.

## Current Scope

- **Frontend MVP**: Vite + React + TypeScript workflow console.
- **Python Backend**: FastAPI + SQLAlchemy + Uvicorn with persistent task state.
- **AI Infrastructure**: Gemini-first routing with Clod.io fallback.
- **Real-World Context**: Integrated with GitHub Search and Greptile for repository analysis.
- **Agentic Sandbox**: Real GitHub PR loop with automated code reviews and self-repair.

## Five Phases

1. **Intent Parsing & Context Building**
   - Uses **TryniaService** to find top-starred GitHub repositories matching the user's intent.
   - AI validates repository relevance before extracting patterns.
   - Rewrites vague requests into a detailed, structured engineering specification.

2. **Preflight Bug-List Generation**
   - Uses **GreptileService** to fetch and analyze READMEs from similar repositories.
   - Extracts common bugs, security vulnerabilities, and anti-patterns.
   - Appends these as negative constraints to the final agent brief.

3. **Human-in-the-Loop (HITL) Confirmation**
   - Pauses at `PENDING_APPROVAL`.
   - Allows users to review, edit, or reject the structured brief and bug list.

4. **Compute Routing & Generation**
   - Scores task difficulty (1-5) and routes to the most cost-effective model via **Clod.io**.
   - Generates code artifacts strictly adhering to the preflight constraints.

5. **GitHub Sandbox & GrepLoop Repair**
   - Uses **GitHubService** to commit code to a dedicated sandbox repository.
   - Opens a real Pull Request and waits for the **Greptile App** bot review.
   - If the bot finds issues, the feedback is fed back into Phase 4 for regeneration (up to 3 iterations).

## Getting Started

### 1. Setup Environment

Create the conda environment and install dependencies:

```bash
conda env create -f environment.yml
conda activate aegis-harness
pip install -r backend/requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the root directory (see `.env.example`):

```text
GEMINI_API_KEY=your_key
CLOD_API_KEY=your_key
GITHUB_TOKEN=your_github_classic_token
GREPTILE_API_KEY=your_key
NIA_API_KEY=your_key
```

### 3. Run the Project

- **Backend (FastAPI)**: `npm run backend` (Runs on port 8000)
- **Frontend (Vite)**: `npm run dev` (Runs on port 5173)
- **Full Test Suite**: `npm run test:python` (Runs 100+ pytest cases)

## Repository Layout

```text
src/                         # Frontend workflow console
backend/aegis_harness/       # AI logic, state machine & prompting
backend/app/                 # FastAPI routers, services, & ORM
backend/tests/               # 106-case comprehensive test suite
docs/                        # Architecture & system prompts
pyproject.toml               # Pytest configuration
package.json                 # Project scripts
```

## Demo Path

1. Select a demo case (e.g., **Wallet Signing Audit**).
2. Click **Build Agent Brief** — watch Phase 1 & 2 search GitHub and analyze READMEs.
3. Review the **Negative Constraints** and the expanded prompt.
4. Click **Approve and Execute**.
5. Phase 5 will open a real PR on GitHub, wait for the Greptile bot review, and perform a self-repair if needed.
