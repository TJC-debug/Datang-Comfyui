import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "stage_result_save", ROOT / "stage_result_save.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StageResultSaveTests(unittest.TestCase):
    def test_node_is_a_real_output_with_stage_widgets(self):
        module = load_module()
        required = module.DatangStageResultSave.INPUT_TYPES()["required"]
        self.assertEqual(required["图片"][0], "IMAGE")
        self.assertTrue(required["图片"][1]["lazy"])
        self.assertEqual(required["阶段序号"][0], "INT")
        self.assertEqual(required["阶段名称"][0], "STRING")
        optional = module.DatangStageResultSave.INPUT_TYPES()["optional"]
        self.assertEqual(list(optional), ["输入DPI", "是否保存"])
        self.assertEqual(optional["是否保存"][0], "BOOLEAN")
        self.assertTrue(optional["是否保存"][1]["forceInput"])
        self.assertEqual(optional["输入DPI"][0], "INT")
        self.assertTrue(optional["输入DPI"][1]["forceInput"])
        self.assertEqual(module.DatangStageResultSave.RETURN_TYPES, ())
        self.assertTrue(module.DatangStageResultSave.OUTPUT_NODE)

    def test_save_switch_is_backward_compatible_and_strict(self):
        module = load_module()
        self.assertTrue(module.normalize_save_enabled(None))
        self.assertTrue(module.normalize_save_enabled(True))
        self.assertFalse(module.normalize_save_enabled(False))
        with self.assertRaisesRegex(ValueError, "布尔值"):
            module.normalize_save_enabled(1)

    def test_disabled_save_does_not_request_or_touch_the_image(self):
        module = load_module()
        node = module.DatangStageResultSave()
        self.assertEqual(node.check_lazy_status(None, 是否保存=False), [])
        self.assertEqual(
            node.save_stage_images(None, 是否保存=False),
            {"ui": {"images": []}},
        )

    def test_enabled_or_unconnected_save_requests_the_lazy_image(self):
        module = load_module()
        node = module.DatangStageResultSave()
        self.assertEqual(node.check_lazy_status(None), ["图片"])
        self.assertEqual(node.check_lazy_status(None, 是否保存=True), ["图片"])
        self.assertEqual(node.check_lazy_status([object()], 是否保存=True), [])

    def test_optional_dpi_is_strict_and_backward_compatible(self):
        module = load_module()
        self.assertIsNone(module.normalize_optional_dpi(None))
        self.assertEqual(module.normalize_optional_dpi(600), 600)
        with self.assertRaisesRegex(ValueError, "72 到 1200"):
            module.normalize_optional_dpi(71)
        with self.assertRaisesRegex(ValueError, "72 到 1200"):
            module.normalize_optional_dpi(300.5)
        with self.assertRaisesRegex(ValueError, "72 到 1200"):
            module.normalize_optional_dpi(True)

    def test_stage_folder_is_versioned_ordered_and_safe(self):
        module = load_module()
        self.assertEqual(
            module.build_stage_folder(2, "裁剪"),
            "datang-stage-result-v1/02_裁剪",
        )
        self.assertEqual(
            module.build_stage_folder(1000, "换底/白色"),
            "datang-stage-result-v1/999_换底-白色",
        )

    def test_empty_or_reserved_stage_names_are_safe(self):
        module = load_module()
        self.assertEqual(module.sanitize_stage_name("  "), "阶段结果")
        self.assertEqual(module.sanitize_stage_name("CON"), "_CON")

    def test_node_writes_a_real_png_and_returns_the_stage_subfolder(self):
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            self.skipTest("当前测试 Python 未安装 numpy 或 Pillow")

        module = load_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            stage_subfolder = "datang-stage-result-v1/02_裁剪"
            stage_dir = output_dir / "datang-stage-result-v1" / "02_裁剪"
            stage_dir.mkdir(parents=True)

            folder_paths = types.ModuleType("folder_paths")
            folder_paths.get_output_directory = lambda: str(output_dir)
            folder_paths.get_save_image_path = lambda *_args: (
                str(stage_dir), "result", 1, stage_subfolder, "unused"
            )
            comfy = types.ModuleType("comfy")
            cli_args = types.ModuleType("comfy.cli_args")
            cli_args.args = types.SimpleNamespace(disable_metadata=True)

            class FakeImage:
                shape = (2, 3, 3)

                def cpu(self):
                    return self

                def numpy(self):
                    return np.ones((2, 3, 3), dtype=np.float32) * 0.5

            previous = {
                name: sys.modules.get(name)
                for name in ("folder_paths", "comfy", "comfy.cli_args")
            }
            sys.modules["folder_paths"] = folder_paths
            sys.modules["comfy"] = comfy
            sys.modules["comfy.cli_args"] = cli_args
            try:
                legacy_result = module.DatangStageResultSave().save_stage_images(
                    [FakeImage()], 2, "裁剪"
                )
                legacy_record = legacy_result["ui"]["images"][0]
                legacy_saved = stage_dir / legacy_record["filename"]
                with Image.open(legacy_saved) as image:
                    self.assertEqual(image.size, (3, 2))
                    self.assertNotIn("dpi", image.info)

                result = module.DatangStageResultSave().save_stage_images(
                    [FakeImage()], 2, "裁剪", 输入DPI=600
                )
            finally:
                for name, value in previous.items():
                    if value is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = value

            image_record = result["ui"]["images"][0]
            self.assertEqual(image_record["subfolder"], stage_subfolder)
            self.assertEqual(image_record["type"], "output")
            saved = stage_dir / image_record["filename"]
            self.assertTrue(saved.is_file())
            with Image.open(saved) as image:
                self.assertEqual(image.size, (3, 2))
                self.assertAlmostEqual(image.info["dpi"][0], 600, places=1)
                self.assertAlmostEqual(image.info["dpi"][1], 600, places=1)


if __name__ == "__main__":
    unittest.main()
