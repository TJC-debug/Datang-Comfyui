import unittest

import image_size_restore as module


class ImageSizeRestoreTests(unittest.TestCase):
    def require_torch(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        return torch

    def test_registration_and_contract(self):
        self.assertEqual(module.NODE_ID, "DatangImageSizeRestore")
        self.assertIs(module.NODE_CLASS_MAPPINGS[module.NODE_ID], module.DatangImageSizeRestore)
        self.assertEqual(module.NODE_DISPLAY_NAME_MAPPINGS[module.NODE_ID], "大汤图像尺寸回正")
        self.assertEqual(module.DatangImageSizeRestore.CATEGORY, "大汤自制节点/图像")
        self.assertEqual(
            list(module.DatangImageSizeRestore.INPUT_TYPES()["required"]),
            ["处理后图像", "尺寸参考图像", "回正方式"],
        )
        self.assertEqual(module.DatangImageSizeRestore.RETURN_TYPES, ("IMAGE",))

    def test_matching_size_is_returned_without_resampling(self):
        torch = self.require_torch()
        image = torch.rand((2, 12, 10, 3), dtype=torch.float32)
        reference = torch.zeros((1, 12, 10, 3), dtype=torch.float32)
        result = module.DatangImageSizeRestore().restore_size(image, reference, module.MODE_EDGE)[0]
        self.assertIs(result, image)

    def test_default_mode_pads_and_crops_without_changing_copied_pixels(self):
        torch = self.require_torch()
        small = torch.arange(2 * 2 * 3, dtype=torch.float32).reshape(1, 2, 2, 3) / 12.0
        large_reference = torch.zeros((1, 4, 4, 3), dtype=torch.float32)
        padded = module.DatangImageSizeRestore().restore_size(
            small, large_reference, module.MODE_EDGE
        )[0]
        self.assertEqual(tuple(padded.shape), (1, 4, 4, 3))
        self.assertTrue(torch.equal(padded[:, 1:3, 1:3, :], small))

        large = torch.arange(6 * 6 * 3, dtype=torch.float32).reshape(1, 6, 6, 3) / 108.0
        small_reference = torch.zeros((1, 4, 4, 3), dtype=torch.float32)
        cropped = module.DatangImageSizeRestore().restore_size(
            large, small_reference, module.MODE_EDGE
        )[0]
        self.assertTrue(torch.equal(cropped, large[:, 1:5, 1:5, :]))

    def test_resampling_modes_always_match_the_reference_dimensions(self):
        torch = self.require_torch()
        image = torch.rand((2, 17, 23, 3), dtype=torch.float32)
        reference = torch.zeros((1, 19, 13, 3), dtype=torch.float32)
        for mode in (module.MODE_COVER, module.MODE_STRETCH):
            with self.subTest(mode=mode):
                result = module.DatangImageSizeRestore().restore_size(image, reference, mode)[0]
                self.assertEqual(tuple(result.shape), (2, 19, 13, 3))

    def test_unknown_mode_is_rejected(self):
        torch = self.require_torch()
        image = torch.zeros((1, 4, 4, 3), dtype=torch.float32)
        with self.assertRaisesRegex(ValueError, "不支持的回正方式"):
            module.DatangImageSizeRestore().restore_size(image, image[:, :3], "未知")


if __name__ == "__main__":
    unittest.main()
