# Proof of Concept Plan

## Objective

Implement a minimal working refactoring to validate the architecture and test infrastructure.

## Recommended First Implementation

**Extract Method** - A good proof-of-concept because:
- Representative of complex refactorings
- Tests the full stack (CLI → Engine → libCST)
- Already has test fixtures created
- Well-documented in Fowler's catalog
- Medium complexity (not too simple, not too complex)

## Implementation Steps

### Step 1: Basic Project Setup

1. **Create `pyproject.toml`** with minimal dependencies:
   ```toml
   [project]
   name = "molting-cli"
   dependencies = ["libcst>=1.0.0", "click>=8.0.0"]
   ```

2. **Create package structure:**
   ```bash
   mkdir -p molting/core molting/refactorings/composing_methods molting/utils
   touch molting/__init__.py
   touch molting/cli.py
   touch molting/core/__init__.py
   ```

3. **Verify installation:**
   ```bash
   pip install -e .
   molting --help  # Should work
   ```

### Step 2: Implement Target Parser

**File:** `molting/core/target.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re

@dataclass
class RefactoringTarget:
    """Parse pytest-style targets with GitHub line numbers."""

    file_path: Path
    class_name: Optional[str] = None
    method_name: Optional[str] = None
    symbol_name: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None

    @classmethod
    def parse(cls, target: str) -> 'RefactoringTarget':
        """
        Parse: 'path/file.py::Class::method#L10-L15'

        Examples:
            'foo.py' → file only
            'foo.py::MyClass' → class
            'foo.py::MyClass::method' → method
            'foo.py::MyClass::method#L10-L15' → method with lines
            'foo.py::MyClass::method#L10' → single line
        """
        # Split on '#' for line numbers
        if '#' in target:
            path_part, line_part = target.split('#', 1)
            line_start, line_end = cls._parse_lines(line_part)
        else:
            path_part = target
            line_start = line_end = None

        # Split on '::' for path/class/method
        parts = path_part.split('::')
        file_path = Path(parts[0])

        class_name = parts[1] if len(parts) > 1 else None
        method_name = parts[2] if len(parts) > 2 else None
        symbol_name = parts[3] if len(parts) > 3 else None

        return cls(
            file_path=file_path,
            class_name=class_name,
            method_name=method_name,
            symbol_name=symbol_name,
            line_start=line_start,
            line_end=line_end,
        )

    @staticmethod
    def _parse_lines(line_part: str) -> tuple[Optional[int], Optional[int]]:
        """Parse 'L10-L15' or 'L10' into (start, end)."""
        match = re.match(r'L(\d+)(?:-L(\d+))?', line_part)
        if not match:
            raise ValueError(f"Invalid line range: {line_part}")

        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start

        return start, end
```

**Test it:**
```python
# Quick validation
target = RefactoringTarget.parse("foo.py::Order::print_owing#L6-L8")
assert target.file_path == Path("foo.py")
assert target.class_name == "Order"
assert target.method_name == "print_owing"
assert target.line_start == 6
assert target.line_end == 8
```

### Step 3: Implement Extract Method with libCST

**File:** `molting/refactorings/composing_methods/extract_method.py`

