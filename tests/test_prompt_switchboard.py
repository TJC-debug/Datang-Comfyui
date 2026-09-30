import json
import unittest

from prompt_switchboard import PromptSwitchboard


class PromptSwitchboardTests(unittest.TestCase):
    def setUp(self):
        self.node = PromptSwitchboard()

    def test_combines_only_enabled_non_empty_items(self):
        data = json.dumps(
            [
                {"text": "masterpiece", "enabled": True},
                {"text": "low quality", "enabled": False},
                {"text": " soft light ", "enabled": True},
                {"text": "   ", "enabled": True},
            ]
        )
        self.assertEqual(
            self.node.combine(data, ", "),
            ("masterpiece, soft light",),
        )

    def test_all_disabled_returns_empty_string(self):
        data = json.dumps([{"text": "portrait", "enabled": False}])
        self.assertEqual(self.node.combine(data, ", "), ("",))

    def test_custom_separator_is_preserved(self):
        data = json.dumps(
            [
                {"text": "first", "enabled": True},
                {"text": "second", "enabled": True},
            ]
        )
        self.assertEqual(self.node.combine(data, "\n"), ("first\nsecond",))

    def test_invalid_json_fails_safely(self):
        self.assertEqual(self.node.combine("not-json", ", "), ("",))

    def test_legacy_string_list_is_supported(self):
        data = json.dumps(["first", "second"])
        self.assertEqual(self.node.combine(data, " | "), ("first | second",))

    def test_single_select_mode_outputs_only_first_enabled_item(self):
        data = json.dumps(
            [
                {"text": "first", "enabled": True, "_selection_mode": "单选"},
                {"text": "second", "enabled": True},
            ]
        )
        self.assertEqual(self.node.combine(data, ", "), ("first",))

    def test_editable_names_do_not_change_output(self):
        data = json.dumps(
            [
                {"name": "保持背景", "text": "keep background", "enabled": True},
                {"name": "自然手部", "text": "natural hands", "enabled": True},
            ]
        )
        self.assertEqual(
            self.node.combine(data, ", "),
            ("keep background, natural hands",),
        )


if __name__ == "__main__":
    unittest.main()
