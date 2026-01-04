"""Task Management API Routes.

Endpoints for managing async agent tasks:
- List tasks
- Get task status
- Cancel tasks
- Get task history
"""

from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from gateway.auth import AuthenticatedUser, get_current_user, require_scope

logger = structlog.get_logger()
router = APIRouter()


# ============================================================================
# Models
# ============================================================================


class TaskStatus(BaseModel):
    """Task status information."""
    task_id: UUID
    agent_id: str
    status: str  # pending, running, completed, failed, cancelled
    progress: float = Field(ge=0.0, le=1.0)
    current_step: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class TaskResult(BaseModel):
    """Complete task result."""
    task_id: UUID
    agent_id: str
    status: str
    input: str
    output: Optional[str] = None
    reasoning_trace: list[dict] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    created_at: datetime
    completed_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)


class TaskListResponse(BaseModel):
    """Paginated task list response."""
    tasks: list[TaskStatus]
    total: int
    page: int
    page_size: int
    has_more: bool


# ============================================================================
# Routes
# ============================================================================


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks",
    description="Get paginated list of tasks for the organization",
)
async def list_tasks(
    user: Annotated[AuthenticatedUser, Depends(require_scope("tasks:read"))],
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
) -> TaskListResponse:
    """List all tasks for the organization."""
    logger.info(
        "list_tasks",
        user_id=user.user_id,
        org_id=user.org_id,
        status_filter=status_filter,
        agent_id=agent_id,
    )

    # TODO: Implement actual database query
    # Mock response
    return TaskListResponse(
        tasks=[],
        total=0,
        page=page,
        page_size=page_size,
        has_more=False,
    )


@router.get(
    "/{task_id}",
    response_model=TaskStatus,
    summary="Get task status",
    description="Get the current status of a task",
)
async def get_task_status(
    task_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_scope("tasks:read"))],
) -> TaskStatus:
    """Get task status by ID."""
    logger.info("get_task_status", task_id=str(task_id), user_id=user.user_id)

    # TODO: Implement actual database lookup
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task '{task_id}' not found",
    )


@router.get(
    "/{task_id}/result",
    response_model=TaskResult,
    summary="Get task result",
    description="Get the complete result of a completed task",
)
async def get_task_result(
    task_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_scope("tasks:read"))],
) -> TaskResult:
    """Get complete task result."""
    logger.info("get_task_result", task_id=str(task_id), user_id=user.user_id)

    # TODO: Implement actual database lookup
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task '{task_id}' not found",
    )


@router.post(
    "/{task_id}/cancel",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Cancel task",
    description="Request cancellation of a running task",
)
async def cancel_task(
    task_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_scope("tasks:write"))],
) -> dict:
    """Cancel a running task."""
    logger.info("cancel_task", task_id=str(task_id), user_id=user.user_id)

    # TODO: Implement actual cancellation
    return {
        "task_id": str(task_id),
        "status": "cancellation_requested",
        "message": "Task cancellation has been requested",
    }


@router.post(
    "/{task_id}/retry",
    response_model=TaskStatus,
    summary="Retry task",
    description="Retry a failed task",
)
async def retry_task(
    task_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_scope("tasks:write"))],
) -> TaskStatus:
    """Retry a failed task."""
    logger.info("retry_task", task_id=str(task_id), user_id=user.user_id)

    # TODO: Implement actual retry logic
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task '{task_id}' not found",
    )
