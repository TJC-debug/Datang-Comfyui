from __future__ import annotations

from typing import Any


NODE_ID = "DatangPhotoPrintCrop"
MAX_OUTPUT_SIDE = 8192
MAX_OUTPUT_PIXELS = 24_000_000

SIZE_PRESETS: dict[str, tuple[float, float]] = {
    "5寸（3.5 x 5 英寸）": (3.5, 5.0),
    "6寸（4 x 6 英寸）": (4.0, 6.0),
    "7寸（5 x 7 英寸）": (5.0, 7.0),
    "8寸（6 x 8 英寸）": (6.0, 8.0),
    "10寸（8 x 10 英寸）": (8.0, 10.0),
    "12寸（10 x 12 英寸）": (10.0, 12.0),
}
SIZE_OPTIONS = (*SIZE_PRESETS.keys(), "自定义尺寸")
DIRECTION_OPTIONS = ("跟随原图", "横版", "竖版")
CROP_OPTIONS = ("居中裁剪", "指定焦点裁剪", "保留全图并补边")
VISIBLE_CROP_OPTIONS = ("居中裁剪", "保留全图并补边")
FOCUS_POINTS: dict[str, tuple[float, float]] = {
    "居中": (0.5, 0.5),
    "左上": (0.0, 0.0),
    "上方": (0.5, 0.0),
    "右上": (1.0, 0.0),
    "左侧": (0.0, 0.5),
    "右侧": (1.0, 0.5),
    "左下": (0.0, 1.0),
    "下方": (0.5, 1.0),
    "右下": (1.0, 1.0),
}


def _validate_output_size(width: int, height: int) -> tuple[int, int]:
    if width < 1 or height < 1:
        raise ValueError("输出尺寸必须至少为 1 x 1 像素")
    if width > MAX_OUTPUT_SIDE or height > MAX_OUTPUT_SIDE or width * height > MAX_OUTPUT_PIXELS:
        raise ValueError(
            f"输出尺寸 {width} x {height} 过大；"
            f"单边上限 {MAX_OUTPUT_SIDE}px，总像素上限约 {MAX_OUTPUT_PIXELS // 1_000_000}MP"
        )
    return width, height


def resolve_output_size(
    preset: str,
    direction: str,
    custom_width: float,
    custom_height: float,
    unit: str,
    dpi: int,
    source_width: int,
    source_height: int,
) -> tuple[int, int, int]:
    final_dpi = int(dpi)
    if preset == "自定义尺寸":
        width = float(custom_width)
        height = float(custom_height)
        if width <= 0 or height <= 0:
            raise ValueError("使用自定义尺寸时，自定义宽和自定义高必须大于 0")
        if unit == "英寸":
            width_px = int(round(width * final_dpi))
            height_px = int(round(height * final_dpi))
        elif unit == "厘米":
            width_px = int(round(width * final_dpi / 2.54))
            height_px = int(round(height * final_dpi / 2.54))
        elif unit == "像素":
            width_px = int(round(width))
            height_px = int(round(height))
        else:
            raise ValueError(f"不支持的尺寸单位：{unit}")
    elif preset in SIZE_PRESETS:
        width_inch, height_inch = SIZE_PRESETS[preset]
        width_px = int(round(width_inch * final_dpi))
        height_px = int(round(height_inch * final_dpi))
    else:
        raise ValueError(f"不支持的成品尺寸：{preset}")

    short_side, long_side = sorted((width_px, height_px))
    if direction == "横版":
        output_width, output_height = long_side, short_side
    elif direction == "竖版":
        output_width, output_height = short_side, long_side
    elif direction == "跟随原图":
        if source_width >= source_height:
            output_width, output_height = long_side, short_side
        else:
            output_width, output_height = short_side, long_side
    else:
        raise ValueError(f"不支持的照片方向：{direction}")

    output_width, output_height = _validate_output_size(output_width, output_height)
    return output_width, output_height, final_dpi


def calculate_crop_box(
    source_width: int,
    source_height: int,
    output_width: int,
    output_height: int,
    align_x: float,
    align_y: float,
) -> tuple[int, int, int, int]:
    source_ratio = source_width / source_height
    output_ratio = output_width / output_height
    if source_ratio > output_ratio:
        crop_height = source_height
        crop_width = max(1, min(source_width, int(round(source_height * output_ratio))))
    else:
        crop_width = source_width
        crop_height = max(1, min(source_height, int(round(source_width / output_ratio))))

    crop_x0 = int(round((source_width - crop_width) * align_x))
    crop_y0 = int(round((source_height - crop_height) * align_y))
    crop_x0 = max(0, min(source_width - crop_width, crop_x0))
    crop_y0 = max(0, min(source_height - crop_height, crop_y0))
    return crop_x0, crop_y0, crop_x0 + crop_width, crop_y0 + crop_height


def _resize_image(image: Any, output_width: int, output_height: int) -> Any:
    import torch.nn.functional as functional

    if tuple(image.shape[:2]) == (output_height, output_width):
        return image
    return functional.interpolate(
        image.permute(2, 0, 1).unsqueeze(0),
        size=(output_height, output_width),
        mode="bicubic",
        align_corners=False,
        antialias=True,
    )[0].permute(1, 2, 0).clamp(0.0, 1.0)


