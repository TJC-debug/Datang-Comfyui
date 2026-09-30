import unittest
from unittest.mock import patch

import id_photo_ratio_crop as module
from portrait_composition import FaceDetection


class IdPhotoRatioCropTests(unittest.TestCase):
    def require_torch(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        return torch

    def test_registration_and_full_parameter_contract(self):
        self.assertEqual(module.NODE_ID, "DatangIdPhotoRatioCrop")
        self.assertIs(module.NODE_CLASS_MAPPINGS[module.NODE_ID], module.DatangIdPhotoRatioCrop)
        self.assertEqual(
            module.NODE_DISPLAY_NAME_MAPPINGS[module.NODE_ID],
            "大汤证件照比例裁剪",
        )
        inputs = module.DatangIdPhotoRatioCrop.INPUT_TYPES()
        self.assertEqual(
            inputs["required"]["比例预设"][0][:2],
            ("保持原图比例（自动识别）", "保持原图尺寸（宽高不变）"),
        )
        self.assertEqual(
            list(inputs["required"]),
            [
                "图像",
                "人脸矫正",
                "比例预设",
                "自定义比例宽",
                "自定义比例高",
                "单位",
                "DPI",
                "脸部大小",
                "垂直偏移",
                "尺寸限制",
                "填充模式",
            ],
        )
        self.assertEqual(list(inputs["optional"]), ["自定义填充色"])
        self.assertEqual(module.DatangIdPhotoRatioCrop.RETURN_TYPES, ("IMAGE", "BOOLEAN", "MASK", "INT"))

    def test_ratio_presets_reuse_existing_values_and_custom_ratio_is_reduced(self):
        self.assertEqual(module.resolve_crop_ratio("1:1 正方形", 3, 4), (1, 1))
        self.assertEqual(module.resolve_crop_ratio("3:4 常用证件照", 1, 1), (3, 4))
        self.assertEqual(module.resolve_crop_ratio("自定义比例", 35, 49), (5, 7))
        with self.assertRaisesRegex(ValueError, "必须大于 0"):
            module.resolve_crop_ratio("自定义比例", 0, 4)

    def test_output_keeps_exact_ratio_without_fixed_size_resampling(self):
        torch = self.require_torch()
        image = torch.linspace(0.0, 1.0, 500 * 400 * 3, dtype=torch.float32).reshape(1, 500, 400, 3)
        detection = FaceDetection(
            bbox=(170.0, 100.0, 230.0, 160.0),
            confidence=0.98,
            landmarks=None,
            detector="test-detector",
            face_count=1,
        )
        with patch.object(module, "detect_face", return_value=detection):
            result, expanded, mask, dpi = module.DatangIdPhotoRatioCrop().crop_id_photo_by_ratio(
                image,
                False,
                "3:4 常用证件照",
                3,
                4,
                "厘米",
                600,
                0.42,
                0.38,
                2000,
                "边框颜色",
            )
        self.assertEqual(tuple(result.shape[1:3]), (192, 144))
        self.assertEqual(tuple(mask.shape[1:3]), (192, 144))
        self.assertEqual(result.shape[2] * 4, result.shape[1] * 3)
        self.assertFalse(expanded)
        self.assertEqual(dpi, 600)

    def test_source_ratio_and_source_size_are_separate_explicit_options(self):
        torch = self.require_torch()
        image = torch.linspace(0.0, 1.0, 500 * 400 * 3, dtype=torch.float32).reshape(1, 500, 400, 3)
        detection = FaceDetection(
            bbox=(170.0, 100.0, 230.0, 160.0),
            confidence=0.98,
            landmarks=None,
            detector="test-detector",
            face_count=1,
        )
        with patch.object(module, "detect_face", return_value=detection):
            ratio_result, _, ratio_mask, _ = module.DatangIdPhotoRatioCrop().crop_id_photo_by_ratio(
                image,
                False,
                module.RATIO_SOURCE,
                3,
                4,
                "厘米",
                600,
                0.42,
                0.38,
                2000,
                "边框颜色",
            )
            size_result, _, size_mask, _ = module.DatangIdPhotoRatioCrop().crop_id_photo_by_ratio(
                image,
                False,
                module.SIZE_SOURCE,
                3,
                4,
                "厘米",
                600,
                0.42,
                0.38,
                2000,
                "边框颜色",
            )

        self.assertEqual(tuple(ratio_result.shape[1:3]), (180, 144))
        self.assertEqual(tuple(ratio_mask.shape[1:3]), (180, 144))
        self.assertEqual(ratio_result.shape[2] * 5, ratio_result.shape[1] * 4)
        self.assertEqual(tuple(size_result.shape), (1, 500, 400, 3))
        self.assertEqual(tuple(size_mask.shape), (1, 500, 400))

    def test_custom_fill_and_all_units_follow_the_original_crop_controls(self):
        torch = self.require_torch()
        image = torch.zeros((1, 80, 80, 3), dtype=torch.float32)
        detection = FaceDetection(
            bbox=(5.0, 2.0, 25.0, 22.0),
            confidence=0.99,
            landmarks=None,
            detector="test-detector",
            face_count=1,
        )
        with patch.object(module, "detect_face", return_value=detection):
            result, expanded, mask, dpi = module.DatangIdPhotoRatioCrop().crop_id_photo_by_ratio(
                image,
                False,
                "1:1 正方形",
                1,
                1,
                "像素",
                350,
                0.42,
                0.38,
                2000,
                "自定义颜色",
                "#369",
            )
        self.assertEqual(result.shape[1], result.shape[2])
        self.assertTrue(expanded)
        self.assertEqual(float(mask.max()), 1.0)
        self.assertEqual(dpi, 350)

    def test_missing_face_is_a_clear_error(self):
        torch = self.require_torch()
        image = torch.zeros((1, 100, 80, 3), dtype=torch.float32)
        with patch.object(module, "detect_face", return_value=None):
            with self.assertRaisesRegex(ValueError, "未检测到人脸"):
                module.DatangIdPhotoRatioCrop().crop_id_photo_by_ratio(
                    image,
                    True,
                    "3:4 常用证件照",
                    3,
                    4,
                    "厘米",
                    300,
                    0.42,
                    0.38,
                    2000,
                    "边框颜色",
                )


if __name__ == "__main__":
    unittest.main()
