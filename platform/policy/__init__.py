"""Policy Engine - OPA-style Policy Evaluation.

Implements enterprise policy controls for:
- Agent access control
- Tool usage restrictions
- Data access policies
- Rate limiting policies
- Compliance rules
"""

__version__ = "0.1.0"

from policy.engine import PolicyEngine, PolicyDecision
from policy.rules import Rule, RuleSet

__all__ = ["PolicyEngine", "PolicyDecision", "Rule", "RuleSet"]
