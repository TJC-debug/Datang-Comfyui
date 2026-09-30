from pathlib import Path
import importlib.util
import unittest

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("fast_face_beauty", ROOT / "fast_face_beauty.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def textured_image(batch=1, height=96, width=112, channels=3):
    yy, xx = np.mgrid[:height, :width]
    base = np.zeros((batch, height, width, channels), dtype=np.float32)
    base[..., 0] = (178 + 26 * np.sin(xx / 2.4) + 9 * np.cos(yy / 3.7)) / 255.0
    base[..., 1] = (132 + 18 * np.cos(yy / 2.9)) / 255.0
    base[..., 2] = (108 + 14 * np.sin((xx + yy) / 4.1)) / 255.0
    if channels > 3:
        base[..., 3] = np.linspace(0.2, 1.0, width)[None, None, :]
    return torch.from_numpy(base)


class FastFaceBeautyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_node_contract_requires_skin_mask_and_six_float_sliders(self):
        required = self.module.DatangFastFaceBeauty.INPUT_TYPES()["required"]
        self.assertEqual(
            list(required),
            [
                "图像",
                "皮肤遮罩",
                "美颜强度",
                "磨皮",
                "美白提亮",
                "纹理保留",
                "黑眼圈淡化",
                "瑕疵皱纹淡化",
            ],
        )
        self.assertEqual(required["皮肤遮罩"], ("MASK",))
        for name in list(required)[2:]:
            kind, options = required[name]
            self.assertEqual(kind, "FLOAT")
            self.assertEqual(options["display"], "slider")
            self.assertEqual(
                (options["min"], options["max"], options["step"]),
                (0.0, 100.0, 1.0),
            )

    def test_module_has_no_internal_face_detector_or_model_contract(self):
        self.assertFalse(hasattr(self.module, "detect_faces"))
        self.assertFalse(hasattr(self.module, "MODEL_PATH"))
        self.assertNotIn("FaceDetectorYN", (ROOT / "fast_face_beauty.py").read_text("utf-8"))

    def test_zero_strength_returns_original_tensor_exactly(self):
        image = textured_image()
        mask = torch.ones((1, 96, 112), dtype=torch.float32)
        result = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 0, 100, 100, 0, 100, 100
        )[0]
        self.assertIs(result, image)

    def test_empty_mask_returns_original_tensor_exactly(self):
        image = textured_image()
        mask = torch.zeros((1, 96, 112), dtype=torch.float32)
        result = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 80, 70, 30, 55, 45, 45
        )[0]
        self.assertIs(result, image)

    def test_all_effect_sliders_zero_return_original_tensor_exactly(self):
        image = textured_image()
        mask = torch.ones((1, 96, 112), dtype=torch.float32)
        result = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 100, 0, 0, 70, 0, 0
        )[0]
        self.assertIs(result, image)

    def test_black_area_is_exact_and_white_area_is_processed(self):
        image = textured_image()
        mask = torch.zeros((1, 96, 112), dtype=torch.float32)
        mask[:, :, :56] = 1.0
        result = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 80, 70, 30, 55, 45, 45
        )[0]
        self.assertTrue(torch.equal(result[:, :, 56:], image[:, :, 56:]))
        self.assertGreater(
            torch.count_nonzero(result[:, :, :56] != image[:, :, :56]).item(), 100
        )

    def test_gray_mask_has_less_effect_than_white_mask(self):
        image = textured_image(width=120)
        mask = torch.zeros((1, 96, 120), dtype=torch.float32)
        mask[:, :, :40] = 1.0
        mask[:, :, 40:80] = 0.35
        result = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 100, 0, 45, 70, 0, 0
        )[0]
        white_change = torch.mean(torch.abs(result[:, :, :40] - image[:, :, :40])).item()
        gray_change = torch.mean(torch.abs(result[:, :, 40:80] - image[:, :, 40:80])).item()
        self.assertGreater(white_change, gray_change)
        self.assertTrue(torch.equal(result[:, :, 80:], image[:, :, 80:]))

    def test_texture_retention_reduces_smoothing_change(self):
        image = textured_image()
        mask = torch.ones((1, 96, 112), dtype=torch.float32)
        low_texture = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 100, 100, 0, 0, 0, 0
        )[0]
        high_texture = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 100, 100, 0, 100, 0, 0
        )[0]
        low_delta = torch.mean(torch.abs(low_texture - image)).item()
        high_delta = torch.mean(torch.abs(high_texture - image)).item()
        self.assertGreater(low_delta, high_delta)

    def test_dark_area_slider_lifts_local_shadow_inside_mask(self):
        image = torch.full((1, 96, 112, 3), 0.65, dtype=torch.float32)
        image[:, 44:51, 35:77] = 0.35
        mask = torch.ones((1, 96, 112), dtype=torch.float32)
        result = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 100, 0, 0, 70, 100, 0
        )[0]
        self.assertGreater(
            result[:, 44:51, 35:77].mean().item(),
            image[:, 44:51, 35:77].mean().item(),
        )

    def test_blemish_slider_reduces_small_low_contrast_spot(self):
        image = torch.full((1, 96, 112, 3), 0.50, dtype=torch.float32)
        image[:, 48, 56] = 0.54
        mask = torch.ones((1, 96, 112), dtype=torch.float32)
        result = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 100, 0, 0, 70, 0, 100
        )[0]
        self.assertLess(result[:, 48, 56].mean().item(), image[:, 48, 56].mean().item())

    def test_mask_resizes_and_single_mask_broadcasts_across_batch(self):
        image = textured_image(batch=2, height=80, width=120)
        mask = torch.ones((1, 20, 30), dtype=torch.float32)
        result = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 70, 55, 20, 65, 30, 30
        )[0]
        self.assertEqual(result.shape, image.shape)
        self.assertGreater(torch.count_nonzero(result != image).item(), 100)

    def test_incompatible_mask_batch_is_rejected(self):
        image = textured_image(batch=2)
        mask = torch.ones((3, 96, 112), dtype=torch.float32)
        with self.assertRaisesRegex(ValueError, "批次数量"):
            self.module.DatangFastFaceBeauty().beautify(
                image, mask, 70, 55, 20, 65, 30, 30
            )

    def test_alpha_and_output_geometry_are_preserved(self):
        image = textured_image(channels=4)
        mask = torch.ones((1, 96, 112), dtype=torch.float32)
        result = self.module.DatangFastFaceBeauty().beautify(
            image, mask, 80, 70, 30, 55, 45, 45
        )[0]
        self.assertEqual(result.shape, image.shape)
        self.assertEqual(result.dtype, image.dtype)
        self.assertTrue(torch.equal(result[..., 3], image[..., 3]))


if __name__ == "__main__":
    unittest.main()
