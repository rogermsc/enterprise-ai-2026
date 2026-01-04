# Zero-Trust Agent Design

## Principles for Secure AI Agent Systems

### Core Philosophy

> "Never trust, always verify" — applied to AI agents means treating every agent action as potentially hostile until proven safe.

---

## Zero-Trust Principles for AI

### 1. No Implicit Trust

Traditional systems trust internal components. Zero-trust AI systems:

- Verify every tool call
- Validate every agent decision
- Authenticate every context switch
- Audit every action

### 2. Least Privilege

Agents receive minimum required permissions:

```python
# Bad: Overly permissive
agent_permissions = ["*"]

# Good: Scoped permissions
agent_permissions = [
    "knowledge_base:read",
    "tickets:read",
    "tickets:create",
    "email:send:requires_approval",
]
```

### 3. Assume Breach

Design as if the agent is already compromised:

- Limit blast radius of any single agent
- Segment sensitive operations
- Monitor for anomalous behavior
- Enable quick revocation

---

## Implementation Patterns

### Pattern 1: Tool Sandboxing

Every tool executes in isolation:

```
┌─────────────────────────────────────────────────┐
│                 AGENT PROCESS                    │
├─────────────────────────────────────────────────┤
│                                                  │
│   ┌─────────────────────────────────────────┐   │
│   │           SANDBOX BOUNDARY               │   │
│   │  ┌─────────────────────────────────┐    │   │
│   │  │         TOOL EXECUTOR            │    │   │
│   │  │  • Limited network access        │    │   │
│   │  │  • No filesystem (except /tmp)   │    │   │
│   │  │  • Memory limits                 │    │   │
│   │  │  • CPU time limits               │    │   │
│   │  └─────────────────────────────────┘    │   │
│   └─────────────────────────────────────────┘   │
│                                                  │
└─────────────────────────────────────────────────┘
```

Implementation:

```python
class SandboxedToolExecutor:
    def __init__(self, limits: ResourceLimits):
        self.limits = limits

    async def execute(self, tool: Tool, params: dict) -> ToolResult:
        # Create isolated execution context
        with resource_limits(
            max_memory_mb=self.limits.memory_mb,
            max_cpu_seconds=self.limits.cpu_seconds,
            network_policy=self.limits.network_policy,
        ):
            # Execute with timeout
            result = await asyncio.wait_for(
                tool.run(params),
                timeout=self.limits.timeout_seconds
            )
            return result
```

### Pattern 2: Capability-Based Security

Tools are accessed via unforgeable capability tokens:

```python
# Capability token structure
@dataclass
class ToolCapability:
    tool_id: str
    granted_to: str  # Agent ID
    actions: list[str]
    constraints: dict  # e.g., {"max_calls": 10}
    expires_at: datetime
    signature: str  # HMAC signature

# Verification at execution time
def verify_capability(cap: ToolCapability, action: str) -> bool:
    # Check signature
    if not verify_signature(cap):
        return False

    # Check expiration
    if datetime.now() > cap.expires_at:
        return False

    # Check action allowed
    if action not in cap.actions:
        return False

    return True
```

### Pattern 3: Human-in-the-Loop Gates

Sensitive actions require explicit approval:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    AGENT     │────►│   APPROVAL   │────►│    HUMAN     │
│   DECIDES    │     │    QUEUE     │     │   REVIEWER   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                     ┌──────────────┐             │
                     │   EXECUTE    │◄────────────┘
                     │    ACTION    │  (if approved)
                     └──────────────┘
```

Configuration:

```yaml
# Human approval configuration
approval_gates:
  - pattern: "email:send:*"
    required: true
    approvers: ["customer_success", "admin"]
    timeout_minutes: 60

  - pattern: "database:write:*"
    required: true
    approvers: ["data_team"]
    timeout_minutes: 30

  - pattern: "payment:*"
    required: true
    approvers: ["finance"]
    timeout_minutes: 120
