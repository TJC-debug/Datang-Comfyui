from pathlib import Path
import importlib.util
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "datang_group_presence", ROOT / "datang_group_presence.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DatangGroupPresenceTests(unittest.TestCase):
    def test_node_contract_exposes_marker_and_direct_boolean_states(self):
        module = load_module()
        node = module.DatangGroupPresenceMarker
        self.assertEqual(node.INPUT_TYPES()["required"]["组已启用"][0], "BOOLEAN")
        self.assertEqual(node.RETURN_TYPES, ("STRING", "BOOLEAN", "BOOLEAN"))
        self.assertEqual(node.RETURN_NAMES, ("状态标记", "是否为空", "组已启用"))

    def test_enabled_group_outputs_a_non_empty_marker(self):
        module = load_module()
        self.assertEqual(
            module.DatangGroupPresenceMarker().evaluate(True),
            ("enabled", False, True),
        )

    def test_ignored_or_unbound_group_outputs_none(self):
        module = load_module()
        self.assertEqual(
            module.DatangGroupPresenceMarker().evaluate(False),
            (None, True, False),
        )


if __name__ == "__main__":
    unittest.main()
