.PHONY: help bootstrap format lint typecheck test test-verbose clean install all check

UV ?= uv
UV_RUN = $(UV) run

# Default target - show help
help:
	@echo "Available targets:"
	@echo "  make bootstrap    - First-time setup: install project dependencies"
	@echo "  make format       - Auto-fix code formatting (black + ruff)"
	@echo "  make lint         - Check code style without modifying"
	@echo "  make typecheck    - Run mypy type checking"
	@echo "  make test         - Run tests"
	@echo "  make test-verbose - Run tests with verbose output"
	@echo "  make clean        - Remove generated files"
	@echo "  make install      - Sync dependencies with uv"
	@echo "  make all          - Format, typecheck, and test"
	@echo "  make check        - Lint, typecheck, and test (no auto-fix)"

# First-time setup
bootstrap: install
	@echo "✅ Bootstrap complete!"

# Auto-fix formatting and linting
format:
	@echo "→ Formatting with black..."
	$(UV_RUN) black .
	@echo "→ Auto-fixing with ruff..."
	$(UV_RUN) ruff check --fix .
	@echo "✅ Formatting complete"

# Check without modifying
lint:
	@echo "→ Checking code style with black..."
	$(UV_RUN) black --check .
	@echo "→ Linting with ruff..."
	$(UV_RUN) ruff check .
	@echo "✅ Lint checks passed"

# Type checking
typecheck:
	@echo "→ Type checking with mypy..."
	$(UV_RUN) mypy molting/ $$(find tests -name "*.py" ! -name "conftest.py" ! -path "*/fixtures/*")
	@echo "✅ Type checking passed"

# Run tests
test:
	@echo "→ Running tests..."
	$(UV_RUN) pytest tests/
	@echo "✅ Tests passed"

# Run tests with verbose output
test-verbose:
	@echo "→ Running tests (verbose)..."
	$(UV_RUN) pytest tests/ -v
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
	@echo "→ Syncing dependencies with uv..."
	$(UV) sync
	@echo "✅ Installation complete"

# Run everything (format, typecheck, test)
all: format typecheck test
	@echo "✅ All checks passed!"

# Check without auto-fixing (lint + typecheck + test)
check: lint typecheck test
	@echo "✅ All checks passed!"
