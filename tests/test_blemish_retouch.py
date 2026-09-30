from pathlib import Path
from unittest import mock
import importlib.util
import unittest

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "blemish_retouch", ROOT / "blemish_retouch.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BlemishRetouchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_node_contract_requires_external_mask_and_returns_preview_mask(self):
        required = self.module.DatangBlemishRetouch.INPUT_TYPES()["required"]
        self.assertEqual(
            list(required),
            [
                "图像",
                "皮肤遮罩",
                "修复强度",
                "检测灵敏度",
                "最大瑕疵尺寸",
                "深色斑点修复",
                "红印修复",
                "五官边缘保护",
                "边缘羽化",
            ],
        )
        self.assertEqual(required["皮肤遮罩"], ("MASK",))
        self.assertEqual(self.module.DatangBlemishRetouch.RETURN_TYPES, ("IMAGE", "MASK"))

    def test_detector_only_accepts_small_marks_inside_skin_mask(self):
        image = np.full((128, 128, 3), (184, 145, 126), dtype=np.uint8)
        image[59:65, 61:67] = (95, 66, 58)
        image[20:26, 20:26] = (90, 50, 50)
        mask = np.zeros((128, 128), dtype=np.float32)
        mask[32:106, 32:106] = 1.0
        detected = self.module.detect_blemishes(image, mask, 70, 28, 100, 100)
        self.assertGreater(detected[62, 64], 0)
        self.assertEqual(detected[23, 23], 0)

    def test_detector_rejects_region_larger_than_maximum_size(self):
        image = np.full((128, 128, 3), (184, 145, 126), dtype=np.uint8)
        image[45:90, 43:91] = (95, 66, 58)
        mask = np.ones((128, 128), dtype=np.float32)
        detected = self.module.detect_blemishes(image, mask, 80, 20, 100, 100)
        self.assertEqual(np.count_nonzero(detected), 0)

    def test_empty_skin_mask_returns_original_without_loading_model(self):
        image = torch.full((1, 96, 112, 3), 0.55, dtype=torch.float32)
        mask = torch.zeros((1, 96, 112), dtype=torch.float32)
        with mock.patch.object(self.module, "_run_lama") as run_lama:
            result, detected = self.module.DatangBlemishRetouch().retouch(
                image, mask, 85, 70, 32, 100, 100, 78, 5
            )
        self.assertIs(result, image)
        self.assertEqual(torch.count_nonzero(detected).item(), 0)
        run_lama.assert_not_called()

    def test_repair_changes_only_detected_skin_area_and_preserves_alpha(self):
        image = torch.full((1, 96, 112, 4), 0.65, dtype=torch.float32)
        image[:, 45:51, 53:59, :3] = 0.23
        image[..., 3] = torch.linspace(0.1, 1.0, 112)[None, None, :]
        mask = torch.zeros((1, 96, 112), dtype=torch.float32)
        mask[:, 20:80, 22:90] = 1.0

        def fake_lama(images, repair_masks):
            return torch.full_like(images[..., :3], 0.72)

        with mock.patch.object(self.module, "_run_lama", side_effect=fake_lama):
            result, detected = self.module.DatangBlemishRetouch().retouch(
                image, mask, 100, 80, 26, 100, 100, 78, 0
            )
        self.assertGreater(detected[:, 45:51, 53:59].sum().item(), 0)
        self.assertTrue(torch.equal(result[:, :15], image[:, :15]))
        self.assertTrue(torch.equal(result[..., 3], image[..., 3]))
        self.assertGreater(result[:, 45:51, 53:59, :3].mean(), image[:, 45:51, 53:59, :3].mean())

    def test_zero_strength_returns_original_but_still_outputs_detection_preview(self):
        image = torch.full((1, 96, 112, 3), 0.65, dtype=torch.float32)
        image[:, 45:51, 53:59] = 0.23
        mask = torch.ones((1, 96, 112), dtype=torch.float32)
        with mock.patch.object(self.module, "_run_lama") as run_lama:
            result, detected = self.module.DatangBlemishRetouch().retouch(
                image, mask, 0, 80, 26, 100, 100, 78, 4
            )
        self.assertIs(result, image)
        self.assertGreater(torch.count_nonzero(detected).item(), 0)
        run_lama.assert_not_called()

    def test_model_lookup_does_not_download_and_has_actionable_error(self):
        with mock.patch("pathlib.Path.is_file", return_value=False):
            with self.assertRaisesRegex(FileNotFoundError, "不会自动联网下载"):
                self.module._find_lama_model()

    def test_structure_protection_keeps_eye_mask_margin_but_detects_far_blemish(self):
        image = np.full((160, 160, 3), (184, 145, 126), dtype=np.uint8)
        image[83:89, 58:64] = (80, 52, 48)
        image[116:122, 105:111] = (86, 58, 50)
        mask = np.ones((160, 160), dtype=np.float32)
        mask[62:82, 42:82] = 0.0
        protected = self.module.detect_blemishes(image, mask, 82, 30, 100, 100, 85)
        unprotected = self.module.detect_blemishes(image, mask, 82, 30, 100, 100, 0)
        self.assertEqual(protected[86, 61], 0)
        self.assertGreater(unprotected[86, 61], 0)
        self.assertGreater(protected[119, 108], 0)


if __name__ == "__main__":
    unittest.main()
