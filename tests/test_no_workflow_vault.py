from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NoWorkflowVaultContractTests(unittest.TestCase):
    def test_vault_runtime_files_are_not_shipped(self):
        self.assertFalse((ROOT / "web" / "datang_workflow_vault.js").exists())
        self.assertFalse((ROOT / "web" / "datang_workflow_vault_core.js").exists())

    def test_unrelated_datang_features_remain_shipped(self):
        expected_files = (
            "prompt_switchboard.py",
            "datang_group_switch.py",
            "model_selector.py",
            "web/prompt_switchboard_v16.js",
            "web/datang_group_switch.js",
            "web/datang_group_core.js",
            "web/model_selector.js",
            "web/id_photo_layout.js",
            "web/id_photo_layout_core.js",
        )
        for relative_path in expected_files:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_active_readme_marks_vault_as_removed(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("0.4.3 保险箱移除说明", readme)
        self.assertIn("跨工作流复制粘贴", readme)


if __name__ == "__main__":
    unittest.main()
