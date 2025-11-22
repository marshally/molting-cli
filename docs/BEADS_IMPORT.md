---
priority: 2
type: task
status: open
---

# Simple rope refactorings

Epic for refactorings that can be implemented using rope's text-based refactoring capabilities.

## Implement Rename Method refactoring

Implement the Rename Method refactoring from test_simplifying_method_calls.py using rope.

Test class: TestRenameMethod

## Implement Add Parameter refactoring

Implement the Add Parameter refactoring from test_simplifying_method_calls.py using rope.

Test class: TestAddParameter

## Implement Remove Parameter refactoring

Implement the Remove Parameter refactoring from test_simplifying_method_calls.py using rope.

Test class: TestRemoveParameter

# Simple libCST refactorings

Epic for refactorings that can be implemented using libCST's AST-based transformations within a single file.

## Implement Extract Method refactoring

Implement the Extract Method refactoring from test_composing_methods.py using libCST.

Test class: TestExtractMethod

## Implement Extract Function refactoring

Implement the Extract Function refactoring from test_composing_methods.py using libCST.

Test class: TestExtractFunction

## Implement Inline Method refactoring

Implement the Inline Method refactoring from test_composing_methods.py using libCST.

Test class: TestInlineMethod

## Implement Inline Temp refactoring

Implement the Inline Temp refactoring from test_composing_methods.py using libCST.

Test class: TestInlineTemp

## Implement Replace Temp with Query refactoring

Implement the Replace Temp with Query refactoring from test_composing_methods.py using libCST.

Test class: TestReplaceTempWithQuery

## Implement Introduce Explaining Variable refactoring

Implement the Introduce Explaining Variable refactoring from test_composing_methods.py using libCST.

Test class: TestIntroduceExplainingVariable

## Implement Split Temporary Variable refactoring

Implement the Split Temporary Variable refactoring from test_composing_methods.py using libCST.

Test class: TestSplitTemporaryVariable

## Implement Remove Assignments to Parameters refactoring

Implement the Remove Assignments to Parameters refactoring from test_composing_methods.py using libCST.

Test class: TestRemoveAssignmentsToParameters

## Implement Replace Method with Method Object refactoring

Implement the Replace Method with Method Object refactoring from test_composing_methods.py using libCST.

Test class: TestReplaceMethodWithMethodObject

## Implement Substitute Algorithm refactoring

Implement the Substitute Algorithm refactoring from test_composing_methods.py using libCST.

Test class: TestSubstituteAlgorithm

## Implement Decompose Conditional refactoring

Implement the Decompose Conditional refactoring from test_simplifying_conditionals.py using libCST.

Test class: TestDecomposeConditional

## Implement Consolidate Conditional Expression refactoring

Implement the Consolidate Conditional Expression refactoring from test_simplifying_conditionals.py using libCST.

Test class: TestConsolidateConditionalExpression

## Implement Consolidate Duplicate Conditional Fragments refactoring

Implement the Consolidate Duplicate Conditional Fragments refactoring from test_simplifying_conditionals.py using libCST.

Test class: TestConsolidateDuplicateConditionalFragments

## Implement Remove Control Flag refactoring

Implement the Remove Control Flag refactoring from test_simplifying_conditionals.py using libCST.

Test class: TestRemoveControlFlag

## Implement Replace Nested Conditional with Guard Clauses refactoring

Implement the Replace Nested Conditional with Guard Clauses refactoring from test_simplifying_conditionals.py using libCST.

Test class: TestReplaceNestedConditionalWithGuardClauses

## Implement Introduce Assertion refactoring

Implement the Introduce Assertion refactoring from test_simplifying_conditionals.py using libCST.

Test class: TestIntroduceAssertion

## Implement Self Encapsulate Field refactoring

Implement the Self Encapsulate Field refactoring from test_organizing_data.py using libCST.

Test class: TestSelfEncapsulateField

## Implement Encapsulate Field refactoring

Implement the Encapsulate Field refactoring from test_organizing_data.py using libCST.

Test class: TestEncapsulateField

## Implement Encapsulate Collection refactoring

Implement the Encapsulate Collection refactoring from test_organizing_data.py using libCST.

Test class: TestEncapsulateCollection

## Implement Replace Magic Number with Symbolic Constant refactoring

Implement the Replace Magic Number with Symbolic Constant refactoring from test_organizing_data.py using libCST.

Test class: TestReplaceMagicNumberWithSymbolicConstant

## Implement Remove Setting Method refactoring

Implement the Remove Setting Method refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestRemoveSettingMethod

## Implement Hide Method refactoring

Implement the Hide Method refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestHideMethod

## Implement Replace Constructor with Factory Function refactoring

Implement the Replace Constructor with Factory Function refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestReplaceConstructorWithFactoryFunction

## Implement Replace Error Code with Exception refactoring

Implement the Replace Error Code with Exception refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestReplaceErrorCodeWithException

## Implement Replace Exception with Test refactoring

Implement the Replace Exception with Test refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestReplaceExceptionWithTest

## Implement Parameterize Method refactoring

Implement the Parameterize Method refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestParameterizeMethod

## Implement Replace Parameter with Explicit Methods refactoring

Implement the Replace Parameter with Explicit Methods refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestReplaceParameterWithExplicitMethods

