from enum import Enum
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class SearchProvider(str, Enum):
    NIA = "nia"
    GITHUB = "github"

class TaskPhase(str, Enum):
    PHASE_0_INIT = "0_INIT"
    PHASE_1_INTENT = "1_INTENT_PARSING"
    PHASE_2_PRECHECK = "2_PRECHECK_GREPTILE"
    PHASE_3_HITL = "3_HUMAN_IN_THE_LOOP"
    PHASE_4_COMPUTE = "4_COMPUTE_ROUTING"
    PHASE_5_SANDBOX = "5_SANDBOX_TESTING"
    PHASE_6_REWRITING = "6_REWRITING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"

class CodeTask(BaseModel):
    id: str
    original_prompt: str
    structured_prompt: Optional[str] = None
    bug_list_constraints: List[str] = []
    current_phase: TaskPhase = TaskPhase.PHASE_1_INTENT
    search_provider: SearchProvider = SearchProvider.GITHUB
    difficulty_score: Optional[int] = None
    selected_model: Optional[str] = None
    generated_code: Optional[str] = None
    sandbox_iterations: int = 0
    max_iterations: int = 3
    error_message: Optional[str] = None
    # BYOK: target_repo shown to frontend; github_token is NEVER returned
    target_repo: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

class ApprovalRequest(BaseModel):
    approved: bool
    edited_prompt: Optional[str] = None

class TaskCreateRequest(BaseModel):
    request: str
    search_provider: SearchProvider = SearchProvider.GITHUB

class StartRequest(BaseModel):
    prompt: str
    search_provider: SearchProvider = SearchProvider.GITHUB

class GitHubConfig(BaseModel):
    """Payload for POST /api/v1/config — user-supplied GitHub credentials (BYOK)."""
    github_token: str
    target_repo: str  # e.g. "owner/repo-name"
