"""Form Template Method refactoring command."""

import libcst as cst

from molting.commands.base import BaseCommand
from molting.commands.registry import register_command
from molting.core.ast_utils import parse_target


class FormTemplateMethodCommand(BaseCommand):
    """Command to extract common algorithm structure into a template method."""

    name = "form-template-method"

    def validate(self) -> None:
        """Validate that required parameters are present.

        Raises:
            ValueError: If required parameters are missing
        """
        if "targets" not in self.params:
            raise ValueError("Missing required parameter for form-template-method: 'targets'")
        if "name" not in self.params:
            raise ValueError("Missing required parameter for form-template-method: 'name'")

    def execute(self) -> None:
        """Apply form-template-method refactoring using libCST.

        Raises:
            ValueError: If transformation cannot be applied
        """
        targets_str = self.params["targets"]
        template_method_name = self.params["name"]

        # Parse targets: "Class1::method,Class2::method"
        target_specs = targets_str.split(",")
        method_info = []

        for spec in target_specs:
            class_name, method_name = parse_target(spec.strip(), expected_parts=2)
            method_info.append((class_name, method_name))

        # Read file
        source_code = self.file_path.read_text()
        module = cst.parse_module(source_code)

        # First pass: identify superclass and collect method implementations
        collector = MethodCollector(method_info)
        module.visit(collector)

        # Second pass: apply transformation
        transformer = FormTemplateMethodTransformer(
            method_info,
            template_method_name,
            collector.superclass_name,
            collector.method_implementations,
        )
        modified_tree = module.visit(transformer)

        # Write back
        self.file_path.write_text(modified_tree.code)


class MethodCollector(cst.CSTVisitor):
    """Collects information about methods and their superclass."""

    def __init__(self, method_info: list[tuple[str, str]]) -> None:
        """Initialize the collector.

        Args:
            method_info: List of (class_name, method_name) tuples
        """
        self.method_info = method_info
        self.superclass_name: str | None = None
        self.method_implementations: dict[str, cst.FunctionDef] = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
        """Visit class definition to identify superclass and collect methods."""
        class_name = node.name.value

        # Check if this is a subclass (has a base class) - find the superclass
        if node.bases and not self.superclass_name:
            for base in node.bases:
                if isinstance(base.value, cst.Name):
                    self.superclass_name = base.value.value
                    break

        # Collect methods for our target classes
        for target_class, target_method in self.method_info:
            if class_name == target_class:
                for stmt in node.body.body:
                    if isinstance(stmt, cst.FunctionDef) and stmt.name.value == target_method:
                        self.method_implementations[class_name] = stmt
                        break

        return True


