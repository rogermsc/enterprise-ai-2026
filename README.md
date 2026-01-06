# Enterprise AI Platform

A reference implementation for deploying AI agents in enterprise environments with security, observability, and governance patterns.

[![CI](https://github.com/rogermsc/enterprise-ai-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/rogermsc/enterprise-ai-2026/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What This Is

- A **reference architecture** for enterprise AI agent deployment
- A **learning resource** demonstrating security, observability, and governance patterns
- A **starting point** for teams building their own AI agent infrastructure
- A collection of **working examples** with tests and documentation

## What This Is NOT

- **Not production-ready out of the box** - requires customization for your environment
- **Not a managed service** - you are responsible for deployment, operations, and security
- **Not fully battle-tested** - this is v0.1.0, expect rough edges
- **Not a substitute for security review** - have your team review before deploying

---

## Quickstart (< 5 minutes)

### Option 1: Run the CLI Tool

```bash
# Clone and install
git clone https://github.com/rogermsc/enterprise-ai-2026
cd enterprise-ai-2026
pip install -e .

# Run AI readiness assessment
goodai-assess data/enterprise_mature.json
```

### Option 2: Run Tests

```bash
# Install dev dependencies
pip install -e ".[test]"

# Run tests
pytest tests/ -v
```

### Option 3: Explore the Platform Code

```bash
# Install platform dependencies
pip install -e "platform/[test]"

# Run platform tests (no external services needed for unit tests)
pytest tests/ -v
```

---

## Components

| Component | Description | Status |
|-----------|-------------|--------|
| **Gateway** | FastAPI API gateway with auth, rate limiting, audit logging | Alpha |
| **Orchestrator** | LangGraph agent engine with ReAct pattern | Alpha |
| **Policy Engine** | OPA-style rules for governance | Alpha |
| **Memory** | Redis + PostgreSQL + pgvector memory system | Alpha |
| **Eval Framework** | Testing framework with golden datasets | Alpha |
| **CLI Tool** | AI readiness assessment scorer | Stable |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                              │
│   JWT/API Key Auth  │  RBAC  │  Rate Limiting  │  Audit Logs    │
└─────────────────────────────────────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
  │   POLICY    │◄─────▶│ ORCHESTRATOR│◄─────▶│   MEMORY    │
  │   ENGINE    │       │ (LangGraph) │       │   SERVICE   │
  └─────────────┘       └──────┬──────┘       └─────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   TOOL EXECUTION    │
                    └─────────────────────┘
```

## Project Structure

```
enterprise-ai-2026/
├── platform/           # Core platform code (Alpha)
│   ├── gateway/        # API gateway
│   ├── orchestrator/   # Agent engine
│   ├── policy/         # Policy engine
│   ├── memory/         # Memory service
│   └── eval/           # Evaluation framework
├── src/                # CLI tool (Stable)
│   └── goodai_assess/  # AI readiness scorer
├── tests/              # Test suite
├── docs/               # Documentation
├── examples/           # Example implementations
└── infra/              # Infrastructure-as-code
```

## Development

```bash
# Setup
make setup

# Run linter
make lint

# Run tests
make test

# Clean up
make clean
```

## Documentation

- [Architecture Overview](./docs/architecture/reference-architecture.md)
- [Security Patterns](./docs/architecture/zero-trust-agent-design.md)
- [Deployment Guides](./docs/deploy/)
- [Contributing](./CONTRIBUTING.md)

## Requirements

- Python 3.11+
- Docker (for full platform)
- Redis + PostgreSQL (for platform services)

## License

MIT License - see [LICENSE](./LICENSE)

## Security

See [SECURITY.md](./SECURITY.md) for vulnerability reporting.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.
