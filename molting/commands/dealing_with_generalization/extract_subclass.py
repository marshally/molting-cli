"""Extract Subclass refactoring command."""

from typing import cast

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_comma_separated_list
from molting.core.code_generation_utils import create_init_method, create_parameter
from molting.core.visitors import SelfFieldChecker


class ExtractSubclassCommand(BaseCommand):
    """Extract Subclass refactoring: create a new subclass for a subset of features.

    Extract Subclass creates a new subclass to hold features (fields and methods)
    that are only used in some instances of the parent class. This refactoring is
    useful when a class has features that are only sometimes used, causing
    unnecessary complexity. By moving these conditional features into a subclass,
    the parent class becomes simpler and the code's intent becomes clearer.

    The refactoring:
    1. Creates a new subclass that inherits from the parent class
    2. Moves specified features (fields and methods) to the subclass
    3. Removes feature parameters and assignments from the parent's __init__
    4. Removes feature-specific logic (if statements) from parent methods
    5. Overrides methods in the subclass with feature-specific implementations

    **When to use:**
    - A class has several features that are only used in some instances
    - A class has numerous conditional checks (if statements) based on type flags
    - You want to eliminate feature envy or type code in the parent class
    - The class is becoming too complex due to optional or variant behavior

    **Example:**

    Before:
        class Employee:
            def __init__(self, name, hourly_rate, is_labor):
                self.name = name
                self.hourly_rate = hourly_rate
                self.is_labor = is_labor

            def pay_amount(self):
                if self.is_labor:
                    return self.hourly_rate * 160
                else:
                    return self.hourly_rate

    After:
        class Employee:
            def __init__(self, name, hourly_rate):
                self.name = name
                self.hourly_rate = hourly_rate

            def pay_amount(self):
                return self.hourly_rate

        class LaborEmployee(Employee):
            def __init__(self, name, hourly_rate):
                super().__init__(name, hourly_rate)

            def pay_amount(self):
                return self.hourly_rate * 160
    """

    name = "extract-subclass"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_required_params("target", "features", "name")

    def execute(self) -> None:
        """Apply extract-subclass refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        target_class = self.params["target"]
        features_str = self.params["features"]
        subclass_name = self.params["name"]

        # Parse features to extract
        features = parse_comma_separated_list(features_str)

        # Check for name conflicts - if the subclass name already exists, skip
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)
        for stmt in module.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == subclass_name:
                # Class with target name already exists, skip the refactoring
                return

        # Apply transformation
        self.apply_libcst_transform(
            ExtractSubclassTransformer, target_class, features, subclass_name
        )


class ExtractSubclassTransformer(cst.CSTTransformer):
    """Transforms a class to extract a subclass."""

    def __init__(self, target_class: str, features: list[str], subclass_name: str) -> None:
        """Initialize the transformer.

        Args:
            target_class: Name of the class to extract from
            features: List of features (fields/methods) to move to subclass
            subclass_name: Name of the new subclass
        """
        self.target_class = target_class
        self.features = set(features)
        self.subclass_name = subclass_name
        self.target_class_def: cst.ClassDef | None = None
        self.original_feature_params: list[str] = []
        self.original_non_feature_params: list[str] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definition to capture target class."""
        if node.name.value == self.target_class:
            # Capture the original class definition before any transformations
            self.target_class_def = node
            self._capture_original_params(node)
        return True

    def _capture_original_params(self, class_def: cst.ClassDef) -> None:
        """Capture original parameters before transformation.

        Args:
            class_def: The class definition
        """
        # Find __init__ in original class
        for stmt in class_def.body.body:
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == "__init__":
                    if isinstance(stmt.params, cst.Parameters):
                        for param in stmt.params.params:
                            if param.name.value != "self":
                                if param.name.value in self.features:
                                    self.original_feature_params.append(param.name.value)
                                else:
                                    self.original_non_feature_params.append(param.name.value)
                    break

    def leave_Module(  # noqa: N802
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Leave module and insert the subclass."""
        if not self.target_class_def:
            return updated_node

        # Find the position to insert the subclass (after target class)
        new_body: list[cst.BaseStatement] = []
        target_found = False

        for stmt in updated_node.body:
            new_body.append(stmt)
            if isinstance(stmt, cst.ClassDef):
                if stmt.name.value == self.target_class:
                    target_found = True
                    # Insert subclass after the target class
                    subclass = self._create_subclass(stmt)
                    new_body.append(subclass)

        if not target_found:
            return updated_node

        return updated_node.with_changes(body=tuple(new_body))

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and remove features that will be in subclass."""
        if original_node.name.value != self.target_class:
            return updated_node

        # Update __init__ to remove feature parameters and assignments
        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in updated_node.body.body:
            stmt = cast(cst.BaseStatement, stmt)
            if isinstance(stmt, cst.FunctionDef):
                if stmt.name.value == "__init__":
                    # Transform __init__ to remove feature parameters
                    stmt = self._transform_parent_init_method(stmt)
                    new_body_stmts.append(stmt)
                elif self._method_uses_features(stmt):
                    # Transform method to remove feature-specific logic
                    stmt = self._transform_parent_method(stmt)
                    new_body_stmts.append(stmt)
                else:
                    # Keep methods that don't use features
                    new_body_stmts.append(stmt)
            else:
                new_body_stmts.append(stmt)

        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=tuple(new_body_stmts))
        )

    def _transform_parent_init_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform the __init__ method to remove feature parameters and assignments.

        Args:
            node: The __init__ method to transform

        Returns:
            The transformed __init__ method
        """
        # Filter out feature parameters
        new_params = [create_parameter("self")]
        if isinstance(node.params, cst.Parameters):
            for param in node.params.params:
                if param.name.value != "self" and param.name.value not in self.features:
                    new_params.append(param)

        # Filter out feature assignments
        new_stmts: list[cst.BaseStatement] = []

        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    # Check if this is a self.feature assignment
                    if not self._is_feature_assignment(stmt):
                        new_stmts.append(stmt)
                else:
                    new_stmts.append(stmt)

        # Ensure we have at least one statement
        if not new_stmts:
            new_stmts.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        return node.with_changes(
            params=cst.Parameters(params=new_params), body=cst.IndentedBlock(body=new_stmts)
        )

    def _transform_parent_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform a method to remove feature-specific logic.

        Args:
            node: The method to transform

        Returns:
            The transformed method
        """
        # Remove if statements that check features
        new_stmts: list[cst.BaseStatement] = []

        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.If):
                    # Check if this if checks a feature
                    if self._if_checks_feature(stmt):
                        # Keep only the else clause
                        if stmt.orelse:
                            if isinstance(stmt.orelse, cst.Else):
                                else_stmts = cast(
                                    tuple[cst.BaseStatement, ...], stmt.orelse.body.body
                                )
                                new_stmts.extend(else_stmts)
                        continue
                new_stmts.append(stmt)

        if not new_stmts:
            new_stmts.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        return node.with_changes(body=cst.IndentedBlock(body=new_stmts))

    def _if_checks_feature(self, if_stmt: cst.If) -> bool:
        """Check if an if statement checks a feature.

        Args:
            if_stmt: The if statement to check

        Returns:
            True if the if statement checks a feature
        """
        checker = SelfFieldChecker(target_fields=self.features)
        if_stmt.test.visit(checker)
        return checker.found

    def _create_subclass(self, parent_class: cst.ClassDef) -> cst.ClassDef:
        """Create the subclass with extracted features.

        Args:
            parent_class: The parent class definition

        Returns:
            The new subclass definition
        """
        # Use the original parameters captured before transformation
        feature_params = self.original_feature_params
        non_feature_params = self.original_non_feature_params

        # Create __init__ method for subclass
        # The subclass needs:
        # 1. Non-feature params that will be passed to super (except those with defaults)
        # 2. Feature params that are actual fields (not boolean flags)

        # Determine which params the subclass should take
        # We need to figure out which non-feature params to include and which to give defaults
        subclass_param_names = []

        # Analyze which non-feature params to include
        for param_name in non_feature_params:
            # Skip params that might have default values in subclass
            if self._should_skip_param_in_subclass(param_name):
                continue
            subclass_param_names.append(param_name)

        # Add only non-boolean feature parameters (actual fields, not flags)
        # is_labor is a boolean flag indicating type, so we skip it
        # employee is an actual field, so we include it
        feature_field_names = []
        for param_name in feature_params:
            # Skip boolean flags like is_labor
            if self._is_boolean_flag(param_name):
                continue
            feature_field_names.append(param_name)

        # All params for the subclass __init__
        all_param_names = subclass_param_names + feature_field_names

        # Create super().__init__() call with non-feature params
        super_args = []
        for param_name in non_feature_params:
            if param_name in subclass_param_names:
                super_args.append(cst.Arg(value=cst.Name(param_name)))
            else:
                # Provide default value
                super_args.append(cst.Arg(value=cst.Integer("0")))

        # Create field assignments dict for feature fields
        # (create_init_method will auto-create self.param = param for each param)
        field_assignments: dict[str, cst.BaseExpression] = {
            field: cst.Name(field) for field in feature_field_names
        }

        init_method = create_init_method(
            params=all_param_names,
            field_assignments=field_assignments,
            super_call_args=super_args,
        )

        # Create methods for subclass - override methods that use features
        methods: list[cst.BaseStatement] = [init_method]

        # Find methods in parent that should be overridden in subclass
        # We need to use the original class definition, not the transformed one
        original_class = self.target_class_def
        if original_class:
            for stmt in original_class.body.body:
                if isinstance(stmt, cst.FunctionDef):
                    if stmt.name.value != "__init__" and self._method_uses_features(stmt):
                        # Transform method to use feature-specific logic only
                        transformed_method = self._transform_subclass_method(stmt)
                        methods.append(transformed_method)

        # Create the subclass
        subclass = cst.ClassDef(
            name=cst.Name(self.subclass_name),
            bases=[cst.Arg(value=cst.Name(self.target_class))],
            body=cst.IndentedBlock(body=methods),
        )

        return subclass

    def _transform_subclass_method(self, node: cst.FunctionDef) -> cst.FunctionDef:
        """Transform a method for the subclass to use feature-specific logic.

        Args:
            node: The method to transform

        Returns:
            The transformed method
        """
        # Extract only the feature-specific logic from if statements
        # If we find an if checking features, we only keep that branch and stop processing
        new_stmts: list[cst.BaseStatement] = []
        found_feature_if = False

        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.If):
                    # Check if this if checks a feature
                    if self._if_checks_feature(stmt):
                        # Keep only the if clause (feature-specific logic)
                        if isinstance(stmt.body, cst.IndentedBlock):
                            new_stmts.extend(stmt.body.body)
                        found_feature_if = True
                        # Stop processing - we found the feature-specific branch
                        break
                # If we haven't found a feature if yet, keep other statements
                if not found_feature_if:
                    new_stmts.append(stmt)

        if not new_stmts:
            new_stmts.append(cst.SimpleStatementLine(body=[cst.Pass()]))

        return node.with_changes(body=cst.IndentedBlock(body=new_stmts))

    def _is_feature_assignment(self, stmt: cst.SimpleStatementLine) -> bool:
        """Check if a statement assigns to a feature field.

        Args:
            stmt: The statement to check

        Returns:
            True if statement assigns to a feature field
        """
        for body_stmt in stmt.body:
            if isinstance(body_stmt, cst.Assign):
                for target in body_stmt.targets:
                    if isinstance(target.target, cst.Attribute):
                        if isinstance(target.target.value, cst.Name):
                            if target.target.value.value == "self":
                                field_name = target.target.attr.value
                                if field_name in self.features:
                                    return True
        return False

    def _is_boolean_flag(self, param_name: str) -> bool:
        """Check if a parameter name indicates a boolean flag.

        Args:
            param_name: Name of the parameter

        Returns:
            True if parameter is likely a boolean flag
        """
        return "is_" in param_name or param_name.startswith("has_")

    def _should_skip_param_in_subclass(self, param_name: str) -> bool:
        """Check if a param should be skipped in subclass (will have default value).

        Args:
            param_name: Name of the parameter

        Returns:
            True if param should be skipped
        """
        # Heuristic: skip params that might be replaced by feature-specific values
        # Common patterns: *_price, *_value when features include actual values
        return param_name.endswith("_price") or param_name.endswith("_value")

    def _method_uses_features(self, method: cst.FunctionDef) -> bool:
        """Check if a method uses any of the features being extracted.

        Args:
            method: The method to check

        Returns:
            True if the method uses features
        """
        checker = SelfFieldChecker(target_fields=self.features)
        method.body.visit(checker)
        return checker.found


# Register the command
register_command(ExtractSubclassCommand)
