import json
import unittest
from pathlib import Path

from model_selector import ANY_TYPE, DatangModelSelector


FRONTEND_SOURCE = (Path(__file__).resolve().parents[1] / "web" / "model_selector.js").read_text(
    encoding="utf-8"
)


class DatangModelSelectorTests(unittest.TestCase):
    def setUp(self):
        self.node = DatangModelSelector()

    def test_returns_only_the_enabled_model_value(self):
        data = json.dumps(
            [
                {"name": "修复模型 A", "value": "GFPGANv1.4.pth", "enabled": False},
                {"name": "修复模型 B", "value": "codeformer-v0.1.0.pth", "enabled": True},
            ]
        )
        self.assertEqual(self.node.select_model(data), ("codeformer-v0.1.0.pth",))

    def test_invalid_data_fails_to_an_empty_real_value(self):
        self.assertEqual(self.node.select_model("not-json"), ("",))

    def test_first_non_empty_value_is_the_safe_legacy_fallback(self):
        data = json.dumps(
            [
                {"name": "A", "value": "", "enabled": False},
                {"name": "B", "value": "retinaface_resnet50", "enabled": False},
            ]
        )
        self.assertEqual(self.node.select_model(data), ("retinaface_resnet50",))

    def test_output_type_accepts_combo_and_custom_model_types(self):
        self.assertFalse(ANY_TYPE != ["GFPGANv1.4.pth", "codeformer-v0.1.0.pth"])
        self.assertFalse(ANY_TYPE != "REACTOR_MODEL")

    def test_frontend_contract_keeps_dynamic_exclusive_slots_and_real_target_values(self):
        required_contracts = [
            'const MIN_SLOTS = 2;',
            'targetModelOptions(node)',
            '目标下拉需先转换为输入',
            'for (const candidate of items) candidate.enabled = candidate === item;',
            'items.push({ name: nextItemName(items), value, enabled: false });',
            'items.splice(index, 1);',
            'desiredNodeHeight()',
            'dataWidget.value = value;',
            'name: "Datang.ModelSelector"',
        ]
        for contract in required_contracts:
            self.assertIn(contract, FRONTEND_SOURCE)


if __name__ == "__main__":
    unittest.main()
