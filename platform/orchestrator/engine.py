"""Agent Execution Engine.

Core orchestration engine using LangGraph for stateful agent execution.
Implements the ReAct pattern with tool use, human-in-the-loop, and observability.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from orchestrator.state import (
    AgentState,
    ExecutionContext,
    ExecutionStatus,
    ReasoningStep,
    ToolCall,
)
from orchestrator.tools import ToolRegistry, ToolResult

logger = structlog.get_logger()


class AgentEngine:
    """LangGraph-based agent execution engine.

    Features:
    - Stateful multi-step reasoning
    - Tool execution with sandboxing
    - Human-in-the-loop approval
    - Checkpoint-based recovery
    - Observability hooks
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        model: Optional[Any] = None,
        max_iterations: int = 10,
        enable_human_in_loop: bool = True,
    ):
        self.tool_registry = tool_registry
        self.model = model
        self.max_iterations = max_iterations
        self.enable_human_in_loop = enable_human_in_loop
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph execution graph."""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("reason", self._reason_node)
        graph.add_node("execute_tool", self._tool_node)
        graph.add_node("human_approval", self._human_approval_node)
        graph.add_node("finalize", self._finalize_node)

        # Add edges
        graph.set_entry_point("reason")
        graph.add_conditional_edges(
            "reason",
            self._route_after_reason,
            {
                "execute_tool": "execute_tool",
                "human_approval": "human_approval",
                "finalize": "finalize",
                "end": END,
            },
        )
        graph.add_edge("execute_tool", "reason")
        graph.add_edge("human_approval", "execute_tool")
        graph.add_edge("finalize", END)

        return graph.compile()

    async def execute(
        self,
        agent_id: str,
        input_text: str,
        context: ExecutionContext,
        config_override: Optional[dict] = None,
    ) -> AgentState:
        """Execute an agent task.

        Args:
            agent_id: ID of the agent to execute
            input_text: User input/query
            context: Execution context with user/org info
            config_override: Optional configuration overrides

        Returns:
            Final agent state after execution
        """
        task_id = context.task_id or uuid4()

        logger.info(
            "agent_execution_started",
            task_id=str(task_id),
            agent_id=agent_id,
            user_id=context.user_id,
        )

        # Initialize state
        initial_state = AgentState(
            task_id=task_id,
            agent_id=agent_id,
            context=context,
            input=input_text,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            max_steps=config_override.get("max_iterations", self.max_iterations)
            if config_override
            else self.max_iterations,
        )

        try:
            # Execute graph
            final_state = await self._graph.ainvoke(initial_state)

            logger.info(
                "agent_execution_completed",
                task_id=str(task_id),
                agent_id=agent_id,
                status=final_state.status,
                steps=final_state.current_step,
            )

            return final_state

        except Exception as e:
            logger.error(
                "agent_execution_failed",
                task_id=str(task_id),
                agent_id=agent_id,
                error=str(e),
            )
            initial_state.status = ExecutionStatus.FAILED
            initial_state.error = str(e)
            initial_state.completed_at = datetime.now(timezone.utc)
            return initial_state

    async def _reason_node(self, state: AgentState) -> AgentState:
        """Reasoning node - LLM decides next action."""
        state.current_step += 1

        # Check iteration limit
        if state.current_step > state.max_steps:
            state.status = ExecutionStatus.FAILED
            state.error = f"Max iterations ({state.max_steps}) exceeded"
            return state

        # TODO: Actual LLM call would go here
        # This is a mock implementation
        reasoning_step = ReasoningStep(
            step_number=state.current_step,
            thought=f"Analyzing step {state.current_step}...",
            action="search_knowledge_base" if state.current_step == 1 else None,
            action_input={"query": state.input[:100]} if state.current_step == 1 else None,
            timestamp=datetime.now(timezone.utc),
        )
        state.reasoning_steps.append(reasoning_step)

        return state

    async def _tool_node(self, state: AgentState) -> AgentState:
        """Tool execution node."""
        if not state.reasoning_steps:
            return state

        last_step = state.reasoning_steps[-1]
        if not last_step.action:
            return state

        tool_call = ToolCall(
            id=str(uuid4()),
            name=last_step.action,
            input=last_step.action_input or {},
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Execute tool
            result = await self.tool_registry.execute(
                tool_call.name,
                tool_call.input,
                context=state.context,
            )

            tool_call.output = result.output
            tool_call.completed_at = datetime.now(timezone.utc)
            tool_call.latency_ms = (
                tool_call.completed_at - tool_call.started_at
            ).total_seconds() * 1000

            # Update reasoning with observation
            last_step.observation = str(result.output)

        except Exception as e:
            tool_call.error = str(e)
            tool_call.completed_at = datetime.now(timezone.utc)
            last_step.observation = f"Error: {e}"

        state.tool_calls.append(tool_call)
        return state

    async def _human_approval_node(self, state: AgentState) -> AgentState:
        """Human-in-the-loop approval node."""
        state.status = ExecutionStatus.AWAITING_HUMAN

        # In production, this would:
        # 1. Persist state to database
        # 2. Send notification to approver
        # 3. Wait for webhook callback or polling

        logger.info(
            "awaiting_human_approval",
            task_id=str(state.task_id),
            pending_tool=state.pending_approval.name if state.pending_approval else None,
        )

        # For demo, auto-approve after short delay
        await asyncio.sleep(0.1)
        state.status = ExecutionStatus.RUNNING

        return state

    async def _finalize_node(self, state: AgentState) -> AgentState:
        """Finalization node - prepare final response."""
        state.status = ExecutionStatus.COMPLETED
        state.completed_at = datetime.now(timezone.utc)

        # Generate final answer from reasoning trace
        if state.reasoning_steps:
            observations = [
                s.observation for s in state.reasoning_steps if s.observation
            ]
            state.final_answer = " ".join(observations) if observations else state.input

        state.output = state.final_answer
        return state

    def _route_after_reason(self, state: AgentState) -> str:
        """Route to next node based on reasoning output."""
        if state.status == ExecutionStatus.FAILED:
            return "end"

        if not state.reasoning_steps:
            return "finalize"

        last_step = state.reasoning_steps[-1]

        # Check if we have an action to execute
        if last_step.action:
            # Check if this tool requires human approval
            if (
                self.enable_human_in_loop
                and self.tool_registry.requires_approval(last_step.action)
            ):
                state.pending_approval = ToolCall(
                    id=str(uuid4()),
                    name=last_step.action,
                    input=last_step.action_input or {},
                    started_at=datetime.now(timezone.utc),
                )
                return "human_approval"
            return "execute_tool"

        # No action means we're done reasoning
        if state.current_step >= 2:  # Demo: finish after 2 steps
            return "finalize"

        return "finalize"
