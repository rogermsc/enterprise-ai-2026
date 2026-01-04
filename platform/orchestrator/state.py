"""Agent State Management.

Defines the state schema for agent execution using TypedDict for LangGraph.
Implements state persistence and recovery for long-running tasks.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Optional, Sequence
from uuid import UUID

from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class ExecutionStatus(str, Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCall(BaseModel):
    """Record of a tool invocation."""
    id: str
    name: str
    input: dict[str, Any]
    output: Optional[Any] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    latency_ms: Optional[float] = None
    approved_by: Optional[str] = None  # For human-in-loop


class ReasoningStep(BaseModel):
    """A single step in the agent's reasoning trace."""
    step_number: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[dict[str, Any]] = None
    observation: Optional[str] = None
    timestamp: datetime


class ExecutionContext(BaseModel):
    """Execution context passed to agents."""
    task_id: UUID
    user_id: str
    org_id: str
    session_id: Optional[str] = None
    parent_task_id: Optional[UUID] = None
    metadata: dict[str, str] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Complete agent execution state.

    This state is persisted after each step for:
    - Recovery after failures
    - Human-in-the-loop checkpoints
    - Audit trail
    - Debugging
    """
    # Identity
    task_id: UUID
    agent_id: str
    context: ExecutionContext

    # Execution
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_step: int = 0
    max_steps: int = 10

    # Input/Output
    input: str
    output: Optional[str] = None
    final_answer: Optional[str] = None

    # Message history (for LangGraph)
    messages: Annotated[Sequence[Any], add_messages] = Field(default_factory=list)

    # Reasoning trace
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)

    # Human-in-loop
    pending_approval: Optional[ToolCall] = None
    approval_timeout_seconds: int = 3600

    # Metrics
    token_usage: dict[str, int] = Field(default_factory=lambda: {
        "prompt": 0,
        "completion": 0,
        "total": 0,
    })
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class CheckpointData(BaseModel):
    """Serializable checkpoint for state persistence."""
    task_id: str
    agent_id: str
    state_json: str
    step_number: int
    created_at: datetime
    checksum: str  # For integrity verification
