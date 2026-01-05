"""Policy Evaluation Engine.

OPA-inspired policy engine for enterprise AI governance.
Supports declarative policies with audit logging.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import structlog

from policy.types import Decision
from policy.rules import Rule, RuleSet

logger = structlog.get_logger()


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""
    decision: Decision
    rule_id: Optional[str] = None
    reason: Optional[str] = None
    conditions: dict = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PolicyContext:
    """Context for policy evaluation."""
    # Subject (who)
    user_id: str
    org_id: str
    roles: list[str]

    # Resource (what)
    resource_type: str  # agent, tool, data
    resource_id: str
    action: str  # execute, read, write, delete

    # Environment
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Additional context
    metadata: dict = field(default_factory=dict)


class PolicyEngine:
    """Enterprise policy evaluation engine.

    Features:
    - Declarative rule definitions
    - Priority-based evaluation
    - Audit logging for compliance
    - Caching for performance
    """

    def __init__(self):
        self._rule_sets: dict[str, RuleSet] = {}
        self._default_decision = Decision.DENY

    def register_rule_set(self, rule_set: RuleSet) -> None:
        """Register a rule set."""
        logger.info(
            "rule_set_registered",
            name=rule_set.name,
            rule_count=len(rule_set.rules),
        )
        self._rule_sets[rule_set.name] = rule_set

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """Evaluate all applicable policies.

        Args:
            context: Policy evaluation context

        Returns:
            Policy decision with reason
        """
        logger.debug(
            "policy_evaluation_started",
            user_id=context.user_id,
            resource=f"{context.resource_type}:{context.resource_id}",
            action=context.action,
        )

        # Collect all applicable rules
        applicable_rules: list[tuple[int, Rule]] = []

        for rule_set in self._rule_sets.values():
            for rule in rule_set.rules:
                if self._rule_matches(rule, context):
                    applicable_rules.append((rule.priority, rule))

        # Sort by priority (lower = higher priority)
        applicable_rules.sort(key=lambda x: x[0])

        # Evaluate in order
        for _, rule in applicable_rules:
            decision = self._evaluate_rule(rule, context)
            if decision:
                logger.info(
                    "policy_decision",
                    user_id=context.user_id,
                    resource=f"{context.resource_type}:{context.resource_id}",
                    action=context.action,
                    decision=decision.decision.value,
                    rule_id=rule.id,
                )
                return decision

        # Default decision
        default = PolicyDecision(
            decision=self._default_decision,
            reason="No matching policy rule found",
        )

        logger.info(
            "policy_decision_default",
            user_id=context.user_id,
            resource=f"{context.resource_type}:{context.resource_id}",
            action=context.action,
            decision=default.decision.value,
        )

        return default

    def _rule_matches(self, rule: Rule, context: PolicyContext) -> bool:
        """Check if rule applies to context."""
        # Check resource type
        if rule.resource_type and rule.resource_type != "*":
            if rule.resource_type != context.resource_type:
                return False

        # Check action
        if rule.action and rule.action != "*":
            if rule.action != context.action:
                return False

        # Check roles
        if rule.required_roles:
            if not any(role in context.roles for role in rule.required_roles):
                return False

        return True

    def _evaluate_rule(self, rule: Rule, context: PolicyContext) -> Optional[PolicyDecision]:
        """Evaluate a single rule."""
        # Check conditions
        if rule.conditions:
            for key, expected in rule.conditions.items():
                actual = context.metadata.get(key)
                if actual != expected:
                    return None

        return PolicyDecision(
            decision=rule.decision,
            rule_id=rule.id,
            reason=rule.reason,
        )


def create_default_policies() -> PolicyEngine:
    """Create engine with default enterprise policies."""
    engine = PolicyEngine()

    # Admin access rule set
    admin_rules = RuleSet(
        name="admin_access",
        description="Admin override rules",
        rules=[
            Rule(
                id="admin_allow_all",
                name="Admin Allow All",
                description="Admins can do anything",
                priority=0,
                resource_type="*",
                action="*",
                required_roles=["admin"],
                decision=Decision.ALLOW,
                reason="Admin access granted",
            ),
        ],
    )

    # Tool execution rules
    tool_rules = RuleSet(
        name="tool_execution",
        description="Tool execution policies",
        rules=[
            Rule(
                id="sensitive_tool_approval",
                name="Sensitive Tool Approval",
                description="Sensitive tools require approval",
                priority=10,
                resource_type="tool",
                action="execute",
                conditions={"sensitivity": "high"},
                decision=Decision.REQUIRE_APPROVAL,
                reason="High sensitivity tool requires approval",
            ),
            Rule(
                id="allow_standard_tools",
                name="Allow Standard Tools",
                description="Allow execution of standard tools",
                priority=20,
                resource_type="tool",
                action="execute",
                required_roles=["agent_user", "api_user"],
                decision=Decision.ALLOW,
                reason="Standard tool access granted",
            ),
        ],
    )

    # Agent execution rules
    agent_rules = RuleSet(
        name="agent_execution",
        description="Agent execution policies",
        rules=[
            Rule(
                id="allow_agent_execution",
                name="Allow Agent Execution",
                description="Allow authenticated users to execute agents",
                priority=10,
                resource_type="agent",
                action="execute",
                required_roles=["agent_user", "api_user"],
                decision=Decision.ALLOW,
                reason="Agent execution allowed",
            ),
            Rule(
                id="deny_unauthenticated",
                name="Deny Unauthenticated",
                description="Deny unauthenticated access",
                priority=100,
                resource_type="*",
                action="*",
                decision=Decision.DENY,
                reason="Authentication required",
            ),
        ],
    )

    engine.register_rule_set(admin_rules)
    engine.register_rule_set(tool_rules)
    engine.register_rule_set(agent_rules)

    return engine
