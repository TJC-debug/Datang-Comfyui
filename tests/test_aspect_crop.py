import unittest
from unittest.mock import patch

import aspect_crop as module
import image_size_restore as restore_module
from portrait_composition import FaceDetection


class AspectCropTests(unittest.TestCase):
    def require_torch(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        return torch

    def test_registration_and_shared_ratio_contract(self):
        self.assertEqual(module.NODE_ID, "DatangAspectCrop")
        self.assertIs(module.NODE_CLASS_MAPPINGS[module.NODE_ID], module.DatangAspectCrop)
        self.assertEqual(module.NODE_DISPLAY_NAME_MAPPINGS[module.NODE_ID], "大汤图像比例裁剪")
        inputs = module.DatangAspectCrop.INPUT_TYPES()["required"]
        self.assertEqual(
            list(inputs),
            ["图像", "启用人脸识别", "比例预设", "自定义比例宽", "自定义比例高"],
        )
        optional = module.DatangAspectCrop.INPUT_TYPES()["optional"]
        self.assertEqual(
            list(optional),
            ["脸部大小", "垂直偏移", "输出尺寸方式", "目标像素"],
        )
        self.assertFalse(inputs["启用人脸识别"][1]["default"])
        self.assertEqual(inputs["比例预设"][1]["default"], module.RATIO_SOURCE)
        self.assertEqual(
            inputs["比例预设"][0],
            (
                module.RATIO_SOURCE,
                "1:1 正方形",
                "3:4 常用证件照",
                "4:5 竖版证件照",
                "2:3 标准竖版",
            ),
        )
        self.assertNotIn(module.RATIO_CUSTOM, inputs["比例预设"][0])
        self.assertNotIn(module.RATIO_SQUARE_LEGACY, inputs["比例预设"][0])
        self.assertEqual(optional["脸部大小"][1]["default"], 0.42)
        self.assertEqual(optional["垂直偏移"][1]["default"], 0.38)
        self.assertEqual(optional["输出尺寸方式"][0], module.OUTPUT_SIZE_OPTIONS)
        self.assertEqual(optional["输出尺寸方式"][1]["default"], module.OUTPUT_SIZE_KEEP)
        self.assertEqual(optional["目标像素"][1]["default"], 1536)
        self.assertEqual(module.DatangAspectCrop.RETURN_TYPES, ("IMAGE",))

    def test_source_ratio_always_bypasses_image_and_face_detection(self):
        torch = self.require_torch()
        image = torch.rand((2, 13, 17, 3), dtype=torch.float32)
        with patch.object(module, "detect_face_layout", side_effect=AssertionError("不应检测人脸")):
            result = module.DatangAspectCrop().crop_aspect(
                image, False, module.RATIO_SOURCE, 3, 4
            )[0]
        self.assertIs(result, image)

        with patch.object(module, "detect_face_layout", side_effect=AssertionError("不应检测人脸")):
            legacy_result = module.DatangAspectCrop().crop_aspect(
                image, False, module.RATIO_SOURCE_LEGACY, 3, 4
            )[0]
        self.assertIs(legacy_result, image)

        with patch.object(module, "detect_face_layout", side_effect=AssertionError("不应检测人脸")):
            face_mode_result = module.DatangAspectCrop().crop_aspect(
                image,
                True,
                module.RATIO_SOURCE,
                3,
                4,
                输出尺寸方式=module.OUTPUT_SIZE_LONGEST,
                目标像素=1536,
            )[0]
        self.assertIs(face_mode_result, image)

    def test_source_ratio_keeps_800_by_1067_pixels_and_final_restore_is_exact(self):
        torch = self.require_torch()
        image = torch.rand((1, 1067, 800, 3), dtype=torch.float32)
        reference = module.DatangAspectCrop().crop_aspect(
            image,
            False,
            module.RATIO_SOURCE,
            3,
            4,
            输出尺寸方式=module.OUTPUT_SIZE_LONGEST,
            目标像素=1536,
        )[0]
        self.assertIs(reference, image)
        self.assertEqual(tuple(reference.shape), (1, 1067, 800, 3))

        aligned_processing_result = reference[:, :1064, :, :]
        restored = restore_module.DatangImageSizeRestore().restore_size(
            aligned_processing_result,
            reference,
            restore_module.MODE_STRETCH,
        )[0]
        self.assertEqual(tuple(restored.shape), (1, 1067, 800, 3))

    def test_actual_crop_can_resize_by_selected_edge_without_changing_ratio(self):
        torch = self.require_torch()
        image = torch.rand((1, 40, 33, 3), dtype=torch.float32)
        cases = (
            (module.OUTPUT_SIZE_KEEP, 999, (1, 40, 30, 3)),
            (module.OUTPUT_SIZE_LONGEST, 100, (1, 100, 75, 3)),
            (module.OUTPUT_SIZE_SHORTEST, 90, (1, 120, 90, 3)),
            (module.OUTPUT_SIZE_WIDTH, 81, (1, 108, 81, 3)),
            (module.OUTPUT_SIZE_HEIGHT, 88, (1, 88, 66, 3)),
        )
        for size_mode, target_pixels, expected_shape in cases:
            with self.subTest(size_mode=size_mode):
                result = module.DatangAspectCrop().crop_aspect(
                    image,
                    False,
                    "3:4 常用证件照",
                    3,
                    4,
                    输出尺寸方式=size_mode,
                    目标像素=target_pixels,
                )[0]
                self.assertEqual(tuple(result.shape), expected_shape)

    def test_user_case_outputs_exact_three_by_four_1536_canvas(self):
        torch = self.require_torch()
        image = torch.zeros((1, 1067, 800, 3), dtype=torch.float32)
        result = module.DatangAspectCrop().crop_aspect(
            image,
            False,
            "3:4 常用证件照",
            3,
            4,
            输出尺寸方式=module.OUTPUT_SIZE_LONGEST,
            目标像素=1536,
        )[0]
        self.assertEqual(tuple(result.shape), (1, 1536, 1152, 3))

    def test_output_size_validation_only_applies_to_actual_crop_ratios(self):
        torch = self.require_torch()
        image = torch.zeros((1, 40, 33, 3), dtype=torch.float32)
        with self.assertRaisesRegex(ValueError, "不支持的输出尺寸方式"):
            module.DatangAspectCrop().crop_aspect(
                image,
                False,
                "3:4 常用证件照",
                3,
                4,
                输出尺寸方式="未知方式",
            )
        with self.assertRaisesRegex(ValueError, "目标像素必须大于 0"):
            module.DatangAspectCrop().crop_aspect(
                image,
                False,
                "3:4 常用证件照",
                3,
                4,
                输出尺寸方式=module.OUTPUT_SIZE_LONGEST,
                目标像素=0,
            )

    def test_center_mode_exact_ratio_bypasses_image_and_face_detection(self):
        torch = self.require_torch()

        exact_ratio_image = torch.rand((2, 12, 9, 3), dtype=torch.float32)
        with patch.object(module, "detect_face_layout", side_effect=AssertionError("不应检测人脸")):
            exact_ratio_result = module.DatangAspectCrop().crop_aspect(
                exact_ratio_image, False, "3:4 常用证件照", 3, 4
            )[0]
        self.assertIs(exact_ratio_result, exact_ratio_image)

    def test_disabled_face_mode_is_an_exact_center_crop_and_never_detects(self):
        torch = self.require_torch()
        image = torch.arange(2 * 500 * 401 * 3, dtype=torch.float32).reshape(2, 500, 401, 3)
        with patch.object(module, "detect_face_layout", side_effect=AssertionError("不应检测人脸")):
            result = module.DatangAspectCrop().crop_aspect(
                image, False, "3:4 常用证件照", 1, 1
            )[0]
        self.assertEqual(tuple(result.shape), (2, 500, 375, 3))
        self.assertTrue(torch.equal(result, image[:, :, 13:388, :]))
        self.assertEqual(result.shape[2] * 4, result.shape[1] * 3)

    def test_enabled_face_mode_uses_face_size_and_eye_position_for_the_crop_window(self):
        torch = self.require_torch()
        image = torch.arange(10 * 20 * 3, dtype=torch.float32).reshape(1, 10, 20, 3)
        detection = FaceDetection(
            bbox=(8.0, 2.0, 12.0, 6.0),
            confidence=0.99,
            landmarks=None,
            detector="test-detector",
            face_count=1,
        )
        with patch.object(module, "detect_face", return_value=detection):
            result = module.DatangAspectCrop().crop_aspect(
                image, True, module.RATIO_SQUARE, 1, 1, 0.5, 0.5
            )[0]
        self.assertEqual(tuple(result.shape), (1, 8, 8, 3))
        self.assertTrue(torch.equal(result, image[:, 0:8, 6:14, :]))

    def test_face_size_controls_zoom_and_vertical_offset_controls_headroom(self):
        torch = self.require_torch()
        image = torch.arange(20 * 20 * 3, dtype=torch.float32).reshape(1, 20, 20, 3)
        detection = FaceDetection((8.0, 8.0, 12.0, 12.0), 0.99, None, "test", 1)
        with patch.object(module, "detect_face", return_value=detection):
            loose = module.DatangAspectCrop().crop_aspect(
                image, True, "1:1 正方形", 1, 1, 0.4, 0.3
            )[0]
            tight = module.DatangAspectCrop().crop_aspect(
                image, True, "1:1 正方形", 1, 1, 0.8, 0.3
            )[0]
            more_headroom = module.DatangAspectCrop().crop_aspect(
                image, True, "1:1 正方形", 1, 1, 0.4, 0.5
            )[0]
        self.assertEqual(tuple(loose.shape), (1, 10, 10, 3))
        self.assertEqual(tuple(tight.shape), (1, 5, 5, 3))
        self.assertTrue(torch.equal(loose, image[:, 7:17, 5:15, :]))
        self.assertTrue(torch.equal(more_headroom, image[:, 5:15, 5:15, :]))

    def test_face_mode_detects_each_batch_item_and_keeps_common_dimensions(self):
        torch = self.require_torch()
        image = torch.arange(2 * 6 * 10 * 3, dtype=torch.float32).reshape(2, 6, 10, 3)
        detections = [
            FaceDetection((0.0, 1.0, 2.0, 3.0), 0.99, None, "test", 1),
            FaceDetection((8.0, 1.0, 10.0, 3.0), 0.99, None, "test", 1),
        ]
        with patch.object(module, "detect_face", side_effect=detections):
            result = module.DatangAspectCrop().crop_aspect(
                image, True, "1:1 正方形", 1, 1, 0.5, 0.38
            )[0]
        self.assertEqual(tuple(result.shape), (2, 4, 4, 3))
        self.assertTrue(torch.equal(result[0:1], image[0:1, 0:4, 0:4, :]))
        self.assertTrue(torch.equal(result[1:2], image[1:2, 0:4, 6:10, :]))

    def test_face_mode_without_a_detected_face_is_a_clear_error(self):
        torch = self.require_torch()
        image = torch.zeros((1, 10, 10, 3), dtype=torch.float32)
        with patch.object(module, "detect_face", return_value=None):
            with self.assertRaisesRegex(ValueError, "关闭.*按人脸构图"):
                module.DatangAspectCrop().crop_aspect(
                    image, True, "3:4 常用证件照", 3, 4, 0.42, 0.38
                )

    def test_face_mode_rejects_mixed_output_sizes_without_resampling_or_padding(self):
        torch = self.require_torch()
        image = torch.zeros((2, 20, 20, 3), dtype=torch.float32)
        detections = [
            FaceDetection((8.0, 8.0, 12.0, 12.0), 0.99, None, "test", 1),
            FaceDetection((6.0, 6.0, 14.0, 14.0), 0.99, None, "test", 1),
        ]
        with patch.object(module, "detect_face", side_effect=detections):
            with self.assertRaisesRegex(ValueError, "请逐张处理"):
                module.DatangAspectCrop().crop_aspect(
                    image, True, "1:1 正方形", 1, 1, 0.5, 0.38
                )

    def test_face_mode_can_normalize_mixed_crops_when_output_scaling_is_enabled(self):
        torch = self.require_torch()
        image = torch.zeros((2, 20, 20, 3), dtype=torch.float32)
        detections = [
            FaceDetection((8.0, 8.0, 12.0, 12.0), 0.99, None, "test", 1),
            FaceDetection((6.0, 6.0, 14.0, 14.0), 0.99, None, "test", 1),
        ]
        with patch.object(module, "detect_face", side_effect=detections):
            result = module.DatangAspectCrop().crop_aspect(
                image,
                True,
                "1:1 正方形",
                1,
                1,
                0.5,
                0.38,
                module.OUTPUT_SIZE_LONGEST,
                12,
            )[0]
        self.assertEqual(tuple(result.shape), (2, 12, 12, 3))

    def test_custom_ratio_is_reduced_and_impossible_exact_ratio_is_clear(self):
        self.assertEqual(module.resolve_crop_ratio(module.RATIO_CUSTOM, 35, 49), (5, 7))
        self.assertEqual(module.resolve_crop_ratio(module.RATIO_SQUARE, 3, 4), (1, 1))
        self.assertEqual(module.resolve_crop_ratio(module.RATIO_SQUARE_LEGACY, 3, 4), (1, 1))
        self.assertIsNone(module.resolve_crop_ratio(module.RATIO_SOURCE_LEGACY, 3, 4))
        with self.assertRaisesRegex(ValueError, "必须大于 0"):
            module.resolve_crop_ratio(module.RATIO_CUSTOM, 0, 4)

        torch = self.require_torch()
        image = torch.zeros((1, 10, 10, 3), dtype=torch.float32)
        with self.assertRaisesRegex(ValueError, "无法按 11:13"):
            module.crop_without_resampling(image, 11, 13)


if __name__ == "__main__":
    unittest.main()