def estimate_border_color(image: Any) -> Any:
    import torch

    border_pixels = torch.cat(
        (
            image[0, :, :3],
            image[-1, :, :3],
            image[:, 0, :3],
            image[:, -1, :3],
        ),
        dim=0,
    )
    return border_pixels.median(dim=0).values


def crop_to_output(
    source: Any,
    output_width: int,
    output_height: int,
    align_x: float,
    align_y: float,
) -> Any:
    source_height, source_width = [int(value) for value in source.shape[:2]]
    x0, y0, x1, y1 = calculate_crop_box(
        source_width,
        source_height,
        output_width,
        output_height,
        align_x,
        align_y,
    )
    return _resize_image(source[y0:y1, x0:x1, :3], output_width, output_height)


def fit_with_border_and_mask(source: Any, output_width: int, output_height: int) -> tuple[Any, Any]:
    source_height, source_width = [int(value) for value in source.shape[:2]]
    scale = min(output_width / source_width, output_height / source_height)
    fitted_width = max(1, min(output_width, int(round(source_width * scale))))
    fitted_height = max(1, min(output_height, int(round(source_height * scale))))
    fitted = _resize_image(source, fitted_width, fitted_height)
    fill_color = estimate_border_color(source)
    result = fill_color.reshape(1, 1, 3).expand(output_height, output_width, 3).clone()
    fill_mask = source.new_ones((output_height, output_width))
    offset_x = (output_width - fitted_width) // 2
    offset_y = (output_height - fitted_height) // 2
    result[offset_y : offset_y + fitted_height, offset_x : offset_x + fitted_width] = fitted
    fill_mask[offset_y : offset_y + fitted_height, offset_x : offset_x + fitted_width] = 0.0
    return result, fill_mask


def fit_with_border(source: Any, output_width: int, output_height: int) -> Any:
    """Compatibility helper for callers that only need the composed image."""
    result, _ = fit_with_border_and_mask(source, output_width, output_height)
    return result


class DatangPhotoPrintCrop:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "图像": ("IMAGE",),
                "成品尺寸": (SIZE_OPTIONS, {"default": "6寸（4 x 6 英寸）"}),
                "照片方向": (DIRECTION_OPTIONS, {"default": "跟随原图"}),
                "裁剪方式": (CROP_OPTIONS, {"default": "居中裁剪"}),
                "焦点位置": (tuple(FOCUS_POINTS), {"default": "居中"}),
                "自定义宽": (
                    "FLOAT",
                    {"default": 10.0, "min": 0.01, "max": 8192.0, "step": 0.01, "round": 0.01},
                ),
                "自定义高": (
                    "FLOAT",
                    {"default": 15.0, "min": 0.01, "max": 8192.0, "step": 0.01, "round": 0.01},
                ),
                "自定义单位": (("厘米", "英寸", "像素"), {"default": "厘米"}),
                "DPI": ("INT", {"default": 300, "min": 72, "max": 1200, "step": 1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "MASK")
    RETURN_NAMES = ("处理后图像", "DPI", "补边遮罩")
    FUNCTION = "crop_photo"
    CATEGORY = "大汤自制节点/图像"
    DESCRIPTION = "生活照打印裁剪：居中裁剪，或保留全图并使用边框颜色补边；白色遮罩标出新增补边区域。"

    def crop_photo(
        self,
        图像: Any,
        成品尺寸: str,
        照片方向: str,
        裁剪方式: str,
        焦点位置: str,
        自定义宽: float,
        自定义高: float,
        自定义单位: str,
        DPI: int,
    ) -> dict[str, Any]:
        import torch

        if 图像.ndim != 4 or 图像.shape[-1] < 3:
            raise ValueError("图像必须是 ComfyUI IMAGE 格式")
        if 图像.shape[0] != 1:
            raise ValueError("本节点一次只处理一张照片；批量请交给纳贝队列")

        source = 图像[0, ..., :3].to(dtype=torch.float32).clamp(0.0, 1.0)
        source_height, source_width = [int(value) for value in source.shape[:2]]
        output_width, output_height, final_dpi = resolve_output_size(
            成品尺寸,
            照片方向,
            自定义宽,
            自定义高,
            自定义单位,
            DPI,
            source_width,
            source_height,
        )

        if 裁剪方式 == "保留全图并补边":
            result, fill_mask = fit_with_border_and_mask(source, output_width, output_height)
        elif 裁剪方式 == "居中裁剪":
            result = crop_to_output(source, output_width, output_height, 0.5, 0.5)
            fill_mask = source.new_zeros((output_height, output_width))
        elif 裁剪方式 == "指定焦点裁剪":
            if 焦点位置 not in FOCUS_POINTS:
                raise ValueError(f"不支持的焦点位置：{焦点位置}")
            align_x, align_y = FOCUS_POINTS[焦点位置]
            result = crop_to_output(source, output_width, output_height, align_x, align_y)
            fill_mask = source.new_zeros((output_height, output_width))
        else:
            raise ValueError(f"不支持的裁剪方式：{裁剪方式}")

        return result.unsqueeze(0), final_dpi, fill_mask.unsqueeze(0)


NODE_CLASS_MAPPINGS = {NODE_ID: DatangPhotoPrintCrop}
NODE_DISPLAY_NAME_MAPPINGS = {NODE_ID: "大汤生活照打印裁剪"}
