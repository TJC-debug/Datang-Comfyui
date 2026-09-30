import inspect
import unittest

import photo_print_crop as module


class PhotoPrintCropTests(unittest.TestCase):
    def require_torch(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        return torch

    def run_custom(
        self,
        image,
        method="居中裁剪",
        focus="居中",
        width=4,
        height=4,
        direction="跟随原图",
    ):
        return module.DatangPhotoPrintCrop().crop_photo(
            image,
            "自定义尺寸",
            direction,
            method,
            focus,
            width,
            height,
            "像素",
            300,
        )

    def test_registration_and_append_only_output_contract(self):
        self.assertEqual(module.NODE_ID, "DatangPhotoPrintCrop")
        self.assertIs(module.NODE_CLASS_MAPPINGS[module.NODE_ID], module.DatangPhotoPrintCrop)
        self.assertEqual(module.NODE_DISPLAY_NAME_MAPPINGS[module.NODE_ID], "大汤生活照打印裁剪")
        self.assertEqual(module.DatangPhotoPrintCrop.CATEGORY, "大汤自制节点/图像")
        self.assertEqual(
            list(module.DatangPhotoPrintCrop.INPUT_TYPES()["required"]),
            [
                "图像",
                "成品尺寸",
                "照片方向",
                "裁剪方式",
                "焦点位置",
                "自定义宽",
                "自定义高",
                "自定义单位",
                "DPI",
            ],
        )
        self.assertEqual(module.VISIBLE_CROP_OPTIONS, ("居中裁剪", "保留全图并补边"))
        self.assertEqual(module.CROP_OPTIONS, ("居中裁剪", "指定焦点裁剪", "保留全图并补边"))
        self.assertEqual(module.DatangPhotoPrintCrop.RETURN_TYPES, ("IMAGE", "INT", "MASK"))
        self.assertEqual(module.DatangPhotoPrintCrop.RETURN_NAMES, ("处理后图像", "DPI", "补边遮罩"))
        self.assertFalse(hasattr(module.DatangPhotoPrintCrop, "OUTPUT_NODE"))

    def test_print_presets_and_direction_resolve_to_exact_pixels(self):
        self.assertEqual(
            module.resolve_output_size("6寸（4 x 6 英寸）", "竖版", 1, 1, "像素", 300, 2000, 3000),
            (1200, 1800, 300),
        )
        self.assertEqual(
            module.resolve_output_size("8寸（6 x 8 英寸）", "横版", 1, 1, "像素", 300, 2000, 3000),
            (2400, 1800, 300),
        )
        self.assertEqual(
            module.resolve_output_size("5寸（3.5 x 5 英寸）", "跟随原图", 1, 1, "像素", 300, 1600, 900),
            (1500, 1050, 300),
        )

    def test_center_crop_uses_the_middle_without_stretching_and_returns_black_mask(self):
        torch = self.require_torch()
        columns = torch.arange(8, dtype=torch.float32).reshape(1, 1, 8, 1).expand(1, 4, 8, 3) / 8
        result, dpi, mask = self.run_custom(columns)
        self.assertEqual(tuple(result.shape), (1, 4, 4, 3))
        self.assertTrue(torch.equal(result, columns[:, :, 2:6, :]))
        self.assertEqual(dpi, 300)
        self.assertEqual(tuple(mask.shape), (1, 4, 4))
        self.assertEqual(float(mask.max()), 0.0)

    def test_specified_focus_selects_the_requested_horizontal_edge_for_legacy_workflows(self):
        torch = self.require_torch()
        columns = torch.arange(8, dtype=torch.float32).reshape(1, 1, 8, 1).expand(1, 4, 8, 3) / 8
        left, _, left_mask = self.run_custom(columns, method="指定焦点裁剪", focus="左侧")
        right, _, right_mask = self.run_custom(columns, method="指定焦点裁剪", focus="右侧")
        self.assertTrue(torch.equal(left, columns[:, :, :4, :]))
        self.assertTrue(torch.equal(right, columns[:, :, 4:, :]))
        self.assertEqual(float(left_mask.max()), 0.0)
        self.assertEqual(float(right_mask.max()), 0.0)

    def test_specified_focus_selects_the_requested_vertical_edge_for_legacy_workflows(self):
        torch = self.require_torch()
        rows = torch.arange(8, dtype=torch.float32).reshape(1, 8, 1, 1).expand(1, 8, 4, 3) / 8
        top, _, _ = self.run_custom(rows, method="指定焦点裁剪", focus="上方")
        bottom, _, _ = self.run_custom(rows, method="指定焦点裁剪", focus="下方")
        self.assertTrue(torch.equal(top, rows[:, :4, :, :]))
        self.assertTrue(torch.equal(bottom, rows[:, 4:, :, :]))

    def test_keep_full_image_adds_border_and_marks_only_padding_white(self):
        torch = self.require_torch()
        border = torch.tensor([0.1, 0.2, 0.3], dtype=torch.float32)
        image = border.reshape(1, 1, 1, 3).expand(1, 4, 8, 3).clone()
        image[:, 1:3, 1:7, :] = torch.tensor([0.9, 0.8, 0.7])
        result, _, mask = self.run_custom(image, method="保留全图并补边", width=8, height=8)
        self.assertEqual(tuple(result.shape), (1, 8, 8, 3))
        self.assertEqual(tuple(mask.shape), (1, 8, 8))
        self.assertTrue(torch.allclose(result[0, 0], border.expand(8, 3), atol=1e-6))
        self.assertTrue(torch.equal(mask[0, :2], torch.ones((2, 8))))
        self.assertTrue(torch.equal(mask[0, 2:6], torch.zeros((4, 8))))
        self.assertTrue(torch.equal(mask[0, 6:], torch.ones((2, 8))))

    def test_mask_uses_geometry_even_when_source_matches_border_color(self):
        torch = self.require_torch()
        image = torch.full((1, 4, 8, 3), 0.25, dtype=torch.float32)
        _, _, mask = self.run_custom(image, method="保留全图并补边", width=8, height=8)
        self.assertEqual(float(mask.sum()), 32.0)
        self.assertEqual(float(mask[0, 3, 3]), 0.0)
        self.assertEqual(float(mask[0, 0, 3]), 1.0)

    def test_matching_aspect_ratio_needs_no_padding_and_returns_black_mask(self):
        torch = self.require_torch()
        image = torch.rand((1, 4, 8, 3), dtype=torch.float32)
        result, _, mask = self.run_custom(image, method="保留全图并补边", width=8, height=4)
        self.assertTrue(torch.equal(result, image))
        self.assertEqual(float(mask.max()), 0.0)

    def test_invalid_or_unsafe_custom_size_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "必须大于 0"):
            module.resolve_output_size("自定义尺寸", "竖版", 0, 5, "像素", 300, 100, 100)
        with self.assertRaisesRegex(ValueError, "过大"):
            module.resolve_output_size("自定义尺寸", "竖版", 8192, 8192, "像素", 300, 100, 100)

    def test_batch_is_rejected_and_preview_or_detector_dependencies_are_absent(self):
        torch = self.require_torch()
        image = torch.zeros((2, 4, 4, 3), dtype=torch.float32)
        with self.assertRaisesRegex(ValueError, "一次只处理一张"):
            self.run_custom(image)
        source = inspect.getsource(module).lower()
        self.assertNotIn("previewimage", source)
        self.assertNotIn("datang_preview", source)
        self.assertNotIn("detect_face", source)
        self.assertNotIn("mediapipe", source)
        self.assertNotIn("mtcnn", source)


if __name__ == "__main__":
    unittest.main()
