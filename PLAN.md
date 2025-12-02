# Plan: Pattern Matching for Multiple Calls Refactoring

## Problem Statement

The `test_multiple_calls` tests for several simplifying conditionals refactorings require finding and replacing the same conditional pattern across multiple functions in a file. Currently skipped tests:

1. `consolidate_conditional_expression::test_multiple_calls`
2. `consolidate_duplicate_conditional_fragments::test_multiple_calls`
3. `decompose_conditional::test_multiple_calls`
4. `separate_query_from_modifier::test_multiple_calls`

### Example Transformation (consolidate_conditional_expression)

**Input:** Three functions with identical conditional patterns
```python
def disability_amount(employee):
    if employee.seniority < 2:
        return 0
    if employee.months_disabled > 12:
        return 0
    if employee.is_part_time:
        return 0
    return 100

def vacation_days(employee):
    if employee.seniority < 2:      # SAME PATTERN
        return 0
    # ... same conditions ...

def bonus_multiplier(employee):
    if employee.seniority < 2:      # SAME PATTERN (different return 0.5)
        return 0.5
    # ... same conditions ...
```

**Expected:** All three functions use the extracted helper
```python
def disability_amount(employee):
    if is_not_eligible_for_disability(employee):
        return 0
    return 100

def vacation_days(employee):
    if is_not_eligible_for_disability(employee):
        return 0
    # ...

def is_not_eligible_for_disability(employee):
    return employee.seniority < 2 or employee.months_disabled > 12 or employee.is_part_time
```

## Design Approach

### Core Concept: Condition-Based Pattern Matching

The key insight is that we need to match **conditions**, not return values. The same eligibility check appears in multiple functions but may return different values (0 vs 0.5).

### Phase 1: Pattern Signature

Create a canonical signature for a sequence of conditions:

```python
@dataclass
class ConditionalPatternSignature:
    """Hashable representation of a conditional pattern."""
    conditions: tuple[str, ...]  # Normalized condition strings
    num_statements: int
```

**Normalization Rules:**
1. Replace first function parameter with `$0`, second with `$1`, etc.
2. Strip whitespace and normalize formatting
3. Sort conditions alphabetically (OR is commutative)

Example: `employee.seniority < 2` → `$0.seniority < 2`

### Phase 2: Pattern Scanner

A visitor that finds all functions containing a matching pattern:

```python
class PatternScanner(cst.CSTVisitor):
    """Finds functions with matching conditional patterns."""

    def __init__(self, target_pattern: ConditionalPatternSignature):
        self.target_pattern = target_pattern
        self.matches: list[PatternMatch] = []
```

### Phase 3: Multi-Function Transformer

Modify existing transformers to:
1. Extract pattern from target function
2. Scan entire module for matches
3. Replace pattern in ALL matching functions
4. Add helper function once at module level

## Implementation Plan

### Step 1: Create `molting/core/conditional_pattern.py`

New module with:
- `ConditionalPatternSignature` dataclass
- `ConditionNormalizer` - transforms conditions to canonical form
- `PatternExtractor` - extracts pattern from target function
- `PatternScanner` - finds matching patterns across module

### Step 2: Modify `consolidate_conditional_expression.py`

1. After extracting conditions from target, create pattern signature
2. Scan module for other functions with same pattern
3. Store list of functions to transform
4. In `leave_FunctionDef`: check if current function is in transform list
5. In `leave_Module`: add helper function once

### Step 3: Apply Same Pattern to Other Commands

Apply the same infrastructure to:
- `decompose_conditional.py`
- `consolidate_duplicate_conditional_fragments.py`
- `separate_query_from_modifier.py`

### Step 4: Update Tests

Remove skip markers and verify all tests pass.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `molting/core/conditional_pattern.py` | Create | Pattern infrastructure |
| `molting/commands/simplifying_conditionals/consolidate_conditional_expression.py` | Modify | Add multi-function support |
| `tests/simplifying_conditionals/test_consolidate_conditional_expression.py` | Modify | Remove skip marker |

## Estimated Complexity

- **Pattern Infrastructure**: ~150 lines
- **Transformer Modifications**: ~50 lines per command
- **Testing**: Existing fixtures should work

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| False positives (unrelated patterns match) | Exact condition match required, not structural similarity |
| Different parameter names (`emp` vs `employee`) | Positional placeholder normalization |
| Order-sensitive matching | Sort conditions alphabetically |

## Alternative Approaches Rejected

1. **Text-based regex matching** - Too fragile, can't handle formatting
2. **Direct AST hash comparison** - Includes variable names, won't match renames
3. **Full semantic analysis** - Overkill for this use case
