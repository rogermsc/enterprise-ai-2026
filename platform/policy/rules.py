"""Policy Rule Definitions.

Declarative rule structures for the policy engine.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from policy.engine import Decision


@dataclass
class Rule:
    """A single policy rule."""
    id: str
    name: str
    description: str
    priority: int  # Lower = higher priority

    # Matching criteria
    resource_type: Optional[str] = None  # agent, tool, data, *
    action: Optional[str] = None  # execute, read, write, delete, *
    required_roles: list[str] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)

    # Decision
    decision: Decision = Decision.DENY
    reason: Optional[str] = None

    # Metadata
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class RuleSet:
    """Collection of related rules."""
    name: str
    description: str
    rules: list[Rule] = field(default_factory=list)
    enabled: bool = True
    version: str = "1.0.0"

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the set."""
        self.rules.append(rule)

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
