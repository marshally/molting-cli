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
- Consider: setuptools, poetry, or hatch

**Project metadata:**
```toml
[project]
name = "molting-cli"
version = "0.1.0"
description = "CLI tool for Python refactorings from Martin Fowler's catalog"
authors = [{name = "Marshall Yount", email = "..."}]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.8"
```

**Dependencies:**
```toml
dependencies = [
    "libcst>=1.0.0",      # Concrete Syntax Tree manipulation
    "rope>=1.9.0",        # Python refactoring library
    "click>=8.0.0",       # CLI framework
    "rich>=13.0.0",       # Terminal formatting (optional)
]
```

**Development dependencies:**
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
```

**CLI entry point:**
```toml
[project.scripts]
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
```

### 5. Installation Instructions

After setup, users should be able to:

```bash
# Install for development
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run CLI
molting --help
```

### 6. Initial Package Files

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

1. Create `pyproject.toml` with dependencies
2. Create package directory structure
3. Implement minimal CLI entry point
4. Test installation: `pip install -e .`
5. Verify CLI works: `molting --help`

## Notes

- Keep Python 3.8+ compatibility
- Use type hints throughout
- Follow PEP 8 style guide
- Use dataclasses for configuration objects
- Consider using Click for CLI framework (powerful, well-documented)
