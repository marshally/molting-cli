# GitHub Copilot Instructions for molting-cli

## Project Overview

**molting-cli** is a Python CLI tool for automated code refactoring based on Martin Fowler's "Refactoring" catalog. It uses libCST and AST transformations to apply refactoring patterns safely and consistently.

**Key Features:**
- 50+ refactoring patterns from Fowler's catalog
- Safe AST-based transformations
- Test-driven development workflow
- Comprehensive test coverage

## Tech Stack

- **Language**: Python 3.12+
- **AST Libraries**: libcst, ast
- **CLI Framework**: Custom command pattern
- **Testing**: pytest
- **Formatting**: black, ruff
- **Type Checking**: mypy

## Coding Guidelines

### Testing
- Always write tests for new refactoring commands
- Use test-driven development (TDD) approach
- Run `pytest` before committing
- Maintain test coverage for all refactoring patterns

### Code Style
- Run `black` and `ruff` before committing
- Follow existing patterns in `molting/commands/` for new commands
- Use type hints throughout
- Update docs when changing behavior

### Git Workflow
- Always commit `.beads/issues.jsonl` with code changes
- Run `bd sync` at end of work sessions
- Install git hooks: `bd hooks install`

## Issue Tracking with bd

**CRITICAL**: This project uses **bd** for ALL task tracking. Do NOT create markdown TODO lists.

### Essential Commands

```bash
# Find work
bd ready --json                    # Unblocked issues
bd stale --days 30 --json          # Forgotten issues

# Create and manage
bd create "Title" -t bug|feature|task -p 0-4 --json
bd update <id> --status in_progress --json
bd close <id> --reason "Done" --json

# Search
bd list --status open --priority 1 --json
bd show <id> --json

# Sync (CRITICAL at end of session!)
bd sync  # Force immediate export/commit/push
```

### Workflow

1. **Check ready work**: `bd ready --json`
2. **Claim task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** `bd create "Found bug" -p 1 --deps discovered-from:<parent-id> --json`
5. **Complete**: `bd close <id> --reason "Done" --json`
6. **Sync**: `bd sync` (flushes changes to git immediately)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

## Project Structure

```
molting-cli/
├── molting/
│   ├── commands/              # Refactoring commands by category
│   │   ├── base.py           # BaseCommand class
│   │   ├── registry.py       # Command registration
│   │   ├── composing_methods/
│   │   ├── moving_features/
│   │   ├── organizing_data/
│   │   ├── simplifying_conditionals/
│   │   ├── simplifying_method_calls/
│   │   └── dealing_with_generalization/
│   ├── core/                 # Core utilities
│   │   ├── ast_utils.py     # AST helper functions
│   │   ├── visitors.py      # Reusable CST visitors
│   │   └── import_utils.py  # Import management
│   └── cli.py               # CLI entry point
├── tests/                    # Test suite
│   ├── test_*.py            # Test files by category
│   └── fixtures/            # Test fixtures
└── .beads/
    ├── beads.db            # SQLite database (DO NOT COMMIT)
    └── issues.jsonl        # Git-synced issue storage
```

## Available Resources

### MCP Server (Recommended)
Use the beads MCP server for native function calls instead of shell commands:
- Install: `pip install beads-mcp`
- Functions: `mcp__beads__ready()`, `mcp__beads__create()`, etc.

### Key Documentation
- **AGENTS.md** - Comprehensive AI agent guide
- **README.md** - User-facing documentation
- **REFACTORING_TODO.md** - Refactoring backlog and progress

## Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Run `bd sync` at end of sessions
- ✅ Write tests before implementing refactorings
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT commit `.beads/beads.db` (JSONL only)
- ❌ Do NOT skip test coverage

---

**For detailed workflows and advanced features, see [AGENTS.md](../AGENTS.md)**
