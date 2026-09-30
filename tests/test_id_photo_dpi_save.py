import importlib.util
import os
import sys
import tempfile
import types
import unittest


MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "id_photo_dpi_save.py")


class IdPhotoDpiSaveTests(unittest.TestCase):
    def test_node_is_a_real_output_with_dpi_input(self):
        spec = importlib.util.spec_from_file_location("id_photo_dpi_save_contract", MODULE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        required = module.DatangIdPhotoDpiSave.INPUT_TYPES()["required"]
        self.assertEqual(required["图片"], ("IMAGE",))
        self.assertEqual(required["DPI"][1]["default"], 300)
        self.assertEqual(required["DPI"][1]["min"], 72)
        self.assertTrue(module.DatangIdPhotoDpiSave.OUTPUT_NODE)
        self.assertEqual(module.DatangIdPhotoDpiSave.RETURN_TYPES, ())

    def test_saved_png_contains_requested_dpi_metadata(self):
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            self.skipTest("当前测试 Python 缺少 NumPy 或 Pillow")

        class FakeImage:
            def __init__(self, pixels):
                self._pixels = pixels
                self.shape = pixels.shape

            def cpu(self):
                return self

            def numpy(self):
                return self._pixels

        with tempfile.TemporaryDirectory() as output_dir:
            folder_paths = types.ModuleType("folder_paths")
            folder_paths.get_output_directory = lambda: output_dir
            folder_paths.get_save_image_path = lambda prefix, root, width, height: (
                root, "id_%batch_num%", 1, "", prefix
            )
            comfy = types.ModuleType("comfy")
            cli_args = types.ModuleType("comfy.cli_args")
            cli_args.args = types.SimpleNamespace(disable_metadata=False)
            previous = {name: sys.modules.get(name) for name in ("folder_paths", "comfy", "comfy.cli_args")}
            sys.modules["folder_paths"] = folder_paths
            sys.modules["comfy"] = comfy
            sys.modules["comfy.cli_args"] = cli_args
            try:
                spec = importlib.util.spec_from_file_location("id_photo_dpi_save_runtime", MODULE_PATH)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                image = [FakeImage(np.zeros((4, 5, 3), dtype=np.float32))]
                result = module.DatangIdPhotoDpiSave().save_images(image, DPI=600)
                filename = result["ui"]["images"][0]["filename"]
                with Image.open(os.path.join(output_dir, filename)) as saved:
                    self.assertAlmostEqual(saved.info["dpi"][0], 600, delta=1)
                    self.assertAlmostEqual(saved.info["dpi"][1], 600, delta=1)
            finally:
                for name, value in previous.items():
                    if value is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = value


if __name__ == "__main__":
    unittest.main()
