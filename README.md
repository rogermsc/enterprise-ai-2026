# Enterprise AI Platform

**Production-grade AI agent orchestration for the enterprise**

A complete reference implementation for deploying secure, scalable AI agents in enterprise environments. Built with zero-trust security, comprehensive observability, and infrastructure-as-code.

[![CI](https://github.com/rogermsc/enterprise-ai-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/rogermsc/enterprise-ai-2026/actions/workflows/ci.yml)
[![Security](https://github.com/rogermsc/enterprise-ai-2026/actions/workflows/security.yml/badge.svg)](https://github.com/rogermsc/enterprise-ai-2026/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

This platform provides everything needed to deploy AI agents in production:

| Component | Description |
|-----------|-------------|
| **Gateway** | FastAPI-based API gateway with auth, rate limiting, audit logging |
| **Orchestrator** | LangGraph-powered agent engine with ReAct pattern |
| **Policy Engine** | OPA-style rules for governance and approval workflows |
| **Memory** | Multi-tier memory (Redis + PostgreSQL + pgvector) |
| **Eval Framework** | LLMOps testing with golden datasets and CI/CD gates |

## Quick Start

### Run the Example

```bash
# Clone the repository
git clone https://github.com/rogermsc/enterprise-ai-2026
cd enterprise-ai-2026/examples/customer-support-agent

# Create .env file with required secrets
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY and generate passwords

# Start the stack
docker-compose up -d

# Test the agent
curl -X POST http://localhost:8080/api/v1/agents/a1b2c3d4-e5f6-7890-abcd-ef1234567890/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": "What is your return policy?"}'
```

**Access the services:**
- API: http://localhost:8080
- Demo UI: http://localhost:3000
- Grafana: http://localhost:3001
- Jaeger: http://localhost:16686

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENTERPRISE NETWORK                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         API GATEWAY (FastAPI)                         │   │
│  │   • JWT/API Key Auth  • RBAC  • Rate Limiting  • Audit Logging       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐             │
│         ▼                          ▼                          ▼             │
│  ┌─────────────┐          ┌─────────────────┐          ┌─────────────┐     │
│  │   POLICY    │◄────────▶│  ORCHESTRATOR   │◄────────▶│   MEMORY    │     │
│  │   ENGINE    │          │  (LangGraph)    │          │   SERVICE   │     │
│  │   (OPA)     │          │  • ReAct Loop   │          │ Redis/pgvec │     │
│  └─────────────┘          │  • Human-in-Loop│          └─────────────┘     │
│                           │  • Tool Sandbox │                               │
│                           └────────┬────────┘                               │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       TOOL EXECUTION LAYER                            │   │
│  │   Search │ Database │ Email │ Slack │ Custom Tools                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features

### Security

- **Zero-Trust Design**: Every tool call verified, capability-based access
- **Human-in-the-Loop**: Configurable approval gates for sensitive actions
- **Tool Sandboxing**: Isolated execution with resource limits
- **PII Detection**: Automatic scanning and filtering of sensitive data
- **Audit Logging**: Complete trace of all agent actions

### Observability

- **Distributed Tracing**: End-to-end request visibility with Jaeger/OTLP
- **Metrics**: Prometheus metrics for latency, token usage, errors
- **Dashboards**: Pre-built Grafana dashboards
- **Alerting**: Configurable alerts for anomalies and safety violations

### LLMOps

- **Evaluation Framework**: Golden datasets with semantic similarity scoring
- **CI/CD Integration**: Quality gates in GitHub Actions
- **Regression Detection**: Automated detection of quality degradation
- **A/B Testing**: Statistical comparison of agent variants

## Documentation

### Architecture

- [Reference Architecture](./docs/architecture/reference-architecture.md) - Full system design
- [Threat Model](./docs/architecture/threat-model.md) - Security analysis
- [Zero-Trust Agent Design](./docs/architecture/zero-trust-agent-design.md) - Security patterns

### LLMOps

- [Evaluation Framework](./docs/llmops/eval-framework.md) - Testing AI agents
- [Observability Guide](./docs/llmops/observability.md) - Monitoring and alerting

### Deployment

- [AWS Deployment](./docs/deploy/aws.md) - EKS, RDS, ElastiCache
- [Azure Deployment](./docs/deploy/azure.md) - AKS, PostgreSQL, Redis
- [GCP Deployment](./docs/deploy/gcp.md) - GKE, Cloud SQL, Memorystore
- [On-Premises](./docs/deploy/onprem.md) - Self-hosted Kubernetes

## Project Structure

```
enterprise-ai-2026/
├── platform/                    # Core platform code
│   ├── gateway/                 # API gateway (FastAPI)
│   ├── orchestrator/            # Agent engine (LangGraph)
│   ├── policy/                  # Policy engine (OPA-style)
│   ├── memory/                  # Memory service
│   └── eval/                    # Evaluation framework
├── docs/                        # Documentation
│   ├── architecture/            # Architecture docs
│   ├── llmops/                  # LLMOps guides
│   └── deploy/                  # Deployment guides
├── examples/                    # Example implementations
│   └── customer-support-agent/  # Full example with docker-compose
├── infra/                       # Infrastructure as code
│   ├── terraform/               # Terraform modules
│   ├── helm/                    # Helm charts
│   └── docker/                  # Dockerfiles
├── src/                         # Assessment CLI tool
│   └── goodai_assess/           # AI readiness scorer
└── .github/workflows/           # CI/CD pipelines
```

## AI Readiness Assessment CLI

Included is a standalone CLI tool for assessing enterprise AI readiness:

```bash
# Install
pip install -e .

# Run assessment
goodai-assess data/enterprise_mature.json
```

The tool produces deterministic scores across six dimensions: Strategy, Data Foundation, Infrastructure, Governance, Delivery, and Adoption.

See [CLI Documentation](./docs/cli.md) for details.

## Installation

### Platform

```bash
# Install platform dependencies
pip install -e "platform/[all]"
```

### CLI Tool

```bash
# Install CLI
pip install -e .
```

### Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"
pip install -e "platform/[dev]"

# Run tests
pytest tests/ platform/tests/ -v
```

## Deployment

### Kubernetes (Helm)

```bash
helm install ai-platform ./infra/helm/ai-platform \
  --namespace ai-platform \
  --create-namespace \
  --set gateway.replicaCount=3 \
  --set externalPostgresql.host=your-db-host
```

### Terraform (AWS)

```bash
cd infra/terraform
terraform init
terraform apply -var-file=environments/prod.tfvars
```

### Docker Compose

```bash
cd examples/customer-support-agent
docker-compose up -d
```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## Security

See [SECURITY.md](./SECURITY.md) for security policy and vulnerability reporting.

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

## About Good AI

Good AI is an enterprise AI consultancy specializing in production AI deployments.

**Methodology:** Identify → Pilot → Instrument → Learn → Scale/Sunset

**Website:** [wearegoodai.com](https://wearegoodai.com)
