"""Policy Type Definitions.

Shared types for the policy module to avoid circular imports.
"""

from enum import Enum


class Decision(str, Enum):
    """Policy decision outcome."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
