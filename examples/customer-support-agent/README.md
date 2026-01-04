# Customer Support Agent Example

A complete example demonstrating the Enterprise AI Platform with a customer support use case.

## Overview

This example includes:

- **Customer Support Agent**: An AI agent configured for handling support inquiries
- **Knowledge Base**: Pre-loaded FAQ and policy documents with vector search
- **Tool Integration**: Search, order lookup, ticket creation, email (with approval)
- **Observability**: Prometheus, Grafana, and Jaeger for full visibility
- **Demo UI**: Simple chat interface for testing

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Anthropic API key

### 1. Set Environment Variables

```bash
# Create .env file
cat > .env << EOF
ANTHROPIC_API_KEY=your-api-key-here
JWT_SECRET=$(openssl rand -hex 32)
EOF
```

### 2. Start the Stack

```bash
docker-compose up -d
```

### 3. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| API Gateway | http://localhost:8080 | - |
| Demo UI | http://localhost:3000 | - |
| Grafana | http://localhost:3001 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Jaeger | http://localhost:16686 | - |

### 4. Test the Agent

```bash
# Create a session
curl -X POST http://localhost:8080/api/v1/agents/a1b2c3d4-e5f6-7890-abcd-ef1234567890/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "demo-user"}'

# Send a message (replace SESSION_ID with the returned session ID)
curl -X POST http://localhost:8080/api/v1/agents/a1b2c3d4-e5f6-7890-abcd-ef1234567890/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_ID",
    "input": "What is your return policy?"
  }'
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Docker Compose Stack                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│  │   Demo UI    │────▶│   Gateway    │────▶│ Orchestrator │            │
│  │   (React)    │     │  (FastAPI)   │     │ (LangGraph)  │            │
│  │   :3000      │     │    :8080     │     │              │            │
│  └──────────────┘     └──────────────┘     └──────┬───────┘            │
│                                                    │                    │
│                       ┌────────────────────────────┼─────────┐         │
│                       │                            │         │         │
│                       ▼                            ▼         ▼         │
│               ┌──────────────┐            ┌─────────────────────────┐  │
│               │  PostgreSQL  │            │         Redis           │  │
│               │  + pgvector  │            │     (Session Cache)     │  │
│               │    :5432     │            │        :6379            │  │
│               └──────────────┘            └─────────────────────────┘  │
│                                                                         │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐           │
│  │  Prometheus  │────▶│   Grafana    │     │    Jaeger    │           │
│  │    :9090     │     │    :3001     │     │   :16686     │           │
│  └──────────────┘     └──────────────┘     └──────────────┘           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features Demonstrated

### 1. Knowledge Base Search

The agent can search pre-loaded documents to answer questions:

```
User: "What's your return policy?"
Agent: [Uses search_knowledge_base tool]
       "Our return policy allows returns within 30 days of purchase..."
```

### 2. Order Lookup

Query order details by order ID:

```
User: "Where is my order #12345?"
Agent: [Uses lookup_order tool]
       "Your order #12345 was shipped on..."
```

### 3. Human-in-the-Loop

Sensitive actions require approval:

```
User: "Send me a confirmation email"
Agent: [Uses send_email tool - REQUIRES APPROVAL]
       "I've prepared an email for you. It's pending approval..."
```

### 4. Ticket Escalation

Complex issues can be escalated:

```
User: "I need to speak with a manager"
Agent: [Uses create_ticket tool]
       "I've created a support ticket #T-789. A manager will..."
```

## Configuration

### Agent Configuration

Edit `init-db.sql` to modify the agent:

```sql
UPDATE agents SET
  system_prompt = 'Your new prompt...',
  tools = '[...]'::jsonb
WHERE id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
```

### Adding Knowledge Base Documents

```sql
INSERT INTO documents (title, content, source, metadata)
VALUES ('New Article', 'Content here...', 'source', '{}');
```

### Policy Rules

Add approval requirements or rate limits:

```sql
INSERT INTO policy_rules (name, resource_pattern, action, conditions)
VALUES (
  'require_approval_for_refunds',
  'tool:process_refund',
  'require_approval',
  '{"approvers": ["finance"]}'::jsonb
);
```

## Monitoring

### Grafana Dashboards

Pre-configured dashboards:

1. **Agent Performance**: Request rate, latency, error rate
2. **Tool Usage**: Tool call distribution, approval rates
3. **Infrastructure**: CPU, memory, database connections

### Prometheus Metrics

Key metrics to monitor:

| Metric | Description |
|--------|-------------|
| `agent_requests_total` | Total agent invocations |
| `agent_request_duration_seconds` | Request latency histogram |
| `agent_tool_calls_total` | Tool usage by name |
| `agent_tokens_used_total` | LLM token consumption |

### Distributed Tracing

View request traces in Jaeger at http://localhost:16686

Each trace shows:
- Gateway request handling
- Agent reasoning steps
- Tool executions
- Database queries

## Troubleshooting

### Common Issues

**Agent not responding:**
```bash
# Check container logs
docker-compose logs gateway
docker-compose logs orchestrator
```

**Database connection errors:**
```bash
# Verify PostgreSQL is ready
docker-compose exec postgres pg_isready -U aiplatform
```

**Redis connection errors:**
```bash
# Test Redis connection
docker-compose exec redis redis-cli -a aiplatform ping
```

### Reset Everything

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Next Steps

1. **Add more tools**: Implement custom tools in the platform
2. **Expand knowledge base**: Add more documents via SQL or API
3. **Configure policies**: Set up approval workflows
4. **Production deployment**: See [deployment guides](../../docs/deploy/)

## Related Documentation

- [Reference Architecture](../../docs/architecture/reference-architecture.md)
- [Evaluation Framework](../../docs/llmops/eval-framework.md)
- [AWS Deployment](../../docs/deploy/aws.md)
