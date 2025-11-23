# Python Project Setup

## Overview

Setup tasks for configuring molting-cli as a Python package with proper dependencies and tooling.

## Current State

- Empty repository with documentation and test infrastructure
- No Python package structure yet
- No dependencies configured

## Required Setup

### 1. Project Structure

Create the following directory structure:

```
molting-cli/
  molting/              # Main package
    __init__.py
    cli.py              # CLI entry point
    core/               # Core refactoring engine
      __init__.py
      refactoring_base.py
    refactorings/       # Individual refactoring implementations
      __init__.py
      composing_methods/
        __init__.py
        extract_method.py
        inline_method.py
        ...
      moving_features/
        __init__.py
        move_method.py
        ...
    utils/              # Utilities
      __init__.py
      ast_helpers.py
      code_analysis.py
  tests/                # Already created
  docs/                 # Already created
  pyproject.toml        # Need to create
  README.md             # Already created
```

### 2. pyproject.toml Configuration

Create `pyproject.toml` with:

**Build system:**
- Use modern Python packaging (PEP 517/518)
- Use Poetry for dependency management and packaging

**Build system:**
```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

**Project metadata:**
```toml
[tool.poetry]
name = "molting-cli"
version = "0.1.0"
description = "CLI tool for Python refactorings from Martin Fowler's catalog"
authors = ["Marshall Yount <your-email@example.com>"]
readme = "README.md"
license = "MIT"
```

**Python version:**
```toml
[tool.poetry.dependencies]
python = "^3.8"
```

**Dependencies:**
```toml
[tool.poetry.dependencies]
python = "^3.8"
libcst = "^1.0.0"     # Concrete Syntax Tree manipulation
rope = "^1.9.0"       # Python refactoring library
click = "^8.0.0"      # CLI framework
rich = "^13.0.0"      # Terminal formatting
```

**Development dependencies:**
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
pytest-cov = "^4.0.0"
black = "^23.0.0"
ruff = "^0.1.0"
mypy = "^1.0.0"
```

**CLI entry point:**
```toml
[tool.poetry.scripts]
molting = "molting.cli:main"
```

### 3. Development Tools Configuration

**Black (formatting):**
```toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']
```

**Ruff (linting):**
```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
```

**Pytest:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

**MyPy (type checking):**
```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### 4. Additional Configuration Files

**.gitignore:**
```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/
venv/
env/
.env
.venv/
```

**Note:** `poetry.lock` should be **committed** to version control for this CLI application to ensure reproducible builds across all environments.

### 5. Virtual Environment Configuration

**Configure Poetry to use in-project venvs:**
```bash
# Set Poetry to create .venv in project directory (recommended)
poetry config virtualenvs.in-project true

# Verify configuration
poetry config --list
```

This creates `.venv/` in the project root, which:
- IDEs (VSCode, PyCharm) auto-detect
- Makes it clear which venv belongs to the project
- Simplifies cleanup (just delete `.venv/`)

**Alternative:** Poetry's default creates venvs in a centralized location (`~/Library/Caches/pypoetry/virtualenvs/` on macOS), which keeps the project directory clean but requires manual IDE configuration.

### 7. Installation Instructions

After setup, users should be able to:

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Configure in-project venvs (recommended)
poetry config virtualenvs.in-project true

# Install dependencies (creates .venv automatically)
poetry install

# Install without dev dependencies
poetry install --without dev

# Activate virtual environment
poetry shell

# Run CLI
molting --help

# Or run without activating shell
poetry run molting --help
```

### 8. Initial Package Files

**molting/__init__.py:**
```python
"""Molting CLI - Python refactoring tool based on Fowler's catalog."""

__version__ = "0.1.0"
```

**molting/cli.py:**
```python
"""CLI entry point for molting."""

import click

@click.group()
@click.version_option()
def main():
    """Molting - Python refactoring CLI tool."""
    pass

# Refactoring commands will be added here
```

## Next Steps

1. Initialize Poetry project: `poetry init` or create `pyproject.toml` manually
2. Create package directory structure
3. Implement minimal CLI entry point
4. Install dependencies: `poetry install`
5. Verify CLI works: `poetry run molting --help`

## Notes

- Keep Python 3.8+ compatibility
- Use type hints throughout
- Follow PEP 8 style guide
- Use dataclasses for configuration objects
- Using Click for CLI framework (powerful, well-documented, excellent for complex CLIs)
- Poetry manages virtual environments automatically
- Recommend in-project venvs (`.venv/`) for better IDE integration
- Commit `poetry.lock` for reproducible builds (this is a CLI application, not a library)
