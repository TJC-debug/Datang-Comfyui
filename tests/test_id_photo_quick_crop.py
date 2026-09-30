import inspect
import unittest
from unittest.mock import patch

import id_photo_quick_crop as module
from portrait_composition import FaceDetection


class QuickIdPhotoCropTests(unittest.TestCase):
    def require_torch(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        return torch

    def test_registration_and_public_contract_match_the_existing_workflow_shape(self):
        self.assertEqual(module.NODE_ID, "DatangQuickIdPhotoCrop")
        self.assertIs(
            module.NODE_CLASS_MAPPINGS[module.NODE_ID],
            module.DatangQuickIdPhotoCrop,
        )
        self.assertEqual(module.NODE_DISPLAY_NAME_MAPPINGS[module.NODE_ID], "大汤证件照快速裁剪")
        self.assertEqual(module.DatangQuickIdPhotoCrop.CATEGORY, "大汤自制节点/图像")
        input_types = module.DatangQuickIdPhotoCrop.INPUT_TYPES()
        self.assertEqual(
            list(input_types["required"]),
            [
                "图像",
                "人脸矫正",
                "预设尺寸",
                "自定义宽",
                "自定义高",
                "单位",
                "DPI",
                "脸部大小",
                "垂直偏移",
                "尺寸限制",
                "填充模式",
            ],
        )
        self.assertEqual(list(input_types["optional"]), ["自定义填充色"])
        self.assertEqual(input_types["optional"]["自定义填充色"][0], "STRING")
        self.assertEqual(
            module.DatangQuickIdPhotoCrop.RETURN_TYPES,
            ("IMAGE", "BOOLEAN", "MASK", "INT"),
        )
        self.assertEqual(
            module.DatangQuickIdPhotoCrop.RETURN_NAMES,
            ("裁剪后图像", "是否扩图", "扩展遮罩", "DPI"),
        )

    def test_size_presets_keep_centimetre_conversion_and_pixel_dpi_overrides(self):
        self.assertEqual(
            module.resolve_output_size("1寸（2.5 x 3.5 厘米）", 0, 0, "厘米", 600),
            (591, 827, 600),
        )
        self.assertEqual(
            module.resolve_output_size("身份证电子（358 x 441 像素 DPI: 350）", 0, 0, "厘米", 600),
            (358, 441, 350),
        )
        self.assertEqual(
            module.resolve_output_size("自定义尺寸", 300, 400, "像素", 720),
            (300, 400, 720),
        )

    def test_invalid_custom_size_is_rejected_instead_of_returning_the_original(self):
        with self.assertRaisesRegex(ValueError, "必须大于 0"):
            module.resolve_output_size("自定义尺寸", 0, 400, "像素", 300)

    def test_detected_face_produces_the_exact_requested_size_and_dpi(self):
        torch = self.require_torch()
        image = torch.linspace(0.0, 1.0, 400 * 300 * 3, dtype=torch.float32).reshape(1, 400, 300, 3)
        detection = FaceDetection(
            bbox=(120.0, 100.0, 180.0, 160.0),
            confidence=0.98,
            landmarks=None,
            detector="test-detector",
            face_count=1,
        )
        with patch.object(module, "detect_face", return_value=detection):
            result, expanded, mask, dpi = module.DatangQuickIdPhotoCrop().crop_id_photo(
                image,
                False,
                "自定义尺寸",
                60,
                80,
                "像素",
                600,
                0.42,
                0.38,
                2000,
                "边框颜色",
            )
        self.assertEqual(tuple(result.shape), (1, 80, 60, 3))
        self.assertEqual(tuple(mask.shape), (1, 80, 60))
        self.assertFalse(expanded)
        self.assertEqual(float(mask.max()), 0.0)
        self.assertEqual(dpi, 600)

    def test_border_fill_is_reported_by_boolean_and_mask(self):
        torch = self.require_torch()
        image = torch.zeros((1, 40, 40, 3), dtype=torch.float32)
        image[:, :, :, :] = torch.tensor([0.2, 0.4, 0.6])
        image[:, 8:32, 8:32, :] = torch.tensor([0.9, 0.1, 0.2])
        detection = FaceDetection(
            bbox=(5.0, 2.0, 25.0, 22.0),
            confidence=0.99,
            landmarks=None,
            detector="test-detector",
            face_count=1,
        )
        with patch.object(module, "detect_face", return_value=detection):
            result, expanded, mask, _ = module.DatangQuickIdPhotoCrop().crop_id_photo(
                image,
                False,
                "自定义尺寸",
                30,
                40,
                "像素",
                300,
                0.42,
                0.38,
                2000,
                "边框颜色",
            )
        self.assertTrue(expanded)
        self.assertEqual(float(mask.max()), 1.0)
        self.assertTrue(torch.allclose(result[0, 0, 0], torch.tensor([0.2, 0.4, 0.6]), atol=0.01))

    def test_custom_fill_accepts_short_hex(self):
        torch = self.require_torch()
        reference = torch.zeros((2, 2, 3), dtype=torch.float32)
        self.assertTrue(
            torch.allclose(
                module._parse_hex_color("#369", reference),
                torch.tensor([0.2, 0.4, 0.6]),
            )
        )

    def test_landmark_rotation_is_active_without_mediapipe(self):
        torch = self.require_torch()
        image = torch.zeros((100, 100, 3), dtype=torch.float32)
        detection = FaceDetection(
            bbox=(30.0, 25.0, 70.0, 75.0),
            confidence=0.99,
            landmarks=(40.0, 60.0, 50.0, 38.0, 62.0, 45.0, 55.0, 60.0, 70.0, 72.0),
            detector="test-detector",
            face_count=1,
        )
        rotated, mask, _, angle = module._rotate_about_eyes(
            image,
            detection,
            True,
            torch.zeros(3, dtype=torch.float32),
        )
        self.assertGreater(angle, 20.0)
        self.assertGreater(rotated.shape[0], 100)
        self.assertEqual(float(mask.max()), 1.0)
        self.assertNotIn("mediapipe", inspect.getsource(module).lower())

    def test_missing_face_raises_a_clear_error_instead_of_silently_returning_input(self):
        torch = self.require_torch()
        image = torch.zeros((1, 100, 80, 3), dtype=torch.float32)
        with patch.object(module, "detect_face", return_value=None):
            with self.assertRaisesRegex(ValueError, "未检测到人脸"):
                module.DatangQuickIdPhotoCrop().crop_id_photo(
                    image,
                    True,
                    "自定义尺寸",
                    60,
                    80,
                    "像素",
                    300,
                    0.42,
                    0.38,
                    2000,
                    "边框颜色",
                )


if __name__ == "__main__":
    unittest.main()
