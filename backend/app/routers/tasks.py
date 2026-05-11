import uuid
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.state import CodeTask, TaskPhase, ApprovalRequest, SearchProvider, GitHubConfig, StartRequest, TaskCreateRequest
from app.models.orm import TaskRecord
from app.database import get_db, AsyncSessionLocal

from app.services.trynia_service import TryniaService
from app.services.greptile_service import GreptileService
from app.services.clod_service import ClodService
from app.services.github_service import GitHubService
from app.routers.websocket import manager

router = APIRouter()

# Demo Target Repository for Greptile Sandbox
TARGET_REPO = "sebastianZzzz/Harness"

async def get_task_by_id(db: AsyncSession, task_id: str) -> TaskRecord:
    result = await db.execute(select(TaskRecord).where(TaskRecord.id == task_id))
    return result.scalar_one_or_none()

def record_to_pydantic(record: TaskRecord) -> CodeTask:
    if not record: return None
    return CodeTask(
        id=record.id,
        original_prompt=record.original_prompt,
        structured_prompt=record.structured_prompt,
        bug_list_constraints=record.bug_list_constraints or [],
        current_phase=TaskPhase(record.current_phase),
        search_provider=SearchProvider(record.search_provider or "github"),
        difficulty_score=record.difficulty_score,
        selected_model=record.selected_model,
        generated_code=record.generated_code,
        sandbox_iterations=record.sandbox_iterations,
        max_iterations=record.max_iterations,
        target_repo=record.target_repo,  # expose repo; token is NEVER returned
        created_at=record.created_at,
        updated_at=record.updated_at
    )