```

### Pattern 4: Continuous Verification

Runtime behavior monitoring:

```python
class BehaviorMonitor:
    def __init__(self):
        self.baseline = self._load_baseline()
        self.anomaly_threshold = 0.8

    def check_action(self, agent_id: str, action: Action) -> VerifyResult:
        # Check against behavioral baseline
        score = self._compute_anomaly_score(agent_id, action)

        if score > self.anomaly_threshold:
            # Anomalous behavior detected
            return VerifyResult(
                allowed=False,
                reason="Anomalous behavior detected",
                score=score,
                action="block_and_alert"
            )

        return VerifyResult(allowed=True)

    def _compute_anomaly_score(self, agent_id: str, action: Action) -> float:
        # Compare to historical patterns:
        # - Tool usage frequency
        # - Parameter distributions
        # - Time-of-day patterns
        # - Sequence patterns
        ...
```

---

## Security Boundaries

### Boundary Definition

```
┌─────────────────────────────────────────────────────────────┐
│                      TRUST BOUNDARY 0                        │
│                     (External/Untrusted)                     │
│   • User Input                                              │
│   • External APIs                                           │
│   • Retrieved Documents                                      │
├─────────────────────────────────────────────────────────────┤
│                      TRUST BOUNDARY 1                        │
│                     (Platform/Verified)                      │
│   • Authenticated Requests                                  │
│   • Validated Input                                         │
│   • Policy-Checked Actions                                  │
├─────────────────────────────────────────────────────────────┤
│                      TRUST BOUNDARY 2                        │
│                     (Agent/Monitored)                        │
│   • Agent Reasoning                                         │
│   • Tool Selection                                          │
│   • Output Generation                                       │
├─────────────────────────────────────────────────────────────┤
│                      TRUST BOUNDARY 3                        │
│                     (Core/Protected)                         │
│   • Secrets                                                 │
│   • Customer Data                                           │
│   • System Configuration                                    │
└─────────────────────────────────────────────────────────────┘
```

### Cross-Boundary Controls

| From → To | Controls Required |
|-----------|-------------------|
| 0 → 1 | Authentication, validation, sanitization |
| 1 → 2 | Policy check, capability grant |
| 2 → 3 | Encryption, access control, audit |
| 2 → 0 | Output filtering, rate limiting |

---

## Monitoring and Detection

### Key Metrics

```python
# Security-relevant metrics
metrics = {
    # Access patterns
    "tool_calls_per_minute": Gauge,
    "failed_auth_attempts": Counter,
    "permission_denials": Counter,

    # Behavioral
    "anomaly_score": Histogram,
    "unusual_tool_sequences": Counter,

    # Data protection
    "pii_detections": Counter,
    "output_filtering_triggers": Counter,
}
```

### Alert Conditions

| Condition | Severity | Action |
|-----------|----------|--------|
| Anomaly score > 0.9 | Critical | Block + page on-call |
| Failed auth > 10/min | High | Temporary block |
| PII in output | Medium | Log + review |
| Unusual hours activity | Low | Log for review |

---

## Implementation Checklist

### Minimum Viable Security

- [ ] All tools validate input schema
- [ ] All tool calls logged with context
- [ ] Rate limiting on all tools
- [ ] Timeout on all operations
- [ ] Output scanning for PII

### Enhanced Security

- [ ] Capability-based tool access
- [ ] Human-in-the-loop for sensitive actions
- [ ] Behavioral baseline monitoring
- [ ] Automated anomaly detection
- [ ] Cross-boundary encryption

### Advanced Security

- [ ] Formal verification of policies
- [ ] Red team testing program
- [ ] Continuous fuzzing
- [ ] Supply chain verification
- [ ] HSM-backed secrets

---

## References

- NIST Zero Trust Architecture (SP 800-207)
- OWASP LLM Top 10
- MITRE ATLAS (Adversarial AI)
- CIS AI Security Controls
