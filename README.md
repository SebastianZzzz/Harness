# AegisHarness

AegisHarness is a self-healing agentic compiler and guardrail console. It transforms natural-language intents into structured briefs, requires human approval, and tests code in a live GitHub sandbox with bot reviews.

# Authors

- @SebastianZzzz (Sebastian Zhu)
- @li-yiou (Yiou Li)
- @budengjun (Yaolong Hu)

## Current Scope

- **Frontend MVP**: Vite + React + TypeScript workflow console with BYOK (Bring-Your-Own-Key) support.
- **Python Backend**: FastAPI + SQLAlchemy + Uvicorn with robust state machine tracking.
- **AI Infrastructure**: Gemini-first routing with dynamic Clod.io model escalation.
- **Real-World Context**: Integrated with GitHub Search and Greptile for repository analysis.
- **Self-Healing Sandbox**: Real GitHub PR loop with automated bot reviews and context-aware repair.

## The Agentic Pipeline

0. **Initialization & Configuration (0_INIT)**
   - Decoupled task creation.
   - Securely accepts user-provided GitHub Token and Target Repo credentials (BYOK).

1. **Intent Parsing & Context Building**
   - Uses **TryniaService** to find top-starred GitHub repositories matching the user's intent.
   - AI validates repository relevance and expands requests into detailed engineering specifications.

2. **Preflight Bug-List Generation**
   - Uses **GreptileService** to fetch and analyze READMEs from similar repositories.
   - Appends extracted anti-patterns as negative constraints to the agent brief.

3. **Human-in-the-Loop (HITL) Confirmation**
   - Pauses at `PENDING_APPROVAL`.
   - Allows users to review, edit, or reject the structured brief.

4. **Compute Routing & Generation**
   - Scores task difficulty and routes to a fast, cost-effective model (e.g., `clod-unified-smart`).
   - Generates code artifacts adhering to the preflight constraints.

5. **GitHub Sandbox Testing**
   - Uses **GitHubService** to commit code to a user's target repository.
   - Reuses existing PR branches and waits for real Greptile bot reviews.

6. **Contextual Rewriting & Self-Repair (6_REWRITING)**
   - If the bot finds issues, feedback and the *previous code* are fed back into the model.
   - Dynamically escalates to the most powerful model (`clod-unified-max`) for precise bug fixing (up to 3 iterations).

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