@router.post("/{task_id}/config", summary="Set user GitHub credentials (BYOK)")
async def set_github_config(task_id: str, config: GitHubConfig, db: AsyncSession = Depends(get_db)):
    """
    Allow the frontend to provide a user's own GitHub token and target repository.
    The token is stored only for this task's lifecycle and is never returned to the client.
    """
    record = await get_task_by_id(db, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    record.github_token = config.github_token
    record.target_repo = config.target_repo
    await db.commit()
    return {"status": "ok", "target_repo": config.target_repo}

@router.post("/", response_model=CodeTask)
async def create_task(background_tasks: BackgroundTasks, body: Optional[TaskCreateRequest] = None, prompt: Optional[str] = None, search_provider: SearchProvider = SearchProvider.GITHUB, db: AsyncSession = Depends(get_db)):
    """
    Create a new task. If body/prompt is provided, immediately triggers Phase 1 & 2 (Legacy behavior).
    If no prompt is provided, creates a task in 0_INIT phase, allowing config to be set before starting.
    """
    task_id = str(uuid.uuid4())
    
    # Support both old form (query param) and new form (JSON body)
    actual_prompt = prompt
    actual_provider = search_provider
    if body:
        actual_prompt = body.request
        actual_provider = body.search_provider
        
    if not actual_prompt:
        new_record = TaskRecord(
            id=task_id,
            original_prompt="",
            current_phase=TaskPhase.PHASE_0_INIT.value,
            search_provider=actual_provider.value
        )
        db.add(new_record)
        await db.commit()
        await db.refresh(new_record)
        return record_to_pydantic(new_record)
        
    # Legacy behavior: Phase 1
    prompt = actual_prompt
    search_provider = actual_provider
    similar_repos = await TryniaService.search_similar_repos(prompt, provider=search_provider.value)
    structured_prompt = await TryniaService.generate_structured_prompt(prompt, similar_repos)
    
    new_record = TaskRecord(
        id=task_id,
        original_prompt=prompt,
        structured_prompt=structured_prompt,
        current_phase=TaskPhase.PHASE_2_PRECHECK.value,
        search_provider=search_provider.value
    )
    db.add(new_record)
    await db.commit()
    await db.refresh(new_record)
    
    # Trigger Phase 2 asynchronously
    background_tasks.add_task(trigger_phase_2_bg, task_id, similar_repos)
    return record_to_pydantic(new_record)

@router.post("/{task_id}/start", response_model=CodeTask)
async def start_task(task_id: str, req: StartRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Provide the prompt and start Phase 1 & 2 for a task in 0_INIT phase.
    """
    record = await get_task_by_id(db, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if record.current_phase != TaskPhase.PHASE_0_INIT.value:
        raise HTTPException(status_code=400, detail="Task is already started")
        
    # Phase 1: Intent Parsing
    record.original_prompt = req.prompt
    record.search_provider = req.search_provider.value
    record.current_phase = TaskPhase.PHASE_1_INTENT.value
    await db.commit()
    await manager.broadcast_state_change(task_id, record.current_phase)
    
    similar_repos = await TryniaService.search_similar_repos(req.prompt, provider=req.search_provider.value)
    structured_prompt = await TryniaService.generate_structured_prompt(req.prompt, similar_repos)
    
    record.structured_prompt = structured_prompt
    record.current_phase = TaskPhase.PHASE_2_PRECHECK.value
    await db.commit()
    await manager.broadcast_state_change(task_id, record.current_phase)
    
    # Trigger Phase 2 asynchronously
    background_tasks.add_task(trigger_phase_2_bg, task_id, similar_repos)
    return record_to_pydantic(record)

async def trigger_phase_2_bg(task_id: str, similar_repos: list[str]):
    async with AsyncSessionLocal() as db:
        await trigger_phase_2(db, task_id, similar_repos)

async def trigger_phase_2(db: AsyncSession, task_id: str, similar_repos: list[str]):
    """
    Phase 2: Analyze similar repos via GitHub README + Clod.
    """
    record = await get_task_by_id(db, task_id)
    if not record: return
    
    await manager.broadcast_log(task_id, f"Phase 2: Fetching READMEs from {len(similar_repos)} repos and analyzing with Clod...")
    
    constraints = await GreptileService.get_bug_list_from_repos(similar_repos, record.original_prompt)
    record.bug_list_constraints = constraints
    
    # Move to Phase 3
    record.current_phase = TaskPhase.PHASE_3_HITL.value
    await db.commit()
    
    await manager.broadcast_state_change(task_id, record.current_phase)

@router.get("/{task_id}", response_model=CodeTask)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    record = await get_task_by_id(db, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    return record_to_pydantic(record)

@router.post("/{task_id}/approve", response_model=CodeTask)
async def approve_task(task_id: str, approval: ApprovalRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Phase 3: HITL Checkpoint Approval
    """
    record = await get_task_by_id(db, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if record.current_phase != TaskPhase.PHASE_3_HITL.value:
        raise HTTPException(status_code=400, detail="Task is not pending approval")
        
    if not approval.approved:
        record.current_phase = TaskPhase.FAILED.value
        await db.commit()
        await manager.broadcast_state_change(task_id, record.current_phase)
        return record_to_pydantic(record)
        
    if approval.edited_prompt:
        record.structured_prompt = approval.edited_prompt
        
    record.current_phase = TaskPhase.PHASE_4_COMPUTE.value
    await db.commit()
    
    await manager.broadcast_state_change(task_id, record.current_phase)
    
    # Trigger Phase 4 asynchronously
    background_tasks.add_task(trigger_phase_4_bg, task_id)
    return record_to_pydantic(record)

async def trigger_phase_4_bg(task_id: str):
    async with AsyncSessionLocal() as db:
        await trigger_phase_4(db, task_id)

async def trigger_phase_4(db: AsyncSession, task_id: str):
    """
    Phase 4: Compute Routing with Clod.io
    """
    record = await get_task_by_id(db, task_id)
    if not record: return
    
    await manager.broadcast_log(task_id, "Entering Phase 4: Routing to Clod.io for code generation (Gemini fallback enabled)...")

    prompt_to_execute = record.structured_prompt or record.original_prompt
    try:
        model_name, generated_code = await ClodService.evaluate_and_generate(
            prompt=prompt_to_execute,
            constraints=record.bug_list_constraints,
        )
    except RuntimeError as exc:
        error_msg = str(exc)
        print(f"[Phase 4] Both providers failed: {error_msg}")
        await manager.broadcast_log(task_id, f"Phase 4 failed: {error_msg}")
        record.current_phase = TaskPhase.FAILED.value
        await db.commit()
        await manager.broadcast_state_change(task_id, record.current_phase)
        return

    record.selected_model = model_name
    record.generated_code = generated_code
    record.current_phase = TaskPhase.PHASE_5_SANDBOX.value
    await db.commit()
    
    await manager.broadcast_state_change(task_id, record.current_phase, {"selected_model": model_name})
    
    # Trigger Phase 5
    import asyncio
    asyncio.create_task(trigger_phase_5_bg(task_id))

async def trigger_phase_5_bg(task_id: str):
    async with AsyncSessionLocal() as db:
        await trigger_phase_5(db, task_id)

async def trigger_phase_5(db: AsyncSession, task_id: str):
    """
    Phase 5: Greptile Sandbox — submit code as a real GitHub PR,
    wait for Greptile App to auto-review, and iterate if needed.
    """
    record = await get_task_by_id(db, task_id)
    if not record: return
    
    await manager.broadcast_log(task_id, "Phase 5: Submitting code to GitHub PR for Greptile review...")
    
    # Generate semantic Git metadata via Clod ONCE before the loop
    from app.services.github_service import _generate_git_metadata
    meta = await _generate_git_metadata(record.original_prompt)
    branch_name = f"{meta['branch']}-{task_id[:6]}"  # constant branch for the whole task
    pr_title = meta["title"]
    commit_msg = meta["commit"]

    while record.sandbox_iterations < record.max_iterations:
        record.sandbox_iterations += 1
        await db.commit()
        await manager.broadcast_log(
            task_id,
            f"Sandbox iteration {record.sandbox_iterations}/{record.max_iterations}: Pushing to Harness..."
        )
        
        # Create a real GitHub PR (new one each time on the same branch) and wait for Greptile review
        review_result = await GitHubService.run_sandbox(
            task_id=task_id,
            prompt=record.original_prompt,
            code=record.generated_code,
            branch_name=branch_name,
            pr_title=pr_title,
            commit_message=commit_msg,
            github_token=record.github_token,   # BYOK
            target_repo=record.target_repo      # BYOK
        )
        
        pr_url = review_result.get("pr_url", "")
        score = review_result.get("confidence_score")
        needs_warning = review_result.get("needs_warning", False)

        if pr_url:
            await manager.broadcast_log(task_id, f"PR opened: {pr_url}")

        # --- Three-tier decision based on Greptile Confidence Score ---
        if review_result["passed"] and not needs_warning:
            # Score 5 (or timeout / no score): perfect, merge and celebrate
            score_msg = f"🎉 Perfect score ({score}/5)!" if score == 5 else "✅ Greptile review passed!"
            await manager.broadcast_log(task_id, f"{score_msg} Code approved and merging to main...")
            break

        if needs_warning:
            # Score 4: good enough to merge, but nudge user to review manually
            await manager.broadcast_log(
                task_id,
                f"⚠️ Greptile score: {score}/5 — Code is functional but has minor suggestions.\n"
                f"Merging to main. Consider reviewing the PR for optional improvements:\n{pr_url}"
            )
            break

        # Score 1-3: auto-retry — feed report back to Clod as new constraints
        feedback = review_result.get("feedback", "")
        score_label = f"{score}/5" if score is not None else "low"
        await manager.broadcast_log(
            task_id,
            f"❌ Greptile score: {score_label} — Issues found. Regenerating code...\n\nFeedback:\n{feedback[:600]}"
        )

        # ── DEBUG: print full Greptile report to terminal ──────────────────
        sep = "─" * 60
        print(f"\n{sep}")
        print(f"[AEGIS DEBUG] Task {task_id[:8]} — Greptile打回 (iteration {record.sandbox_iterations})")
        print(f"[AEGIS DEBUG] Confidence Score : {score_label}")
        print(f"[AEGIS DEBUG] Greptile Report  ↓\n{feedback}")
        print(sep)
        # ───────────────────────────────────────────────────────────────────

        current_constraints = list(record.bug_list_constraints or [])
        new_constraint = f"[Greptile iteration {record.sandbox_iterations}, score {score_label}]: {feedback[:800]}"
        current_constraints.append(new_constraint)
        record.bug_list_constraints = current_constraints

        # ── DEBUG: print updated constraint list ────────────────────────────
        print(f"[AEGIS DEBUG] 当前约束列表 ({len(current_constraints)} 条):")
        for i, c in enumerate(current_constraints, 1):
            print(f"  [{i}] {c[:120]}{'...' if len(c) > 120 else ''}")
        print(sep)
        # ───────────────────────────────────────────────────────────────────

        print(f"[AEGIS DEBUG] 开始调用 Clod 重新生成代码...")
        # 切换状态为 REWRITING 广播给前端
        record.current_phase = TaskPhase.PHASE_6_REWRITING.value
        await db.commit()
        await manager.broadcast_state_change(task_id, record.current_phase)

        _, new_code = await ClodService.evaluate_and_generate(
            prompt=record.structured_prompt or record.original_prompt,
            constraints=record.bug_list_constraints,
            iteration=record.sandbox_iterations,
            previous_code=record.generated_code
        )
        record.generated_code = new_code
        
        # 恢复状态为 SANDBOX 准备下一轮测试
        record.current_phase = TaskPhase.PHASE_5_SANDBOX.value
        await db.commit()
        await manager.broadcast_state_change(task_id, record.current_phase)

        # ── DEBUG: print snippet of regenerated code ────────────────────────
        print(f"[AEGIS DEBUG] 新代码已生成 ({len(new_code)} chars)，前200字符预览:")
        print(new_code[:200])
        print(f"{sep}\n")
        # ───────────────────────────────────────────────────────────────────


    record.current_phase = TaskPhase.FINISHED.value
    await db.commit()
    await manager.broadcast_state_change(task_id, record.current_phase, {"code": record.generated_code})
