.PHONY: setup lint test clean help

# Default target
help:
	@echo "Available targets:"
	@echo "  setup  - Create venv and install dependencies"
	@echo "  lint   - Run linting (ruff)"
	@echo "  test   - Run tests"
	@echo "  clean  - Remove build artifacts and caches"

# Setup development environment
setup:
	python -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -e ".[test]"
	@echo ""
	@echo "Setup complete. Activate with: source venv/bin/activate"

# Run linting
lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

# Run tests
test:
	pytest tests/ -v

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -rf __pycache__/
	rm -rf src/__pycache__/
	rm -rf tests/__pycache__/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
