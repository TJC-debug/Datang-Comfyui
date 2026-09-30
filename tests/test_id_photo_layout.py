import json
import unittest

from id_photo_layout import (
    DatangIdPhotoLayout,
    IdPhotoLayoutError,
    parse_layout,
    reflow_layout_to_photo_size,
)


def layout(**overrides):
    value = {
        "schemaVersion": 1,
        "layoutId": "layout-a",
        "canvas": {"width": 600, "height": 400, "background": "#ffffff"},
        "slots": [
            {"x": 20, "y": 30, "width": 120, "height": 160},
            {"x": 160, "y": 30, "width": 120, "height": 160},
        ],
        "cropMarks": [{"x1": 10, "y1": 20, "x2": 40, "y2": 20, "width": 2}],
    }
    value.update(overrides)
    return value


class IdPhotoLayoutContractTests(unittest.TestCase):
    def test_node_contract_is_registered_for_image_and_json(self):
        required = DatangIdPhotoLayout.INPUT_TYPES()["required"]
        self.assertEqual(required["图片"], ("IMAGE",))
        self.assertEqual(required["DPI"][0], "INT")
        self.assertEqual(required["DPI"][1]["default"], 300)
        external_dpi = DatangIdPhotoLayout.INPUT_TYPES()["optional"]["输入DPI"]
        self.assertEqual(external_dpi[0], "INT")
        self.assertTrue(external_dpi[1]["forceInput"])
        optional = DatangIdPhotoLayout.INPUT_TYPES()["optional"]
        self.assertEqual(optional["输入照片宽度"][0], "INT")
        self.assertEqual(optional["输入照片高度"][0], "INT")
        self.assertTrue(optional["输入照片宽度"][1]["forceInput"])
        self.assertTrue(optional["输入照片高度"][1]["forceInput"])
        self.assertEqual(required["排版数据"][0], "STRING")
        self.assertEqual(DatangIdPhotoLayout.RETURN_TYPES, ("IMAGE", "STRING", "INT"))

    def test_valid_layout_keeps_exact_pixels_and_background(self):
        parsed = parse_layout(json.dumps(layout()))
        self.assertEqual(parsed["canvas"]["width"], 600)
        self.assertEqual(parsed["canvas"]["height"], 400)
        self.assertEqual(parsed["canvas"]["background"], (1.0, 1.0, 1.0))
        self.assertEqual(len(parsed["slots"]), 2)

    def test_rejects_out_of_bounds_and_overlapping_slots(self):
        with self.assertRaisesRegex(IdPhotoLayoutError, "超出画布"):
            parse_layout(layout(slots=[{"x": 590, "y": 0, "width": 20, "height": 20}]))
        with self.assertRaisesRegex(IdPhotoLayoutError, "重叠"):
            parse_layout(layout(slots=[
                {"x": 0, "y": 0, "width": 100, "height": 100},
                {"x": 50, "y": 50, "width": 100, "height": 100},
            ]))

    def test_rejects_unknown_schema_and_diagonal_crop_marks(self):
        with self.assertRaisesRegex(IdPhotoLayoutError, "v1"):
            parse_layout(layout(schemaVersion=2))
        invalid = layout(cropMarks=[{"x1": 0, "y1": 0, "x2": 10, "y2": 10}])
        with self.assertRaisesRegex(IdPhotoLayoutError, "水平或垂直"):
            parse_layout(invalid)

    def test_crop_marks_are_clipped_out_of_every_photo_slot(self):
        parsed = parse_layout(layout(
            slots=[{"x": 20, "y": 30, "width": 120, "height": 160}],
            cropMarks=[{"x1": 0, "y1": 50, "x2": 200, "y2": 50, "width": 1}],
        ))
        self.assertEqual(parsed["cropMarks"], [
            {"x1": 0, "y1": 50, "x2": 19, "y2": 50, "width": 1},
            {"x1": 140, "y1": 50, "x2": 200, "y2": 50, "width": 1},
        ])

    def test_dpi_is_validated_in_the_execution_contract(self):
        parsed = parse_layout(layout(dpi=350))
        self.assertEqual(parsed["dpi"], 350)
        self.assertEqual(parse_layout(layout())["dpi"], 300)
        with self.assertRaisesRegex(IdPhotoLayoutError, "dpi"):
            parse_layout(layout(dpi=50))

    def test_image_orientation_is_validated_and_old_ui_settings_are_migrated(self):
        parsed = parse_layout(layout(imageOrientation="landscape"))
        self.assertEqual(parsed["imageOrientation"], "landscape")
        migrated = parse_layout(layout(_ui={"settings": {"photoOrientation": "portrait"}}))
        self.assertEqual(migrated["imageOrientation"], "portrait")
        with self.assertRaisesRegex(IdPhotoLayoutError, "imageOrientation"):
            parse_layout(layout(imageOrientation="diagonal"))

    def test_landscape_orientation_rotates_a_portrait_input_before_composition(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        source = torch.tensor([[[[1.0, 0.0, 0.0]], [[0.0, 0.0, 1.0]]]])
        contract = layout(
            imageOrientation="landscape",
            canvas={"width": 2, "height": 1, "background": "#ffffff"},
            slots=[{"x": 0, "y": 0, "width": 2, "height": 1}],
            cropMarks=[],
        )
        output, receipt, dpi = DatangIdPhotoLayout().compose(source, 300, json.dumps(contract))
        self.assertEqual(tuple(output.shape), (1, 1, 2, 3))
        self.assertTrue(torch.equal(output[0, 0, 0], torch.tensor([0.0, 0.0, 1.0])))
        self.assertTrue(torch.equal(output[0, 0, 1], torch.tensor([1.0, 0.0, 0.0])))
        self.assertEqual(json.loads(receipt)["imageOrientation"], "landscape")
        self.assertEqual(dpi, 300)

        protected_contract = layout(
            canvas={"width": 3, "height": 1, "background": "#ffffff"},
            slots=[{"x": 1, "y": 0, "width": 1, "height": 1}],
            cropMarks=[{"x1": 0, "y1": 0, "x2": 2, "y2": 0, "width": 1}],
        )
        red_pixel = torch.tensor([[[[1.0, 0.0, 0.0]]]])
        protected, _, _ = DatangIdPhotoLayout().compose(red_pixel, 300, json.dumps(protected_contract))
        self.assertTrue(torch.equal(protected[0, 0, 1], torch.tensor([1.0, 0.0, 0.0])))
        self.assertTrue(torch.equal(protected[0, 0, 0], torch.tensor([0.0, 0.0, 0.0])))
        self.assertTrue(torch.equal(protected[0, 0, 2], torch.tensor([0.0, 0.0, 0.0])))

    def test_each_slot_can_rotate_the_same_person_independently(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")

        source = torch.tensor([[[[1.0, 0.0, 0.0]], [[0.0, 0.0, 1.0]]]])
        contract = layout(
            imageOrientation="original",
            canvas={"width": 3, "height": 2, "background": "#ffffff"},
            slots=[
                {"x": 0, "y": 0, "width": 1, "height": 2, "rotation": 0},
                {"x": 1, "y": 0, "width": 2, "height": 1, "rotation": 90},
            ],
            cropMarks=[],
        )

        parsed = parse_layout(contract)
        self.assertEqual([slot["rotation"] for slot in parsed["slots"]], [0, 90])
        output, _, _ = DatangIdPhotoLayout().compose(source, 300, json.dumps(contract))
        self.assertTrue(torch.equal(output[0, 0, 0], torch.tensor([1.0, 0.0, 0.0])))
        self.assertTrue(torch.equal(output[0, 1, 0], torch.tensor([0.0, 0.0, 1.0])))
        self.assertTrue(torch.equal(output[0, 0, 1], torch.tensor([0.0, 0.0, 1.0])))
        self.assertTrue(torch.equal(output[0, 0, 2], torch.tensor([1.0, 0.0, 0.0])))

        with self.assertRaisesRegex(IdPhotoLayoutError, "rotation"):
            parse_layout(layout(slots=[{"x": 0, "y": 0, "width": 1, "height": 1, "rotation": 45}]))

    def test_downscaling_uses_pillow_lanczos_without_changing_contain_layout(self):
        try:
            import numpy as np
            import torch
            from PIL import Image
        except ImportError:
            self.skipTest("当前测试 Python 缺少 torch、numpy 或 Pillow")

        pixels = torch.arange(8 * 8 * 3, dtype=torch.float32).reshape(1, 8, 8, 3)
        source = torch.remainder(pixels * 37, 256).div(255)
        contract = layout(
            canvas={"width": 5, "height": 5, "background": "#ffffff"},
            slots=[{"x": 1, "y": 1, "width": 3, "height": 3}],
            cropMarks=[],
        )

        output, receipt, _ = DatangIdPhotoLayout().compose(source, 300, json.dumps(contract))
        source_uint8 = source[0].mul(255).round().to(torch.uint8).numpy()
        expected = np.asarray(
            Image.fromarray(source_uint8, mode="RGB").resize(
                (3, 3),
                resample=getattr(Image, "Resampling", Image).LANCZOS,
            ),
            dtype=np.float32,
        ) / 255

        self.assertTrue(np.array_equal(output[0, 1:4, 1:4].numpy(), expected))
        self.assertTrue(torch.equal(output[0, 0, 0], torch.tensor([1.0, 1.0, 1.0])))
        self.assertEqual(json.loads(receipt)["resizeFilter"], "lanczos")

    def test_external_dpi_input_scales_the_frozen_layout_without_reflow(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        source = torch.zeros((1, 1, 1, 3))
        contract = layout(
            dpi=300,
            canvas={"width": 600, "height": 400, "background": "#ffffff"},
            slots=[{"x": 100, "y": 50, "width": 200, "height": 300}],
            cropMarks=[{"x1": 10, "y1": 20, "x2": 30, "y2": 20, "width": 1}],
        )
        output, receipt, dpi = DatangIdPhotoLayout().compose(source, 300, json.dumps(contract), 输入DPI=600)
        self.assertEqual(tuple(output.shape), (1, 800, 1200, 3))
        self.assertEqual(dpi, 600)
        parsed_receipt = json.loads(receipt)
        self.assertEqual(parsed_receipt["layoutDpi"], 300)
        self.assertEqual(parsed_receipt["dpiSource"], "input")

    def test_external_dpi_does_not_validate_a_legacy_polluted_internal_widget(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        source = torch.zeros((1, 1, 1, 3))
        contract = layout(
            dpi=300,
            canvas={"width": 2, "height": 2, "background": "#ffffff"},
            slots=[{"x": 0, "y": 0, "width": 1, "height": 1}],
            cropMarks=[],
        )
        output, receipt, dpi = DatangIdPhotoLayout().compose(
            source,
            source,
            json.dumps(contract),
            输入DPI=600,
        )
        self.assertEqual(tuple(output.shape), (1, 4, 4, 3))
        self.assertEqual(dpi, 600)
        self.assertEqual(json.loads(receipt)["dpiSource"], "input")

    def test_external_photo_size_reflows_existing_rows_without_changing_canvas(self):
        contract = parse_layout(layout(
            dpi=300,
            canvas={"width": 500, "height": 400, "background": "#ffffff"},
            slots=[
                {"x": 90, "y": 50, "width": 100, "height": 140},
                {"x": 210, "y": 50, "width": 100, "height": 140},
                {"x": 90, "y": 210, "width": 100, "height": 140},
                {"x": 210, "y": 210, "width": 100, "height": 140},
            ],
            cropMarks=[{"x1": 10, "y1": 20, "x2": 40, "y2": 20, "width": 1}],
        ))
        reflowed = reflow_layout_to_photo_size(contract, 80, 120)
        self.assertEqual(reflowed["canvas"]["width"], 500)
        self.assertEqual(reflowed["canvas"]["height"], 400)
        self.assertEqual(
            [(slot["x"], slot["y"], slot["width"], slot["height"]) for slot in reflowed["slots"]],
            [(160, 70, 80, 120), (260, 70, 80, 120), (160, 210, 80, 120), (260, 210, 80, 120)],
        )
        for mark in reflowed["cropMarks"]:
            for slot in reflowed["slots"]:
                if mark["y1"] == mark["y2"]:
                    self.assertFalse(slot["y"] <= mark["y1"] < slot["y"] + slot["height"] and max(mark["x1"], slot["x"]) <= min(mark["x2"], slot["x"] + slot["width"] - 1))
                else:
                    self.assertFalse(slot["x"] <= mark["x1"] < slot["x"] + slot["width"] and max(mark["y1"], slot["y"]) <= min(mark["y2"], slot["y"] + slot["height"] - 1))

    def test_external_photo_width_and_height_must_be_connected_together(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        source = torch.zeros((1, 100, 80, 3))
        with self.assertRaisesRegex(IdPhotoLayoutError, "必须同时连接"):
            DatangIdPhotoLayout().compose(
                source, 300, json.dumps(layout()), 输入照片宽度=80
            )

    def test_external_photo_size_keeps_canvas_and_is_recorded_in_receipt(self):
        try:
            import torch
        except ImportError:
            self.skipTest("当前测试 Python 未安装 torch")
        source = torch.zeros((1, 100, 80, 3))
        contract = layout(
            canvas={"width": 500, "height": 400, "background": "#ffffff"},
            slots=[
                {"x": 90, "y": 120, "width": 100, "height": 140},
                {"x": 210, "y": 120, "width": 100, "height": 140},
            ],
            cropMarks=[],
        )
        output, receipt, _ = DatangIdPhotoLayout().compose(
            source,
            300,
            json.dumps(contract),
            输入照片宽度=80,
            输入照片高度=100,
        )
        self.assertEqual(tuple(output.shape), (1, 400, 500, 3))
        parsed = json.loads(receipt)
        self.assertEqual(parsed["photoSizeSource"], "input")
        self.assertEqual(parsed["photoSize"], {"width": 80, "height": 100})

    def test_single_external_size_rejects_mixed_layout_and_oversized_grid(self):
        mixed = parse_layout(layout(
            canvas={"width": 600, "height": 500, "background": "#ffffff"},
            slots=[
                {"x": 0, "y": 0, "width": 100, "height": 140},
                {"x": 200, "y": 0, "width": 180, "height": 120, "rotation": 90},
            ],
            cropMarks=[],
        ))
        with self.assertRaisesRegex(IdPhotoLayoutError, "混合排版"):
            reflow_layout_to_photo_size(mixed, 80, 100)

        regular = parse_layout(layout(
            canvas={"width": 300, "height": 200, "background": "#ffffff"},
            slots=[
                {"x": 10, "y": 10, "width": 100, "height": 100},
                {"x": 120, "y": 10, "width": 100, "height": 100},
            ],
            cropMarks=[],
        ))
        with self.assertRaisesRegex(IdPhotoLayoutError, "无法按当前行列完整排入"):
            reflow_layout_to_photo_size(regular, 180, 180)


if __name__ == "__main__":
    unittest.main()
