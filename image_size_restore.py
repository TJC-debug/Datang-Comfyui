from __future__ import annotations

import math
from typing import Any


NODE_ID = "DatangImageSizeRestore"
MODE_EDGE = "仅补齐或裁掉边缘（不缩放）"
MODE_COVER = "等比缩放后居中裁剪"
MODE_STRETCH = "直接缩放到参考尺寸"
RESTORE_MODES = (MODE_EDGE, MODE_COVER, MODE_STRETCH)


def _validate_image(image: Any, name: str) -> None:
    if image.ndim != 4 or image.shape[-1] < 1:
        raise ValueError(f"{name}必须是 ComfyUI IMAGE 格式")
    if image.shape[1] < 1 or image.shape[2] < 1:
        raise ValueError(f"{name}尺寸必须至少为 1 x 1 像素")


def _resize(image: Any, width: int, height: int) -> Any:
    import torch.nn.functional as functional

    if tuple(image.shape[1:3]) == (height, width):
        return image
    return functional.interpolate(
        image.movedim(-1, 1),
        size=(height, width),
        mode="bicubic",
        align_corners=False,
        antialias=True,
    ).movedim(1, -1).clamp(0.0, 1.0)


def _border_median(image: Any) -> Any:
    import torch

    border_pixels = torch.cat(
        (
            image[:, 0, :, :],
            image[:, -1, :, :],
            image[:, :, 0, :],
            image[:, :, -1, :],
        ),
        dim=1,
    )
    return border_pixels.median(dim=1).values


def crop_or_pad_without_resampling(image: Any, width: int, height: int) -> Any:
    if tuple(image.shape[1:3]) == (height, width):
        return image

    source_height, source_width = [int(value) for value in image.shape[1:3]]
    copy_width = min(source_width, width)
    copy_height = min(source_height, height)
    source_x = (source_width - copy_width) // 2
    source_y = (source_height - copy_height) // 2
    destination_x = (width - copy_width) // 2
    destination_y = (height - copy_height) // 2

    fill = _border_median(image).reshape(image.shape[0], 1, 1, image.shape[-1])
    result = fill.expand(image.shape[0], height, width, image.shape[-1]).clone()
    result[
        :,
        destination_y : destination_y + copy_height,
        destination_x : destination_x + copy_width,
        :,
    ] = image[
        :,
        source_y : source_y + copy_height,
        source_x : source_x + copy_width,
        :,
    ]
    return result


def resize_to_cover(image: Any, width: int, height: int) -> Any:
    source_height, source_width = [int(value) for value in image.shape[1:3]]
    scale = max(width / source_width, height / source_height)
    resized_width = max(width, int(math.ceil(source_width * scale)))
    resized_height = max(height, int(math.ceil(source_height * scale)))
    resized = _resize(image, resized_width, resized_height)
    x0 = (resized_width - width) // 2
    y0 = (resized_height - height) // 2
    return resized[:, y0 : y0 + height, x0 : x0 + width, :]


class DatangImageSizeRestore:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "处理后图像": ("IMAGE",),
                "尺寸参考图像": (
                    "IMAGE",
                    {"tooltip": "只读取这张图的宽和高；通常连接模型处理前的精确尺寸图像。"},
                ),
                "回正方式": (
                    RESTORE_MODES,
                    {
                        "default": MODE_EDGE,
                        "tooltip": "只差少量像素时使用默认模式，可避免再次缩放整张图。",
                    },
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("回正后图像",)
    FUNCTION = "restore_size"
    CATEGORY = "大汤自制节点/图像"
    DESCRIPTION = "把处理后图像精确恢复为参考图像的宽高；默认只裁边或补边，不做重采样。"

    def restore_size(
        self,
        处理后图像: Any,
        尺寸参考图像: Any,
        回正方式: str,
    ) -> tuple[Any]:
        _validate_image(处理后图像, "处理后图像")
        _validate_image(尺寸参考图像, "尺寸参考图像")
        target_height, target_width = [int(value) for value in 尺寸参考图像.shape[1:3]]

        if 回正方式 == MODE_EDGE:
            result = crop_or_pad_without_resampling(处理后图像, target_width, target_height)
        elif 回正方式 == MODE_COVER:
            result = resize_to_cover(处理后图像, target_width, target_height)
        elif 回正方式 == MODE_STRETCH:
            result = _resize(处理后图像, target_width, target_height)
        else:
            raise ValueError(f"不支持的回正方式：{回正方式}")
        return (result,)


NODE_CLASS_MAPPINGS = {NODE_ID: DatangImageSizeRestore}
NODE_DISPLAY_NAME_MAPPINGS = {NODE_ID: "大汤图像尺寸回正"}
