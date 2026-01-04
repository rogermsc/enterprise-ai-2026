# Contributing to Enterprise AI Platform

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. We expect all contributors to:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what is best for the community

## Getting Started

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Git

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/enterprise-ai-2026.git
   cd enterprise-ai-2026
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   pip install -e "platform/[dev]"
   ```

4. **Start local services**
   ```bash
   cd examples/customer-support-agent
   docker-compose up -d postgres redis
   ```

5. **Run tests**
   ```bash
   pytest tests/ platform/tests/ -v
   ```

## Development Workflow

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test improvements

Example: `feature/add-streaming-support`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

Example:
```
feat(orchestrator): add streaming response support

Implement SSE-based streaming for agent responses to improve
perceived latency for long-running requests.

Closes #123
```

### Code Style

We use automated tools to maintain code quality:

- **Ruff**: Linting and formatting
- **MyPy**: Type checking

Run before committing:
```bash
ruff check --fix platform/ src/
ruff format platform/ src/
mypy platform/ src/
```

### Testing

- Write tests for all new functionality
- Maintain >80% code coverage
- Use meaningful test names

```python
# Good
def test_agent_returns_error_when_tool_not_found():
    ...

# Bad
def test_agent():
    ...
```

Run tests:
```bash
# All tests
pytest

# With coverage
pytest --cov=platform --cov-report=html

# Specific test file
pytest platform/tests/test_orchestrator.py -v
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make your changes**
   - Write clean, documented code
   - Add tests
   - Update documentation if needed

3. **Ensure all checks pass**
   ```bash
   ruff check platform/ src/
   ruff format --check platform/ src/
   mypy platform/ src/
   pytest
   ```

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature
   ```

5. **PR Description Template**
   ```markdown
   ## Summary
   Brief description of changes

   ## Changes
   - Change 1
   - Change 2

   ## Testing
   How were these changes tested?

   ## Checklist
   - [ ] Tests added/updated
   - [ ] Documentation updated
   - [ ] Changelog updated (if applicable)
   ```

### Review Process

- All PRs require at least one approval
- CI must pass
- Resolve all comments before merging
- Squash commits when merging

## Documentation

- Update relevant docs with code changes
- Use clear, concise language
- Include code examples where helpful
- Keep the README up to date

## Reporting Issues

### Bug Reports

Include:
- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Error messages and logs

### Feature Requests

Include:
- Clear, descriptive title
- Use case and motivation
- Proposed solution (if any)
- Alternatives considered

## Security Issues

See [SECURITY.md](./SECURITY.md) for reporting security vulnerabilities.

## Community

- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Use GitHub Issues for bugs and features
- **Discord**: [Join our community](https://discord.gg/example)

## Recognition

Contributors are recognized in:
- Release notes
- Contributors list
- Annual contributor highlights

## Questions?

Feel free to open a discussion or reach out to the maintainers.

Thank you for contributing!
