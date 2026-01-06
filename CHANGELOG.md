# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

## [0.1.0] - 2026-01-06

Initial alpha release of Enterprise AI Platform reference implementation.

### Added
- FastAPI gateway with JWT/API key authentication
- LangGraph-based agent orchestrator with ReAct pattern
- OPA-style policy engine for governance
- Multi-tier memory system (Redis + PostgreSQL + pgvector)
- LLMOps evaluation framework with golden datasets
- AI Readiness Assessment CLI tool (`goodai-assess`)
- Architecture documentation
- Deployment guides for AWS, Azure, GCP, and on-premises
- Infrastructure-as-code (Terraform, Helm, Docker Compose)
- GitHub Actions CI/CD pipelines
- Customer support agent example
- Comprehensive test suite (64 tests)

### Security
- Zero-trust agent design patterns
- Capability-based tool access
- Human-in-the-loop approval gates
- Input sanitization and output filtering
- Threat model documentation
- Async Redis implementation to prevent blocking
- Thread-safe API key loading
- Proper error handling for Redis operations

### Known Limitations
- Platform components are alpha quality
- Requires customization for production use
- Not all documented features are fully implemented
- External service integrations are mocked in tests

---

## Versioning

- **Major (X.0.0)**: Breaking changes
- **Minor (0.X.0)**: New features, backward compatible
- **Patch (0.0.X)**: Bug fixes, security patches
