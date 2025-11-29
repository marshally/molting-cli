"""Tests for Remove Setting Method refactoring."""


from tests.conftest import RefactoringTestBase


class TestRemoveSettingMethod(RefactoringTestBase):
    """Tests for Remove Setting Method refactoring."""

    fixture_category = "simplifying_method_calls/remove_setting_method"

    def test_simple(self) -> None:
        """Test removing a setter method to make a field immutable.

        This is the basic case: removing a setter method (set_id) that modifies
        a field, making the field immutable. Verifies the setter is removed while
        the field remains readable before testing multiple call sites.
        """
        self.refactor("remove-setting-method", target="Account::_id")

    def test_multiple_calls(self) -> None:
        """Test removing a setter when it's called from multiple locations.

        Unlike test_simple, this verifies that all call sites that invoke the
        setter are identified and updated. Some may need to be removed or
        restructured, making this test critical for completeness.
        """
        self.refactor("remove-setting-method", target="Account::_id")

    def test_with_instance_vars(self) -> None:
        """Test removing a setter from a class with other instance variables.

        Unlike test_simple which focuses on a single field, this tests removing
        a setter from a class that has multiple instance variables. Verifies that
        other instance state remains unaffected by the setter removal.
        """
        self.refactor("remove-setting-method", target="User::_user_id")
