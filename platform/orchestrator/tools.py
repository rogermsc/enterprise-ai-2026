"""Tool Registry and Execution.

Manages tool registration, validation, sandboxing, and execution.
Implements security controls for tool access.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import structlog

from orchestrator.state import ExecutionContext

logger = structlog.get_logger()


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ToolDefinition:
    """Tool definition and metadata."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    handler: Callable
    requires_approval: bool = False
    allowed_roles: list[str] = field(default_factory=lambda: ["*"])
    rate_limit: Optional[int] = None  # Calls per minute
    timeout_seconds: int = 30
    sandboxed: bool = True


class BaseTool(ABC):
    """Base class for tool implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema for parameters."""
        pass

    @abstractmethod
    async def execute(
        self, params: dict[str, Any], context: ExecutionContext
    ) -> ToolResult:
        """Execute the tool."""
        pass

    @property
    def requires_approval(self) -> bool:
        """Whether tool requires human approval."""
        return False


class ToolRegistry:
    """Registry for managing and executing tools.

    Features:
    - Tool registration with metadata
    - Permission checking
    - Rate limiting
    - Execution sandboxing
    - Audit logging
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
        self._rate_limits: dict[str, list[datetime]] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        logger.info("tool_registered", name=tool.name)
        self._tools[tool.name] = tool

    def register_function(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable,
        requires_approval: bool = False,
        **kwargs,
    ) -> None:
        """Register a function as a tool."""
        self.register(
            ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                handler=handler,
                requires_approval=requires_approval,
                **kwargs,
            )
        )

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())

    def requires_approval(self, name: str) -> bool:
        """Check if tool requires human approval."""
        tool = self._tools.get(name)
        return tool.requires_approval if tool else False

    def check_permission(
        self, name: str, context: ExecutionContext
    ) -> bool:
        """Check if context has permission to execute tool."""
        tool = self._tools.get(name)
        if not tool:
            return False

        if "*" in tool.allowed_roles:
            return True

        return any(role in context.permissions for role in tool.allowed_roles)

    def _check_rate_limit(self, name: str) -> bool:
        """Check if tool is within rate limit."""
        tool = self._tools.get(name)
        if not tool or not tool.rate_limit:
            return True

        now = datetime.now(timezone.utc)
        minute_ago = now.timestamp() - 60

        # Clean old entries
        if name in self._rate_limits:
            self._rate_limits[name] = [
                t for t in self._rate_limits[name] if t.timestamp() > minute_ago
            ]
        else:
            self._rate_limits[name] = []

        # Check limit
        if len(self._rate_limits[name]) >= tool.rate_limit:
            return False

        self._rate_limits[name].append(now)
        return True

    async def execute(
        self,
        name: str,
        params: dict[str, Any],
        context: ExecutionContext,
    ) -> ToolResult:
        """Execute a tool with security checks.

        Args:
            name: Tool name
            params: Tool parameters
            context: Execution context

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found or permission denied
        """
        tool = self._tools.get(name)
        if not tool:
            logger.warning("tool_not_found", name=name)
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool '{name}' not found",
            )

        # Permission check
        if not self.check_permission(name, context):
            logger.warning(
                "tool_permission_denied",
                name=name,
                user_id=context.user_id,
            )
            return ToolResult(
                success=False,
                output=None,
                error=f"Permission denied for tool '{name}'",
            )

        # Rate limit check
        if not self._check_rate_limit(name):
            logger.warning("tool_rate_limited", name=name)
            return ToolResult(
                success=False,
                output=None,
                error=f"Rate limit exceeded for tool '{name}'",
            )

        # Execute
        logger.info(
            "tool_execution_started",
            name=name,
            task_id=str(context.task_id),
        )

        try:
            import asyncio

            # Execute with timeout
            result = await asyncio.wait_for(
                tool.handler(params, context),
                timeout=tool.timeout_seconds,
            )

            logger.info(
                "tool_execution_completed",
                name=name,
                task_id=str(context.task_id),
                success=True,
            )

            return ToolResult(success=True, output=result)

        except asyncio.TimeoutError:
            logger.error(
                "tool_execution_timeout",
                name=name,
                timeout=tool.timeout_seconds,
            )
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool '{name}' timed out after {tool.timeout_seconds}s",
            )

        except Exception as e:
            logger.error(
                "tool_execution_failed",
                name=name,
                error=str(e),
            )
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )


# ============================================================================
# Built-in Tools
# ============================================================================


async def search_knowledge_base(
    params: dict[str, Any], context: ExecutionContext
) -> str:
    """Search the knowledge base for relevant information."""
    query = params.get("query", "")
    # TODO: Implement actual search
    return f"Found 3 results for: {query}"


async def create_ticket(
    params: dict[str, Any], context: ExecutionContext
) -> dict:
    """Create a support ticket."""
    # TODO: Implement actual ticket creation
    return {
        "ticket_id": "TKT-12345",
        "status": "created",
        "priority": params.get("priority", "medium"),
    }


async def send_email(
    params: dict[str, Any], context: ExecutionContext
) -> dict:
    """Send an email (requires approval)."""
    # TODO: Implement actual email sending
    return {
        "sent": True,
        "to": params.get("to"),
        "subject": params.get("subject"),
    }


def create_default_registry() -> ToolRegistry:
    """Create a registry with default tools."""
    registry = ToolRegistry()

    registry.register_function(
        name="search_knowledge_base",
        description="Search the knowledge base for relevant information",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
        handler=search_knowledge_base,
    )

    registry.register_function(
        name="create_ticket",
        description="Create a support ticket",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["title", "description"],
        },
        handler=create_ticket,
    )

    registry.register_function(
        name="send_email",
        description="Send an email to a customer",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string", "format": "email"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
        handler=send_email,
        requires_approval=True,  # Emails require human approval
    )

    return registry
