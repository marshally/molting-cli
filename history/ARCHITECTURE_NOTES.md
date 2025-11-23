# Architecture Notes

## Overview

Architecture design for molting-cli, focusing on how libCST and rope will work together to implement refactorings.

## Core Technologies

### libCST (LibraryCodeSyntaxTree)
**Purpose:** Lossless Python code transformation

**Strengths:**
- Preserves all formatting, comments, whitespace
- Type-safe API with full AST access
- Built for code transformation tools
- Maintains exact source code structure

**Use cases:**
- Precise code modifications
- Extracting/moving code blocks
- Renaming with format preservation
- Custom refactorings

**Example:**
```python
import libcst as cst

# Parse code
module = cst.parse_module(source_code)

# Transform using visitor pattern
class ExtractMethodTransformer(cst.CSTTransformer):
    def leave_FunctionDef(self, original_node, updated_node):
        # Transformation logic
        return updated_node

# Apply transformation
new_module = module.visit(ExtractMethodTransformer())
```

### rope
**Purpose:** Python refactoring library with high-level operations

**Strengths:**
- Pre-built refactoring operations (rename, extract, inline)
- Understands Python scoping and references
- Handles cross-file refactorings
- Built-in safety checks

**Use cases:**
- Renaming (handles all references)
- Move method/field
- Extract variable/method
- Inline operations

**Example:**
```python
from rope.base.project import Project
from rope.refactor.extract import ExtractMethod

project = Project('.')
resource = project.get_file('module.py')

# Extract method refactoring
extractor = ExtractMethod(project, resource, start, end)
changes = extractor.get_changes('new_method_name')
project.do(changes)
```

## Proposed Architecture

### Layered Design

```
┌─────────────────────────────────────┐
│         CLI Layer (cli.py)          │  ← Click commands, argument parsing
├─────────────────────────────────────┤
│   Refactoring Dispatcher            │  ← Route to specific refactoring
├─────────────────────────────────────┤
│   Individual Refactorings           │  ← One class per refactoring type
│   (extract_method.py, rename.py)    │
├─────────────────────────────────────┤
│   Core Engine (Strategy Pattern)    │  ← Choose libCST vs rope vs hybrid
├─────────────────────────────────────┤
│   Utilities & Helpers               │  ← AST analysis, target parsing
└─────────────────────────────────────┘
```

### Strategy: When to Use Each Tool

**Use rope for:**
- Rename (variable, method, class, module)
- Move method/field (cross-file)
- Operations requiring scope analysis
- When pre-built refactorings exist and work well

**Use libCST for:**
- Extract method/function (precise control over formatting)
- Inline operations (preserve exact formatting)
- Complex transformations not in rope
- When formatting preservation is critical
- Custom refactorings not in rope

**Hybrid approach:**
- Use rope for analysis, libCST for transformation
- Example: rope finds all references, libCST modifies each one

### Core Abstractions

**1. Refactoring Base Class:**
```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

class Refactoring(ABC):
    """Base class for all refactorings."""

    @abstractmethod
    def apply(self, target: Path, **params) -> None:
        """Apply the refactoring to the target file."""
        pass

    @abstractmethod
    def validate_params(self, **params) -> None:
        """Validate refactoring parameters."""
        pass
```

**2. Target Specification:**
```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class RefactoringTarget:
    """Represents a refactoring target using pytest-style syntax."""

    file_path: Path
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    symbol_name: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None

    @classmethod
    def parse(cls, target_string: str) -> 'RefactoringTarget':
        """Parse 'path/file.py::Class::method#L10-L15' format."""
        # Implementation
        pass
```

**3. Refactoring Engine Interface:**
```python
class RefactoringEngine(ABC):
    """Interface for different refactoring engines (rope, libCST, hybrid)."""

    @abstractmethod
    def extract_method(self, target: RefactoringTarget, name: str) -> None:
        pass

    @abstractmethod
    def rename(self, target: RefactoringTarget, new_name: str) -> None:
        pass
```

### Module Structure

```
molting/
  cli.py                    # CLI entry point (Click commands)
  core/
    refactoring_base.py     # Base Refactoring class
    target.py               # RefactoringTarget parsing
    engine/
      base.py               # RefactoringEngine interface
      rope_engine.py        # Rope-based engine
      libcst_engine.py      # LibCST-based engine
      hybrid_engine.py      # Combines both
  refactorings/
    composing_methods/
      extract_method.py     # Uses libCST
      inline_method.py      # Uses libCST
      rename.py             # Uses rope (not in composing, but example)
    moving_features/
      move_method.py        # Uses rope
    # ... other categories
  utils/
    ast_helpers.py          # AST analysis utilities
    code_analysis.py        # Code inspection helpers
    formatting.py           # Code formatting utilities
```

## Key Design Decisions

### 1. Target Specification Format
- Use pytest-style: `file.py::Class::method::symbol`
- GitHub-style line numbers: `#L10-L15`
- Parse once, validate early

### 2. Error Handling
- Validate targets before applying
- Provide clear error messages
- Support dry-run mode (show what would change)

### 3. File Modification Strategy
- Always work on file paths (not strings)
- Read → Transform → Write pattern
- Support in-place modification
- Consider backup/undo mechanism

### 4. Testing Strategy
- Test each refactoring independently
- Use fixture files (already implemented)
- AST-based validation
- Test both rope and libCST paths

## Implementation Phases

### Phase 1: Foundation
1. Set up package structure
2. Implement target parsing
3. Create base classes
4. Build minimal CLI

### Phase 2: Proof of Concept
1. Implement one simple refactoring (rename using rope)
2. Implement one complex refactoring (extract method using libCST)
3. Validate with existing test fixtures

### Phase 3: Expand Coverage
1. Implement remaining composing methods
2. Add moving features refactorings
3. Continue through categories

### Phase 4: Polish
1. Add dry-run mode
2. Improve error messages
3. Add progress indicators
4. Documentation

## Open Questions

1. **Should we support multi-file refactorings?**
   - Pros: More powerful, rope supports it
   - Cons: More complex, harder to test
   - Decision: Start single-file, add multi-file later

2. **Backup/undo mechanism?**
   - Options: Git integration, manual backups, in-memory undo
   - Decision: Rely on version control initially

3. **Configuration file support?**
   - Options: .molting.toml for project-wide settings
   - Decision: Add later if needed

4. **Interactive mode?**
   - Show preview, ask for confirmation
   - Decision: Add as optional flag

## Resources

- [libCST Documentation](https://libcst.readthedocs.io/)
- [rope Documentation](https://rope.readthedocs.io/)
- [Fowler's Refactoring Catalog](https://refactoring.com/catalog/)
- [Click Documentation](https://click.palletsprojects.com/)
