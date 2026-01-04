# Observability Guide

## Monitoring AI Agent Systems in Production

### Overview

This document describes observability practices for AI agent systems, covering:

- **Metrics**: Quantitative measurements of system health
- **Logs**: Structured event records for debugging
- **Traces**: Distributed request tracking across components
- **Alerts**: Automated incident detection and notification

---

## Observability Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                  │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │   Gateway   │     │ Orchestrator│     │    Tools    │                   │
│  │             │     │             │     │             │                   │
│  │ ┌─────────┐ │     │ ┌─────────┐ │     │ ┌─────────┐ │                   │
│  │ │ Metrics │ │     │ │ Metrics │ │     │ │ Metrics │ │                   │
│  │ │ Logs    │ │     │ │ Logs    │ │     │ │ Logs    │ │                   │
│  │ │ Traces  │ │     │ │ Traces  │ │     │ │ Traces  │ │                   │
│  │ └────┬────┘ │     │ └────┬────┘ │     │ └────┬────┘ │                   │
│  └──────┼──────┘     └──────┼──────┘     └──────┼──────┘                   │
│         │                   │                   │                           │
└─────────┼───────────────────┼───────────────────┼───────────────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────────────┐
│                   COLLECTION LAYER                                           │
│                             ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    OpenTelemetry Collector                               ││
│  │   • Receives metrics, logs, traces from all services                    ││
│  │   • Processes, filters, and routes telemetry                            ││
│  │   • Exports to multiple backends                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                             │                                                │
└─────────────────────────────┼────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Prometheus    │  │     Loki        │  │     Jaeger      │
│   (Metrics)     │  │    (Logs)       │  │    (Traces)     │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │     Grafana     │
                    │  (Dashboards)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Alertmanager  │
                    │   (Alerts)      │
                    └─────────────────┘
```

---

## Metrics

### Key Performance Indicators

#### Request Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `agent_requests_total` | Counter | agent, status | Total requests |
| `agent_request_duration_seconds` | Histogram | agent, status | Request latency |
| `agent_active_requests` | Gauge | agent | Concurrent requests |

#### Agent Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `agent_iterations_total` | Counter | agent | Reasoning iterations |
| `agent_tool_calls_total` | Counter | agent, tool, status | Tool invocations |
| `agent_tokens_used_total` | Counter | agent, direction | Token consumption |
| `agent_cost_usd_total` | Counter | agent | Estimated cost |

#### Quality Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `agent_hallucination_score` | Histogram | agent | Hallucination detection |
| `agent_safety_violations_total` | Counter | agent, type | Safety issues |
| `agent_user_feedback_score` | Histogram | agent | User ratings |

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'gateway'
    static_configs:
      - targets: ['gateway:8080']
    metrics_path: /metrics

  - job_name: 'orchestrator'
    static_configs:
      - targets: ['orchestrator:8081']
    metrics_path: /metrics

  - job_name: 'tools'
    static_configs:
      - targets: ['tools:8082']
    metrics_path: /metrics

rule_files:
  - /etc/prometheus/rules/*.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Metrics Implementation

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
REQUEST_COUNT = Counter(
    'agent_requests_total',
    'Total agent requests',
    ['agent', 'status']
)

REQUEST_LATENCY = Histogram(
    'agent_request_duration_seconds',
    'Request latency in seconds',
    ['agent', 'status'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_REQUESTS = Gauge(
    'agent_active_requests',
    'Currently active requests',
    ['agent']
)

TOKEN_USAGE = Counter(
    'agent_tokens_used_total',
    'Total tokens consumed',
    ['agent', 'direction']  # input/output
)

# Usage in code
async def handle_request(agent_id: str, request: AgentRequest):
    ACTIVE_REQUESTS.labels(agent=agent_id).inc()
    start_time = time.time()

    try:
        response = await agent.run(request)
        REQUEST_COUNT.labels(agent=agent_id, status='success').inc()
        TOKEN_USAGE.labels(agent=agent_id, direction='input').inc(response.input_tokens)
        TOKEN_USAGE.labels(agent=agent_id, direction='output').inc(response.output_tokens)
        return response
    except Exception as e:
        REQUEST_COUNT.labels(agent=agent_id, status='error').inc()
        raise
    finally:
        duration = time.time() - start_time
        REQUEST_LATENCY.labels(agent=agent_id, status='success').observe(duration)
        ACTIVE_REQUESTS.labels(agent=agent_id).dec()
```

