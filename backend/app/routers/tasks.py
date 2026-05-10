import uuid
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.state import CodeTask, TaskPhase, ApprovalRequest, SearchProvider, TaskCreateRequest
from app.models.orm import TaskRecord
from app.database import get_db, AsyncSessionLocal

from app.services.trynia_service import TryniaService
from app.services.greptile_service import GreptileService
from app.services.clod_service import ClodService
from app.services.github_service import GitHubService
from app.routers.websocket import manager

router = APIRouter()

# Demo Target Repository for Greptile Sandbox
TARGET_REPO = "sebastianZzzz/AegisHarness-Demo"

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
        created_at=record.created_at,
        updated_at=record.updated_at
    )

@router.post("/", response_model=CodeTask)
async def create_task(task_req: TaskCreateRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Phase 1: Intent Parsing & Context.
    """
    task_id = str(uuid.uuid4())
    prompt = task_req.request
    search_provider = task_req.search_provider
    
    # Phase 1: Use selected provider to find similar repos
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
    Phase 3: HITL Checkpoint — approve or reject.
    Can also be called with approved=False to reject from any phase.
    """
    record = await get_task_by_id(db, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")

    if not approval.approved:
        record.current_phase = TaskPhase.FAILED.value
        await db.commit()
        await manager.broadcast_state_change(task_id, record.current_phase)
        return record_to_pydantic(record)

    if record.current_phase != TaskPhase.PHASE_3_HITL.value:
        raise HTTPException(status_code=400, detail=f"Task is not pending approval (current phase: {record.current_phase})")

    if approval.edited_prompt:
        record.structured_prompt = approval.edited_prompt

    record.current_phase = TaskPhase.PHASE_4_COMPUTE.value
    await db.commit()

    await manager.broadcast_state_change(task_id, record.current_phase)

    # Trigger Phase 4 asynchronously
    background_tasks.add_task(trigger_phase_4_bg, task_id)
    return record_to_pydantic(record)

@router.post("/{task_id}/reject", response_model=CodeTask)
async def reject_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Reject a task from any phase and mark as FAILED."""
    record = await get_task_by_id(db, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    record.current_phase = TaskPhase.FAILED.value
    await db.commit()
    await manager.broadcast_state_change(task_id, record.current_phase)
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
    
    await manager.broadcast_log(task_id, "Entering Phase 4: Routing to Clod.io for code generation...")
    
    # Phase 4: Use Clod.io for unified smart routing and code generation
    prompt_to_execute = record.structured_prompt or record.original_prompt
    model_name, generated_code = await ClodService.evaluate_and_generate(
        prompt=prompt_to_execute, 
        constraints=record.bug_list_constraints
    )
    
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
    
    while record.sandbox_iterations < record.max_iterations:
        record.sandbox_iterations += 1
        await db.commit()
        await manager.broadcast_log(
            task_id,
            f"Sandbox iteration {record.sandbox_iterations}/{record.max_iterations}: Opening PR on AegisHarness-Demo..."
        )
        
        # Create a real GitHub PR with the generated code, then wait for Greptile review
        review_result = await GitHubService.run_sandbox(
            task_id=task_id,
            prompt=record.original_prompt,
            code=record.generated_code
        )
        
        pr_url = review_result.get("pr_url", "")
        if pr_url:
            await manager.broadcast_log(task_id, f"PR opened: {pr_url}")
        
        if review_result["passed"]:
            await manager.broadcast_log(task_id, "✅ Greptile review passed! Code approved.")
            break
        
        feedback = review_result.get("feedback", "")
        await manager.broadcast_log(
            task_id,
            f"❌ Greptile found issues. Regenerating...\n\nFeedback:\n{feedback[:500]}"
        )
        
        # Feed Greptile's feedback back as constraints and regenerate
        current_constraints = list(record.bug_list_constraints or [])
        current_constraints.append(f"Greptile review (iteration {record.sandbox_iterations}): {feedback}")
        record.bug_list_constraints = current_constraints
        
        _, new_code = await ClodService.evaluate_and_generate(
            prompt=record.structured_prompt or record.original_prompt,
            constraints=record.bug_list_constraints
        )
        record.generated_code = new_code
        await db.commit()
    
    record.current_phase = TaskPhase.FINISHED.value
    await db.commit()
    await manager.broadcast_state_change(task_id, record.current_phase, {"code": record.generated_code})
