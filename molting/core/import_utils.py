"""Utilities for managing imports in CST modules."""

import libcst as cst


def has_import(module: cst.Module, module_name: str, import_name: str) -> bool:
    """Check if a specific import exists.

    Args:
        module: The module to check
        module_name: The module being imported from (e.g., "typing")
        import_name: The name being imported (e.g., "Protocol")

    Returns:
        True if the import exists
    """
    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine):
            for item in stmt.body:
                if isinstance(item, cst.ImportFrom):
                    if isinstance(item.module, cst.Name):
                        if item.module.value == module_name:
                            # Check for star import
                            if isinstance(item.names, cst.ImportStar):
                                return True
                            # Check for specific import
                            if isinstance(item.names, (list, tuple)):
                                for name in item.names:
                                    if isinstance(name, cst.ImportAlias):
                                        if isinstance(name.name, cst.Name):
                                            if name.name.value == import_name:
                                                return True
    return False


def ensure_import(module: cst.Module, module_name: str, names: list[str]) -> cst.Module:
    """Add import if not already present.

    Args:
        module: The module to modify
        module_name: The module to import from
        names: List of names to import

    Returns:
        Modified module with import added
    """
    # Check if all names are already imported
    all_imported = all(has_import(module, module_name, name) for name in names)
    if all_imported:
        return module

    # Create the import statement
    import_aliases = [cst.ImportAlias(name=cst.Name(name)) for name in names]
    import_stmt = cst.SimpleStatementLine(
        body=[
            cst.ImportFrom(
                module=cst.Name(module_name),
                names=import_aliases,
            )
        ]
    )

    # Insert at the beginning (after any existing imports)
    new_body = [import_stmt] + list(module.body)

    return module.with_changes(body=new_body)
