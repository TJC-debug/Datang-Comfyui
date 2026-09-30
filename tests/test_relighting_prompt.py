import unittest

from relighting_prompt import (
    DEFAULT_SELECTIONS,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    PRESET_GROUPS,
    DatangRelightingPrompt,
    compose_relighting_prompt,
)


class DatangRelightingPromptTests(unittest.TestCase):
    def test_node_contract_uses_ten_native_dropdowns_and_one_string_output(self):
        self.assertIs(NODE_CLASS_MAPPINGS["DatangRelightingPrompt"], DatangRelightingPrompt)
        self.assertEqual(NODE_DISPLAY_NAME_MAPPINGS["DatangRelightingPrompt"], "大汤重新打光提示词")
        self.assertEqual(DatangRelightingPrompt.RETURN_TYPES, ("STRING",))
        self.assertEqual(DatangRelightingPrompt.RETURN_NAMES, ("重新打光提示词",))

        inputs = DatangRelightingPrompt.INPUT_TYPES()["required"]
        self.assertEqual(list(inputs), list(PRESET_GROUPS))
        self.assertEqual(len(inputs), 10)
        for group_name, (values, settings) in inputs.items():
            self.assertEqual(values, list(PRESET_GROUPS[group_name]))
            self.assertEqual(settings["default"], DEFAULT_SELECTIONS[group_name])
            self.assertNotIn("multiline", settings)

    def test_categories_cover_requested_and_preventive_relighting_controls(self):
        expected_groups = {
            "主光方向", "人像布光法", "光线质感", "明暗与光比",
            "色温与色彩", "阴影形态", "补光与控光", "高光与材质",
            "场景光源与光效", "风格预设",
        }
        self.assertEqual(set(PRESET_GROUPS), expected_groups)
        self.assertIn("伦勃朗光", PRESET_GROUPS["人像布光法"])
        self.assertIn("百叶窗光影", PRESET_GROUPS["阴影形态"])
        self.assertIn("负补光加深", PRESET_GROUPS["补光与控光"])
        self.assertIn("压制反光", PRESET_GROUPS["高光与材质"])
        self.assertIn("丁达尔光束", PRESET_GROUPS["场景光源与光效"])
        self.assertIn("产品广告", PRESET_GROUPS["风格预设"])

    def test_default_leaves_every_group_unspecified(self):
        prompt = compose_relighting_prompt(DEFAULT_SELECTIONS)
        self.assertEqual(prompt, "")
        self.assertNotIn("重打光程度", PRESET_GROUPS)

    def test_selected_labels_resolve_to_complete_hidden_prompts_in_group_order(self):
        selected = dict(DEFAULT_SELECTIONS)
        selected.update({
            "主光方向": "画面左侧光",
            "人像布光法": "伦勃朗光",
            "光线质感": "柔光",
            "明暗与光比": "低调暗黑",
            "色温与色彩": "冷暖双色",
            "阴影形态": "百叶窗光影",
            "补光与控光": "负补光加深",
            "高光与材质": "皮肤通透高光",
            "场景光源与光效": "丁达尔光束",
            "风格预设": "电影感",
        })
        prompt = compose_relighting_prompt(selected)

        expected_phrases = [
            "key light from camera-left",
            "Rembrandt lighting",
            "soft diffused light",
            "low-key lighting",
            "warm key light and cool fill light",
            "venetian-blind light and shadow stripes",
            "negative fill",
            "luminous skin highlights",
            "Tyndall light rays",
            "cinematic lighting",
        ]
        positions = [prompt.index(phrase) for phrase in expected_phrases]
        self.assertEqual(positions, sorted(positions))
        for visible_label in selected.values():
            self.assertNotIn(visible_label, prompt)

    def test_node_returns_exact_composed_string_without_model_or_file_dependency(self):
        selected = dict(DEFAULT_SELECTIONS)
        selected["主光方向"] = "逆光"
        selected["光线质感"] = "硬光"
        expected = compose_relighting_prompt(selected)
        self.assertEqual(DatangRelightingPrompt().build_prompt(**selected), (expected,))
        self.assertIs(DatangRelightingPrompt.VALIDATE_INPUTS(**selected), True)

    def test_invalid_or_missing_choice_fails_closed_with_named_category(self):
        selected = dict(DEFAULT_SELECTIONS)
        selected["主光方向"] = "已经删除的方向"
        error = DatangRelightingPrompt.VALIDATE_INPUTS(**selected)
        self.assertIn("主光方向", error)
        with self.assertRaisesRegex(ValueError, "主光方向"):
            compose_relighting_prompt(selected)

        missing = dict(DEFAULT_SELECTIONS)
        missing.pop("阴影形态")
        with self.assertRaisesRegex(ValueError, "阴影形态"):
            compose_relighting_prompt(missing)

    def test_each_optional_group_has_a_no_preference_path(self):
        for group_name, options in PRESET_GROUPS.items():
            self.assertEqual(options.get("不指定"), "", group_name)


if __name__ == "__main__":
    unittest.main()
