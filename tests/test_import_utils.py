"""Tests for import utilities."""

import libcst as cst

from molting.core.import_utils import ensure_import, has_import


class TestHasImport:
    """Tests for has_import()."""

    def test_has_simple_import(self) -> None:
        """Test detecting a simple import."""
        code = """from typing import Protocol

class Foo:
    pass
"""
        module = cst.parse_module(code)
        assert has_import(module, "typing", "Protocol")

    def test_has_multiple_imports(self) -> None:
        """Test detecting import from a statement with multiple imports."""
        code = """from typing import Protocol, Any, cast

class Foo:
    pass
"""
        module = cst.parse_module(code)
        assert has_import(module, "typing", "Protocol")
        assert has_import(module, "typing", "Any")
        assert has_import(module, "typing", "cast")

    def test_does_not_have_import(self) -> None:
        """Test that missing import is not detected."""
        code = """from typing import Any

class Foo:
    pass
"""
        module = cst.parse_module(code)
        assert not has_import(module, "typing", "Protocol")

    def test_wrong_module(self) -> None:
        """Test that import from wrong module is not detected."""
        code = """from collections import Protocol

class Foo:
    pass
"""
        module = cst.parse_module(code)
        assert not has_import(module, "typing", "Protocol")

    def test_has_star_import(self) -> None:
        """Test detecting star import."""
        code = """from typing import *

class Foo:
    pass
"""
        module = cst.parse_module(code)
        assert has_import(module, "typing", "Protocol")
        assert has_import(module, "typing", "Any")

    def test_empty_module(self) -> None:
        """Test empty module has no imports."""
        code = ""
        module = cst.parse_module(code)
        assert not has_import(module, "typing", "Protocol")

    def test_module_with_no_imports(self) -> None:
        """Test module without imports."""
        code = """class Foo:
    pass
"""
        module = cst.parse_module(code)
        assert not has_import(module, "typing", "Protocol")

    def test_import_with_alias(self) -> None:
        """Test detecting import with alias."""
        code = """from typing import Protocol as P

class Foo:
    pass
"""
        module = cst.parse_module(code)
        # Should match the original name, not the alias
        assert has_import(module, "typing", "Protocol")


class TestEnsureImport:
    """Tests for ensure_import()."""

    def test_add_import_when_missing(self) -> None:
        """Test adding import when it doesn't exist."""
        code = """class Foo:
    pass
"""
        module = cst.parse_module(code)
        modified = ensure_import(module, "typing", ["Protocol"])

        # Verify the import was added
        assert has_import(modified, "typing", "Protocol")

        # Verify the class is still there
        assert "class Foo:" in modified.code

    def test_does_not_add_import_when_present(self) -> None:
        """Test that import is not duplicated when already present."""
        code = """from typing import Protocol

class Foo:
    pass
"""
        module = cst.parse_module(code)
        modified = ensure_import(module, "typing", ["Protocol"])

        # Should be unchanged
        assert modified.code == code

    def test_add_multiple_imports(self) -> None:
        """Test adding multiple imports at once."""
        code = """class Foo:
    pass
"""
        module = cst.parse_module(code)
        modified = ensure_import(module, "typing", ["Protocol", "Any", "cast"])

        # Verify all imports were added
        assert has_import(modified, "typing", "Protocol")
        assert has_import(modified, "typing", "Any")
        assert has_import(modified, "typing", "cast")

    def test_does_not_add_when_star_import(self) -> None:
        """Test that import is not added when star import exists."""
        code = """from typing import *

class Foo:
    pass
"""
        module = cst.parse_module(code)
        modified = ensure_import(module, "typing", ["Protocol"])

        # Should be unchanged since star import already exists
        assert modified.code == code

    def test_adds_import_at_beginning(self) -> None:
        """Test that import is added at the beginning of the file."""
        code = """class Foo:
    pass

class Bar:
    pass
"""
        module = cst.parse_module(code)
        modified = ensure_import(module, "typing", ["Protocol"])

        # Verify the import is at the beginning
        lines = modified.code.split("\n")
        assert "from typing import Protocol" in lines[0]

    def test_adds_import_after_existing_imports(self) -> None:
        """Test that import is added with other imports."""
        code = """import sys

class Foo:
    pass
"""
        module = cst.parse_module(code)
        modified = ensure_import(module, "typing", ["Protocol"])

        # Verify the import was added
        assert has_import(modified, "typing", "Protocol")

        # Verify both imports exist
        assert "import sys" in modified.code
        assert "from typing import Protocol" in modified.code

    def test_add_single_import(self) -> None:
        """Test adding a single import."""
        code = """class Foo:
    pass
"""
        module = cst.parse_module(code)
        modified = ensure_import(module, "typing", ["Protocol"])

        # Verify exactly one import was added
        assert modified.code.count("from typing import Protocol") == 1

    def test_empty_module(self) -> None:
        """Test adding import to empty module."""
        code = ""
        module = cst.parse_module(code)
        modified = ensure_import(module, "typing", ["Protocol"])

        # Verify the import was added
        assert has_import(modified, "typing", "Protocol")
