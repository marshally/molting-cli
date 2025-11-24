.PHONY: help bootstrap format lint typecheck test test-verbose clean install all check

# Default target - show help
help:
	@echo "Available targets:"
	@echo "  make bootstrap    - First-time setup: install poetry and dependencies"
	@echo "  make format       - Auto-fix code formatting (black + ruff)"
	@echo "  make lint         - Check code style without modifying"
	@echo "  make typecheck    - Run mypy type checking"
	@echo "  make test         - Run tests"
	@echo "  make test-verbose - Run tests with verbose output"
	@echo "  make clean        - Remove generated files"
	@echo "  make install      - Install dependencies with poetry"
	@echo "  make all          - Format, typecheck, and test"
	@echo "  make check        - Lint and typecheck (no auto-fix)"

# First-time setup - install poetry if needed, then install dependencies
bootstrap:
	@echo "→ Checking for Poetry..."
	@if command -v poetry >/dev/null 2>&1; then \
		echo "✓ Poetry is already installed"; \
		poetry --version; \
	elif command -v pipx >/dev/null 2>&1; then \
		echo "→ Installing Poetry via pipx..."; \
		pipx install poetry; \
		echo "✅ Poetry installed successfully via pipx"; \
	else \
		echo "→ pipx not found, using official Poetry installer..."; \
		curl -sSL https://install.python-poetry.org | python3 -; \
		echo "✅ Poetry installed successfully"; \
		echo "⚠️  You may need to add Poetry to your PATH:"; \
		echo "    export PATH=\"\$$HOME/.local/bin:\$$PATH\""; \
	fi
	@echo "→ Installing project dependencies..."
	@poetry install
	@echo "✅ Bootstrap complete!"

# Auto-fix formatting and linting
format:
	@echo "→ Formatting with black..."
	black .
	@echo "→ Auto-fixing with ruff..."
	ruff check --fix .
	@echo "✅ Formatting complete"

# Check without modifying
lint:
	@echo "→ Checking code style with black..."
	black --check .
	@echo "→ Linting with ruff..."
	ruff check .
	@echo "✅ Lint checks passed"

# Type checking
typecheck:
	@echo "→ Type checking with mypy..."
	mypy molting/ $$(find tests -name "*.py" ! -name "conftest.py" ! -path "*/fixtures/*")
	@echo "✅ Type checking passed"

# Run tests
test:
	@echo "→ Running tests..."
	pytest tests/
	@echo "✅ Tests passed"

# Run tests with verbose output
test-verbose:
	@echo "→ Running tests (verbose)..."
	pytest tests/ -v
	@echo "✅ Tests passed"

# Clean generated files
clean:
	@echo "→ Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Install dependencies
install:
	@echo "→ Installing dependencies with poetry..."
	poetry install
	@echo "✅ Installation complete"

# Run everything (format, typecheck, test)
all: format typecheck test
	@echo "✅ All checks passed!"

# Check without auto-fixing (lint + typecheck + test)
check: lint typecheck test
	@echo "✅ All checks passed!"