## Implement Preserve Whole Object refactoring

Implement the Preserve Whole Object refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestPreserveWholeObject

## Implement Replace Parameter with Method Call refactoring

Implement the Replace Parameter with Method Call refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestReplaceParameterWithMethodCall

## Implement Introduce Parameter Object refactoring

Implement the Introduce Parameter Object refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestIntroduceParameterObject

## Implement Separate Query from Modifier refactoring

Implement the Separate Query from Modifier refactoring from test_simplifying_method_calls.py using libCST.

Test class: TestSeparateQueryFromModifier

# Combined rope + libCST refactorings

Epic for complex refactorings that require both rope (for cross-file operations) and libCST (for structural transformations).

## Implement Move Method refactoring

Implement the Move Method refactoring from test_moving_features.py using both rope and libCST.

Test class: TestMoveMethod

## Implement Move Field refactoring

Implement the Move Field refactoring from test_moving_features.py using both rope and libCST.

Test class: TestMoveField

## Implement Extract Class refactoring

Implement the Extract Class refactoring from test_moving_features.py using both rope and libCST.

Test class: TestExtractClass

## Implement Inline Class refactoring

Implement the Inline Class refactoring from test_moving_features.py using both rope and libCST.

Test class: TestInlineClass

## Implement Hide Delegate refactoring

Implement the Hide Delegate refactoring from test_moving_features.py using both rope and libCST.

Test class: TestHideDelegate

## Implement Remove Middle Man refactoring

Implement the Remove Middle Man refactoring from test_moving_features.py using both rope and libCST.

Test class: TestRemoveMiddleMan

## Implement Introduce Foreign Method refactoring

Implement the Introduce Foreign Method refactoring from test_moving_features.py using both rope and libCST.

Test class: TestIntroduceForeignMethod

## Implement Introduce Local Extension refactoring

Implement the Introduce Local Extension refactoring from test_moving_features.py using both rope and libCST.

Test class: TestIntroduceLocalExtension

## Implement Replace Data Value with Object refactoring

Implement the Replace Data Value with Object refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestReplaceDataValueWithObject

## Implement Change Value to Reference refactoring

Implement the Change Value to Reference refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestChangeValueToReference

## Implement Change Reference to Value refactoring

Implement the Change Reference to Value refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestChangeReferenceToValue

## Implement Replace Array with Object refactoring

Implement the Replace Array with Object refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestReplaceArrayWithObject

## Implement Duplicate Observed Data refactoring

Implement the Duplicate Observed Data refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestDuplicateObservedData

## Implement Change Unidirectional Association to Bidirectional refactoring

Implement the Change Unidirectional Association to Bidirectional refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestChangeUnidirectionalAssociationToBidirectional

## Implement Change Bidirectional Association to Unidirectional refactoring

Implement the Change Bidirectional Association to Unidirectional refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestChangeBidirectionalAssociationToUnidirectional

## Implement Replace Type Code with Class refactoring

Implement the Replace Type Code with Class refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestReplaceTypeCodeWithClass

## Implement Replace Type Code with Subclasses refactoring

Implement the Replace Type Code with Subclasses refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestReplaceTypeCodeWithSubclasses

## Implement Replace Type Code with State/Strategy refactoring

Implement the Replace Type Code with State/Strategy refactoring from test_organizing_data.py using both rope and libCST.

Test class: TestReplaceTypeCodeWithStateStrategy

## Implement Replace Conditional with Polymorphism refactoring

Implement the Replace Conditional with Polymorphism refactoring from test_simplifying_conditionals.py using both rope and libCST.

Test class: TestReplaceConditionalWithPolymorphism

## Implement Introduce Null Object refactoring

Implement the Introduce Null Object refactoring from test_simplifying_conditionals.py using both rope and libCST.

Test class: TestIntroduceNullObject

## Implement Pull Up Field refactoring

Implement the Pull Up Field refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestPullUpField

## Implement Pull Up Method refactoring

Implement the Pull Up Method refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestPullUpMethod

## Implement Pull Up Constructor Body refactoring

Implement the Pull Up Constructor Body refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestPullUpConstructorBody

## Implement Push Down Method refactoring

Implement the Push Down Method refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestPushDownMethod

## Implement Push Down Field refactoring

Implement the Push Down Field refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestPushDownField

## Implement Extract Subclass refactoring

Implement the Extract Subclass refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestExtractSubclass

## Implement Extract Superclass refactoring

Implement the Extract Superclass refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestExtractSuperclass

## Implement Extract Interface refactoring

Implement the Extract Interface refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestExtractInterface

## Implement Collapse Hierarchy refactoring

Implement the Collapse Hierarchy refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestCollapseHierarchy

## Implement Form Template Method refactoring

Implement the Form Template Method refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestFormTemplateMethod

## Implement Replace Inheritance with Delegation refactoring

Implement the Replace Inheritance with Delegation refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestReplaceInheritanceWithDelegation

## Implement Replace Delegation with Inheritance refactoring

Implement the Replace Delegation with Inheritance refactoring from test_dealing_with_generalization.py using both rope and libCST.

Test class: TestReplaceDelegationWithInheritance