---

## Logging

### Structured Log Format

All logs follow a structured JSON format:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "service": "orchestrator",
  "trace_id": "abc123def456",
  "span_id": "789xyz",
  "agent_id": "customer-support-v2",
  "execution_id": "exec-001",
  "message": "Tool execution completed",
  "tool": "search_knowledge_base",
  "duration_ms": 150,
  "result_count": 5
}
```

### Log Levels

| Level | Use Case |
|-------|----------|
| ERROR | Failures requiring attention |
| WARN | Degraded performance or retries |
| INFO | Normal operations, milestones |
| DEBUG | Detailed debugging (off in prod) |

### Logging Implementation

```python
import structlog
from opentelemetry import trace

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = structlog.get_logger()

# Add trace context to logs
def add_trace_context(logger, method_name, event_dict):
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, '032x')
        event_dict["span_id"] = format(ctx.span_id, '016x')
    return event_dict

# Usage
async def execute_tool(tool_name: str, params: dict):
    logger.info(
        "tool_execution_started",
        tool=tool_name,
        param_count=len(params),
    )

    try:
        result = await tool.run(params)
        logger.info(
            "tool_execution_completed",
            tool=tool_name,
            duration_ms=result.duration_ms,
            success=True,
        )
        return result
    except Exception as e:
        logger.error(
            "tool_execution_failed",
            tool=tool_name,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
```

### Log Aggregation with Loki

```yaml
# loki-config.yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
  filesystem:
    directory: /loki/chunks
```

---

## Distributed Tracing

### Trace Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Trace: abc123def456                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Gateway] ─────────────────────────────────────────────────────────────────│
│  │ POST /api/v1/agents/invoke                                               │
│  │ Duration: 2500ms                                                          │
│  │                                                                           │
│  ├── [Auth] ─────────────────                                               │
│  │   │ JWT Validation                                                        │
│  │   │ Duration: 5ms                                                         │
│  │                                                                           │
│  ├── [Orchestrator] ────────────────────────────────────────────────────────│
│  │   │ Agent Execution                                                       │
│  │   │ Duration: 2400ms                                                      │
│  │   │                                                                       │
│  │   ├── [LLM Call #1] ─────────────                                        │
│  │   │   │ Reasoning step                                                    │
│  │   │   │ Duration: 800ms                                                   │
│  │   │   │ Tokens: 500 in, 150 out                                          │
│  │   │                                                                       │
│  │   ├── [Tool: search_kb] ────────                                         │
│  │   │   │ Knowledge base search                                            │
│  │   │   │ Duration: 200ms                                                   │
│  │   │   │ Results: 5                                                        │
│  │   │                                                                       │
│  │   ├── [LLM Call #2] ─────────────                                        │
│  │   │   │ Final response                                                    │
│  │   │   │ Duration: 1200ms                                                  │
│  │   │   │ Tokens: 800 in, 300 out                                          │
│  │                                                                           │
│  ├── [Response] ─────────                                                   │
│  │   │ Serialize & send                                                      │
│  │   │ Duration: 10ms                                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### OpenTelemetry Integration

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Setup tracer
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="localhost:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

# Instrument agent execution
async def execute_agent(agent_id: str, input: str):
    with tracer.start_as_current_span("agent_execution") as span:
        span.set_attribute("agent.id", agent_id)
        span.set_attribute("input.length", len(input))

        # Reasoning loop
        for i in range(max_iterations):
            with tracer.start_as_current_span(f"reasoning_step_{i}") as step_span:
                response = await llm.complete(prompt)
                step_span.set_attribute("tokens.input", response.input_tokens)
                step_span.set_attribute("tokens.output", response.output_tokens)

                if response.tool_call:
                    with tracer.start_as_current_span("tool_execution") as tool_span:
                        tool_span.set_attribute("tool.name", response.tool_call.name)
                        result = await execute_tool(response.tool_call)
                        tool_span.set_attribute("tool.success", result.success)

        span.set_attribute("iterations", i + 1)
        return final_response
```

### Jaeger Configuration

```yaml
# jaeger-config.yaml
collector:
  zipkin:
    http-port: 9411
  grpc-port: 14250
  http-port: 14268

query:
  port: 16686

storage:
  type: elasticsearch
  options:
    es:
      server-urls: http://elasticsearch:9200
      index-prefix: jaeger
```

---

## Dashboards

### Executive Dashboard

| Panel | Description |
|-------|-------------|
| Request Rate | Requests per second over time |
| Success Rate | Percentage of successful requests |
| P50/P95/P99 Latency | Response time percentiles |
| Error Rate | Percentage of failed requests |
| Active Users | Concurrent active sessions |

### Agent Performance Dashboard

| Panel | Description |
|-------|-------------|
| Iterations per Request | Average reasoning steps |
| Tool Usage Distribution | Which tools are called most |
| Token Consumption | Input/output tokens over time |
| Cost per Request | Estimated USD per request |
| Quality Scores | Accuracy, safety, hallucination |

### Infrastructure Dashboard

| Panel | Description |
|-------|-------------|
| CPU/Memory Usage | Resource utilization |
| Queue Depth | Pending requests |
| Database Connections | Connection pool status |
| Cache Hit Rate | Redis cache efficiency |
| Error Breakdown | Errors by type and service |

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "Agent Performance",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_requests_total[5m])",
            "legendFormat": "{{agent}} - {{status}}"
          }
        ]
      },
      {
        "title": "P95 Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(agent_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{agent}}"
          }
        ]
      },
      {
        "title": "Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_tokens_used_total[5m])",
            "legendFormat": "{{agent}} - {{direction}}"
          }
        ]
      }
    ]
  }
}
```

---

## Alerting

### Alert Rules

```yaml
# alerting-rules.yml
groups:
  - name: agent-alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(agent_requests_total{status="error"}[5m]))
          / sum(rate(agent_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(agent_request_duration_seconds_bucket[5m])) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s"

      - alert: SafetyViolation
        expr: increase(agent_safety_violations_total[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Safety violation detected"
          description: "Agent {{ $labels.agent }} triggered safety violation"

      - alert: HighTokenUsage
        expr: |
          sum(rate(agent_tokens_used_total[1h])) > 1000000
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "High token consumption"
          description: "Token usage is {{ $value | humanize }} per hour"
```

### Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'agent']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'

  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'

    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx'
        channel: '#alerts'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'xxx'
        severity: critical

  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx'
        channel: '#ai-platform-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .Annotations.description }}'
```

---

## On-Call Runbooks

### High Error Rate

1. Check error logs: `{service="orchestrator"} |= "error"`
2. Identify error types in metrics dashboard
3. Check downstream service health
4. Review recent deployments
5. Escalate if LLM provider issue

### High Latency

1. Check P95/P99 latency breakdown by component
2. Identify slow tool calls in traces
3. Check LLM API latency metrics
4. Review database query performance
5. Consider scaling if load-related

### Safety Violation

1. **Immediately** retrieve full trace for incident
2. Review input that triggered violation
3. Check if prompt injection attempt
4. Update safety filters if needed
5. File incident report

---

## References

- [Evaluation Framework](./eval-framework.md)
- [Reference Architecture](../architecture/reference-architecture.md)
- [Threat Model](../architecture/threat-model.md)
