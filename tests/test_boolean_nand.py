from pathlib import Path
import importlib.util
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "datang_boolean_nand", ROOT / "datang_boolean_nand.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DatangBooleanNandTests(unittest.TestCase):
    def test_node_contract_uses_boolean_inputs_and_output(self):
        module = load_module()
        node = module.DatangBooleanNand
        required = node.INPUT_TYPES()["required"]

        self.assertEqual(required["条件A是否为空"][0], "BOOLEAN")
        self.assertEqual(required["条件B是否为空"][0], "BOOLEAN")
        self.assertTrue(required["条件A是否为空"][1]["default"])
        self.assertTrue(required["条件B是否为空"][1]["default"])
        self.assertEqual(node.RETURN_TYPES, ("BOOLEAN",))
        self.assertEqual(node.RETURN_NAMES, ("布尔值",))

    def test_truth_table_matches_two_empty_state_sources(self):
        node = load_module().DatangBooleanNand()

        self.assertEqual(node.evaluate(True, True), (False,))
        self.assertEqual(node.evaluate(False, True), (True,))
        self.assertEqual(node.evaluate(True, False), (True,))
        self.assertEqual(node.evaluate(False, False), (True,))

    def test_node_registration_is_stable(self):
        module = load_module()

        self.assertIs(
            module.NODE_CLASS_MAPPINGS["DatangBooleanNand"],
            module.DatangBooleanNand,
        )
        self.assertEqual(
            module.NODE_DISPLAY_NAME_MAPPINGS["DatangBooleanNand"],
            "大汤布尔与非",
        )


if __name__ == "__main__":
    unittest.main()