```python
import libcst as cst
from pathlib import Path
from molting.core.target import RefactoringTarget

class ExtractMethodRefactoring:
    """Extract a code block into a new method."""

    def __init__(self, target: RefactoringTarget, new_method_name: str):
        self.target = target
        self.new_method_name = new_method_name

    def apply(self) -> None:
        """Apply the refactoring to the target file."""
        # Read file
        source = self.target.file_path.read_text()

        # Parse with libCST
        module = cst.parse_module(source)

        # Transform (extract lines into new method)
        transformer = ExtractMethodTransformer(
            class_name=self.target.class_name,
            method_name=self.target.method_name,
            line_start=self.target.line_start,
            line_end=self.target.line_end,
            new_method_name=self.new_method_name,
        )

        new_module = module.visit(transformer)

        # Write back
        self.target.file_path.write_text(new_module.code)


class ExtractMethodTransformer(cst.CSTTransformer):
    """LibCST transformer to extract method."""

    def __init__(self, class_name, method_name, line_start, line_end, new_method_name):
        self.class_name = class_name
        self.method_name = method_name
        self.line_start = line_start
        self.line_end = line_end
        self.new_method_name = new_method_name
        self.extracted_statements = []

    def leave_ClassDef(self, original_node, updated_node):
        """Find target class and add extracted method."""
        if original_node.name.value != self.class_name:
            return updated_node

        # Add new method to class body
        if self.extracted_statements:
            new_method = self._create_new_method()
            new_body = list(updated_node.body.body) + [new_method]
            return updated_node.with_changes(
                body=updated_node.body.with_changes(body=new_body)
            )

        return updated_node

    def leave_FunctionDef(self, original_node, updated_node):
        """Find target method and replace extracted lines."""
        if original_node.name.value != self.method_name:
            return updated_node

        # Extract statements in line range
        new_body = []
        for i, stmt in enumerate(updated_node.body.body):
            line_num = self._get_line_number(stmt)

            if self.line_start <= line_num <= self.line_end:
                # Save for new method
                self.extracted_statements.append(stmt)

                # Replace with method call (only once)
                if line_num == self.line_start:
                    call = self._create_method_call()
                    new_body.append(call)
            else:
                new_body.append(stmt)

        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )

    def _create_new_method(self):
        """Create the extracted method definition."""
        # Simplified - would need proper implementation
        return cst.FunctionDef(
            name=cst.Name(self.new_method_name),
            params=cst.Parameters(),
            body=cst.IndentedBlock(body=self.extracted_statements),
        )

    def _create_method_call(self):
        """Create 'self.new_method()' call."""
        # Simplified
        return cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name(self.new_method_name),
                        )
                    )
                )
            ]
        )

    def _get_line_number(self, node):
        """Get line number of a node."""
        # LibCST provides position info
        metadata = self.get_metadata(cst.PositionProvider, node, None)
        return metadata.start.line if metadata else 0
```

### Step 4: Create CLI Command

**File:** `molting/cli.py`

```python
import click
from pathlib import Path
from molting.core.target import RefactoringTarget
from molting.refactorings.composing_methods.extract_method import ExtractMethodRefactoring

@click.group()
@click.version_option(version="0.1.0")
def main():
    """Molting - Python refactoring CLI tool."""
    pass

@main.command()
@click.argument('target')
@click.argument('new_method_name')
def extract_method(target: str, new_method_name: str):
    """
    Extract a code block into a new method.

    Example:
        molting extract-method Order.py::Order::print_owing#L6-L8 print_banner
    """
    try:
        parsed_target = RefactoringTarget.parse(target)
        refactoring = ExtractMethodRefactoring(parsed_target, new_method_name)
        refactoring.apply()
        click.echo(f"✓ Extracted method '{new_method_name}'")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    main()
```

### Step 5: Test It

1. **Run existing test:**
   ```bash
   pytest tests/test_composing_methods.py::TestExtractMethod::test_simple -v
   ```

2. **Manual test:**
   ```bash
   # Create test file
   cp tests/fixtures/composing_methods/extract_method/simple/input.py /tmp/test.py

   # Run refactoring
   molting extract-method /tmp/test.py::Order::print_owing#L6-L8 print_banner

   # Check result
   cat /tmp/test.py
   ```

3. **Validate:**
   - Does it extract the right lines?
   - Does it create the new method?
   - Does it preserve formatting?
   - Does the test pass?

## Success Criteria

✅ `pip install -e .` works
✅ `molting --help` shows commands
✅ `molting extract-method` command exists
✅ Can parse target specifications
✅ Can extract simple method
✅ Existing test passes
✅ Manual test produces correct output

## Next Steps After POC

Once extract-method works:

1. **Refactor and generalize:**
   - Extract common patterns into base classes
   - Improve error handling
   - Add validation

2. **Implement second refactoring:**
   - Choose something different (e.g., rename using rope)
   - Validates the architecture supports both engines

3. **Add more test fixtures:**
   - Edge cases
   - Complex scenarios
   - Error cases

4. **Improve CLI:**
   - Better error messages
   - Add --dry-run flag
   - Add --verbose flag

## Notes

- Start simple, iterate quickly
- Use test fixtures to validate
- Don't over-engineer early
- Get something working end-to-end first
- libCST has good documentation - reference it often
- The metadata system in libCST is key for line numbers

## Resources for Implementation

- [libCST Quickstart](https://libcst.readthedocs.io/en/latest/tutorial.html)
- [libCST Transformers](https://libcst.readthedocs.io/en/latest/tutorial.html#Working-with-Transformers)
- [libCST Metadata](https://libcst.readthedocs.io/en/latest/metadata.html)
- [Click Documentation](https://click.palletsprojects.com/en/8.1.x/)
