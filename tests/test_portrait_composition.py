import json
import unittest
from unittest.mock import patch

import portrait_composition as module


class PortraitCompositionTests(unittest.TestCase):
    def require_torch(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        return torch

    def test_datang_registration_keeps_the_original_workflow_node_id(self):
        self.assertEqual(module.NODE_ID, "NabeiPortraitComposition")
        self.assertIs(
            module.NODE_CLASS_MAPPINGS["NabeiPortraitComposition"],
            module.DatangPortraitCrop,
        )
        self.assertEqual(
            module.NODE_DISPLAY_NAME_MAPPINGS["NabeiPortraitComposition"],
            "大汤人物定比裁剪",
        )
        self.assertEqual(module.DatangPortraitCrop.CATEGORY, "大汤自制节点/图像")

    def test_public_contract_preserves_the_standalone_project_inputs_and_outputs(self):
        required = module.DatangPortraitCrop.INPUT_TYPES()["required"]
        self.assertEqual(
            list(required),
            [
                "人物照片",
                "画布比例",
                "人像构图",
                "头部大小微调",
                "人物上下微调",
                "人物左右微调",
            ],
        )
        self.assertEqual(
            module.DatangPortraitCrop.RETURN_NAMES,
            ("裁剪结果", "裁剪预览", "填充区域遮罩", "状态信息"),
        )

    def test_largest_fallback_crop_keeps_each_exact_canvas_ratio(self):
        expected = {
            "1:1 正方形": (800, 800),
            "3:4 常用证件照": (798, 1064),
            "4:5 竖版证件照": (800, 1000),
            "2:3 标准竖版": (800, 1200),
        }
        for preset, size in expected.items():
            crop_width, crop_height, _ = module._aspect_crop_size(800, 1200, preset)
            self.assertEqual((crop_width, crop_height), size)

    def test_crop_box_hits_the_declared_head_targets_without_resampling(self):
        head_box = (300.0, 200.0, 500.0, 400.0)
        crop_box, target, limits = module.compute_crop_box(
            head_box,
            800,
            1200,
            "3:4 常用证件照",
            "标准证件照（头部约46%）",
            1.0,
            0.0,
            0.0,
        )
        crop_x0, crop_y0, crop_x1, crop_y1 = crop_box
        crop_width = crop_x1 - crop_x0
        crop_height = crop_y1 - crop_y0
        transformed_top = head_box[1] - crop_y0
        transformed_height = head_box[3] - head_box[1]
        transformed_center_x = ((head_box[0] + head_box[2]) * 0.5) - crop_x0
        self.assertEqual(crop_width * 4, crop_height * 3)
        self.assertLess(abs(transformed_top / crop_height - target["head_top_ratio"]), 0.003)
        self.assertLess(abs(transformed_height / crop_height - target["head_ratio"]), 0.003)
        self.assertLess(abs(transformed_center_x / crop_width - target["head_center_x_ratio"]), 0.003)
        self.assertFalse(any(limits.values()))

    def test_crop_returns_an_exact_source_slice_and_zero_blank_mask(self):
        torch = self.require_torch()
        image = torch.arange(12 * 16 * 3, dtype=torch.float32).reshape(12, 16, 3)
        result, mask = module.crop_image(image, (3, 2, 11, 10))
        self.assertTrue(torch.equal(result, image[2:10, 3:11, :3]))
        self.assertEqual(tuple(mask.shape), (8, 8))
        self.assertEqual(float(mask.max()), 0.0)

    def test_detected_face_produces_an_unscaled_source_crop_and_receipt(self):
        torch = self.require_torch()
        image = torch.arange(800 * 600 * 3, dtype=torch.float32).reshape(1, 800, 600, 3)
        image = image / float(image.numel() - 1)
        detection = module.FaceDetection(
            bbox=(250.0, 200.0, 350.0, 320.0),
            confidence=0.98,
            landmarks=None,
            detector="test-detector",
            face_count=1,
        )
        with patch.object(module, "detect_face", return_value=detection):
            result, preview, mask, status_json = module.DatangPortraitCrop().compose(
                image,
                "3:4 常用证件照",
                "标准证件照（头部约46%）",
                1.0,
                0.0,
                0.0,
            )
        status = json.loads(status_json)
        crop_x0, crop_y0, crop_x1, crop_y1 = status["crop_box"]
        expected = image[:, crop_y0:crop_y1, crop_x0:crop_x1, :3]
        self.assertTrue(torch.equal(result, expected))
        self.assertEqual(tuple(preview.shape), tuple(result.shape))
        self.assertEqual(tuple(mask.shape), tuple(result.shape[:3]))
        self.assertEqual(float(mask.max()), 0.0)
        self.assertTrue(status["success"])
        self.assertFalse(status["needs_review"])
        self.assertFalse(status["resampled"])
        self.assertEqual(status["schema"], "datang.portrait_crop.v1")
        self.assertEqual(status["detector"], "test-detector")

    def test_missing_face_returns_reviewable_fallback_instead_of_fake_success(self):
        torch = self.require_torch()
        image = torch.arange(120 * 80 * 3, dtype=torch.float32).reshape(1, 120, 80, 3)
        image = image / float(image.numel() - 1)
        with patch.object(module, "detect_face", return_value=None):
            result, _, mask, status_json = module.DatangPortraitCrop().compose(
                image,
                "3:4 常用证件照",
                "标准证件照（头部约46%）",
                1.0,
                0.0,
                0.0,
            )
        self.assertEqual(tuple(result.shape), (1, 104, 78, 3))
        self.assertTrue(torch.equal(result, image[:, 8:112, 1:79, :3]))
        self.assertEqual(tuple(mask.shape), (1, 104, 78))
        self.assertEqual(float(mask.max()), 0.0)
        status = json.loads(status_json)
        self.assertFalse(status["success"])
        self.assertTrue(status["needs_review"])
        self.assertIn("未检测到人脸", status["message"])
        self.assertFalse(status["resampled"])

    def test_outside_crop_uses_border_color_without_resampling_or_stretching(self):
        torch = self.require_torch()
        image = torch.arange(120 * 80 * 3, dtype=torch.float32).reshape(1, 120, 80, 3)
        image = image / float(image.numel() - 1)
        detection = module.FaceDetection(
            bbox=(5.0, 2.0, 75.0, 95.0),
            confidence=0.99,
            landmarks=None,
            detector="test-detector",
            face_count=1,
        )
        with patch.object(module, "detect_face", return_value=detection):
            result, _, mask, status_json = module.DatangPortraitCrop().compose(
                image,
                "3:4 常用证件照",
                "半身证件照（头部约26%）",
                1.0,
                0.0,
                0.0,
            )
        status = json.loads(status_json)
        crop_x0, crop_y0, crop_x1, crop_y1 = status["crop_box"]
        self.assertEqual((crop_x1 - crop_x0) * 4, (crop_y1 - crop_y0) * 3)
        destination_x0 = max(0, -crop_x0)
        destination_y0 = max(0, -crop_y0)
        copied = result[
            :,
            destination_y0 : destination_y0 + image.shape[1],
            destination_x0 : destination_x0 + image.shape[2],
            :,
        ]
        self.assertTrue(torch.equal(copied, image))
        self.assertEqual(float(mask[:, destination_y0 : destination_y0 + 120, destination_x0 : destination_x0 + 80].max()), 0.0)
        self.assertEqual(float(mask.max()), 1.0)
        self.assertTrue(status["success"])
        self.assertTrue(status["needs_review"])
        self.assertTrue(status["limits"]["fill_required"])
        self.assertTrue(status["limits"]["safety_limited"])
        self.assertGreater(status["filled_pixels"], 0)
        fill_color = torch.tensor(status["fill_color"], dtype=result.dtype)
        self.assertTrue(torch.allclose(result[0, 0, 0], fill_color, atol=1e-6))

    def test_mtcnn_failure_falls_back_to_existing_opencv_detection(self):
        torch = self.require_torch()
        fallback = module.FaceDetection(
            bbox=(1.0, 2.0, 30.0, 40.0),
            confidence=1.0,
            landmarks=None,
            detector="opencv-haar",
            face_count=1,
        )
        with (
            patch.object(module, "_detect_with_mtcnn", side_effect=RuntimeError("missing")),
            patch.object(module, "_detect_with_opencv", return_value=fallback) as opencv,
        ):
            image = torch.zeros((4, 4, 3), dtype=torch.float32)
            self.assertIs(module.detect_face(image), fallback)
        opencv.assert_called_once()


if __name__ == "__main__":
    unittest.main()