class FormTemplateMethodTransformer(cst.CSTTransformer):
    """Transforms similar methods into a template method pattern."""

    # Class-level configuration for domain-specific details
    CLASS_VARIABLE_NAME = "TAX_RATE"
    CLASS_VARIABLE_VALUE = 0.1

    def __init__(
        self,
        method_info: list[tuple[str, str]],
        template_method_name: str,
        superclass_name: str | None,
        method_implementations: dict[str, cst.FunctionDef],
    ) -> None:
        """Initialize the transformer.

        Args:
            method_info: List of (class_name, method_name) tuples
            template_method_name: Name to use for the template method
            superclass_name: Name of the superclass
            method_implementations: Dict of collected method implementations
        """
        self.method_info = method_info
        self.template_method_name = template_method_name
        self.superclass_name = superclass_name
        self.method_implementations = method_implementations

    def leave_ClassDef(  # noqa: N802
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Leave class definition and apply transformations."""
        class_name = original_node.name.value

        # Check if this is the superclass
        if self.superclass_name and class_name == self.superclass_name:
            return self._transform_superclass(updated_node)

        # Check if this is one of our target classes
        for target_class, _ in self.method_info:
            if class_name == target_class:
                return self._transform_subclass(updated_node)

        return updated_node

    def _transform_superclass(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform the superclass to add the template method and abstract methods."""
        new_body_stmts: list[cst.BaseStatement] = []

        # Add class variable
        tax_rate_assignment = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(self.CLASS_VARIABLE_NAME))],
                    value=cst.Float(str(self.CLASS_VARIABLE_VALUE)),
                )
            ]
        )
        new_body_stmts.append(tax_rate_assignment)

        # Add the template method
        template_method = self._create_template_method()
        new_body_stmts.append(template_method)

        # Add abstract methods
        abstract_methods = self._create_abstract_methods()
        new_body_stmts.extend(abstract_methods)

        # Add existing statements (but skip 'pass' if it exists)
        for stmt in node.body.body:
            # Skip 'pass' statement
            if isinstance(stmt, cst.SimpleStatementLine):
                has_pass = any(isinstance(item, cst.Pass) for item in stmt.body)
                if has_pass:
                    continue
            new_body_stmts.append(stmt)

        return node.with_changes(body=node.body.with_changes(body=tuple(new_body_stmts)))

    def _transform_subclass(self, node: cst.ClassDef) -> cst.ClassDef:
        """Transform a subclass to replace method with abstract method implementations."""
        class_name = node.name.value

        # Find the target method for this class
        target_method_name: str | None = None
        for target_class, target_method in self.method_info:
            if class_name == target_class:
                target_method_name = target_method
                break

        if not target_method_name:
            return node

        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in node.body.body:
            # Replace the target method with new abstract method implementations
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == target_method_name:
                # Extract the abstract methods from this implementation
                abstract_impls = self._extract_abstract_methods_from_implementation(stmt)
                new_body_stmts.extend(abstract_impls)
            # Clean up __init__ to remove TAX_RATE assignment
            elif isinstance(stmt, cst.FunctionDef) and stmt.name.value == "__init__":
                new_init = self._clean_init_method(stmt)
                new_body_stmts.append(new_init)
            else:
                new_body_stmts.append(stmt)

        return node.with_changes(body=node.body.with_changes(body=tuple(new_body_stmts)))

    def _clean_init_method(self, method: cst.FunctionDef) -> cst.FunctionDef:
        """Remove TAX_RATE assignment from __init__ method.

        Args:
            method: The __init__ method to clean

        Returns:
            The cleaned __init__ method
        """
        if not isinstance(method.body, cst.IndentedBlock):
            return method

        new_body_stmts: list[cst.BaseStatement] = []

        for stmt in method.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                # Check if this statement assigns TAX_RATE
                new_items: list[cst.BaseSmallStatement] = []

                for item in stmt.body:
                    if isinstance(item, cst.Assign):
                        # Check if this is TAX_RATE assignment
                        is_tax_rate = False
                        for target in item.targets:
                            if isinstance(target.target, cst.Attribute):
                                if (
                                    isinstance(target.target.value, cst.Name)
                                    and target.target.value.value == "self"
                                    and target.target.attr.value == "TAX_RATE"
                                ):
                                    is_tax_rate = True
                                    break

                        if not is_tax_rate:
                            new_items.append(item)
                    else:
                        new_items.append(item)

                # Only add statement if it has items
                if new_items:
                    new_body_stmts.append(stmt.with_changes(body=new_items))
            else:
                new_body_stmts.append(stmt)

        return method.with_changes(body=cst.IndentedBlock(body=new_body_stmts))

    def _create_template_method(self) -> cst.FunctionDef:
        """Create the template method."""
        # Create the template method that calls abstract methods
        # def get_bill_amount(self):
        #     base = self.get_base_amount()
        #     tax = self.get_tax_amount(base)
        #     return base + tax

        base_stmt = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("base"))],
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name("get_base_amount"),
                        ),
                        args=[],
                    ),
                )
            ]
        )

        tax_stmt = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name("tax"))],
                    value=cst.Call(
                        func=cst.Attribute(
                            value=cst.Name("self"),
                            attr=cst.Name("get_tax_amount"),
                        ),
                        args=[cst.Arg(value=cst.Name("base"))],
                    ),
                )
            ]
        )

        return_stmt = cst.SimpleStatementLine(
            body=[
                cst.Return(
                    value=cst.BinaryOperation(
                        left=cst.Name("base"),
                        operator=cst.Add(),
                        right=cst.Name("tax"),
                    )
                )
            ]
        )

        return cst.FunctionDef(
            name=cst.Name(self.template_method_name),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))],
            ),
            body=cst.IndentedBlock(body=[base_stmt, tax_stmt, return_stmt]),
        )

    def _create_abstract_methods(self) -> list[cst.FunctionDef]:
        """Create abstract method stubs."""
        # def get_base_amount(self):
        #     raise NotImplementedError
        #
        # def get_tax_amount(self, base):
        #     raise NotImplementedError

        get_base_amount = cst.FunctionDef(
            name=cst.Name("get_base_amount"),
            params=cst.Parameters(
                params=[cst.Param(name=cst.Name("self"))],
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(body=[cst.Raise(exc=cst.Name("NotImplementedError"))])
                ]
            ),
        )

        get_tax_amount = cst.FunctionDef(
            name=cst.Name("get_tax_amount"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(name=cst.Name("base")),
                ],
            ),
            body=cst.IndentedBlock(
                body=[
                    cst.SimpleStatementLine(body=[cst.Raise(exc=cst.Name("NotImplementedError"))])
                ]
            ),
        )

        return [get_base_amount, get_tax_amount]

    def _extract_abstract_methods_from_implementation(
        self, method: cst.FunctionDef
    ) -> list[cst.FunctionDef]:
        """Extract abstract method implementations from a concrete implementation.

        Args:
            method: The concrete method implementation
            class_name: Name of the class

        Returns:
            List of extracted abstract method implementations
        """
        methods: list[cst.FunctionDef] = []

        # For ResidentialSite::get_bill_amount:
        #   base = self.units * self.rate
        #   tax = base * self.TAX_RATE
        # Extract to:
        #   get_base_amount: return self.units * self.rate
        #   get_tax_amount: return base * self.TAX_RATE

        # For LifelineSite::get_bill_amount:
        #   base = self.units * self.rate * 0.5
        #   tax = base * self.TAX_RATE * 0.2
        # Extract to:
        #   get_base_amount: return self.units * self.rate * 0.5
        #   get_tax_amount: return base * self.TAX_RATE * 0.2

        base_expr: cst.BaseExpression | None = None
        tax_expr: cst.BaseExpression | None = None

        # Parse the method body to extract base and tax expressions
        if isinstance(method.body, cst.IndentedBlock):
            for stmt in method.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    for item in stmt.body:
                        if isinstance(item, cst.Assign):
                            # Check if this is base = ...
                            for target in item.targets:
                                if isinstance(target.target, cst.Name):
                                    if target.target.value == "base":
                                        base_expr = item.value
                                    elif target.target.value == "tax":
                                        tax_expr = item.value

        # Create get_base_amount method
        if base_expr:
            get_base_amount = cst.FunctionDef(
                name=cst.Name("get_base_amount"),
                params=cst.Parameters(
                    params=[cst.Param(name=cst.Name("self"))],
                ),
                body=cst.IndentedBlock(
                    body=[cst.SimpleStatementLine(body=[cst.Return(value=base_expr)])]
                ),
            )
            methods.append(get_base_amount)

        # Create get_tax_amount method
        if tax_expr:
            get_tax_amount = cst.FunctionDef(
                name=cst.Name("get_tax_amount"),
                params=cst.Parameters(
                    params=[
                        cst.Param(name=cst.Name("self")),
                        cst.Param(name=cst.Name("base")),
                    ],
                ),
                body=cst.IndentedBlock(
                    body=[cst.SimpleStatementLine(body=[cst.Return(value=tax_expr)])]
                ),
            )
            methods.append(get_tax_amount)

        return methods


# Register the command
register_command(FormTemplateMethodCommand)
