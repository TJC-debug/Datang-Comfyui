import unittest

from datang_lazy_switch import DatangBooleanConstant, DatangLazyIfElse


class DatangLazySwitchTests(unittest.TestCase):
    def test_branch_inputs_are_explicitly_lazy(self):
        required = DatangLazyIfElse.INPUT_TYPES()["required"]

        self.assertTrue(required["on_true"][1]["lazy"])
        self.assertTrue(required["on_false"][1]["lazy"])

    def test_only_selected_missing_branch_is_requested(self):
        node = DatangLazyIfElse()

        self.assertEqual(node.check_lazy_status(True, None, "off"), ["on_true"])
        self.assertEqual(node.check_lazy_status(False, "on", None), ["on_false"])
        self.assertEqual(node.check_lazy_status(True, "on", None), [])
        self.assertEqual(node.check_lazy_status(False, None, "off"), [])

    def test_selected_value_and_boolean_constant_are_preserved(self):
        branch = DatangLazyIfElse()
        boolean = DatangBooleanConstant()

        self.assertEqual(branch.select(True, "on", "off"), ("on",))
        self.assertEqual(branch.select(False, "on", "off"), ("off",))
        self.assertEqual(boolean.emit(1), (True,))


if __name__ == "__main__":
    unittest.main()
