from __future__ import annotations

import math
from typing import Any

try:
    from .id_photo_quick_crop import (
        _crop_with_fill,
        _detection_preview,
        _parse_hex_color,
        _resize_output,
        _rotate_about_eyes,
        _scale_detection,
    )
    from .portrait_composition import ASPECT_RATIOS, detect_face, estimate_border_color
except ImportError:  # 允许测试从 Datang-Comfyui 根目录直接导入
    from id_photo_quick_crop import (
        _crop_with_fill,
        _detection_preview,
        _parse_hex_color,
        _resize_output,
        _rotate_about_eyes,
        _scale_detection,
    )
    from portrait_composition import ASPECT_RATIOS, detect_face, estimate_border_color


NODE_ID = "DatangIdPhotoRatioCrop"
RATIO_SOURCE = "保持原图比例（自动识别）"
SIZE_SOURCE = "保持原图尺寸（宽高不变）"
RATIO_CUSTOM = "自定义比例"
RATIO_OPTIONS = (RATIO_SOURCE, SIZE_SOURCE, *ASPECT_RATIOS.keys(), RATIO_CUSTOM)


def resolve_crop_ratio(
    preset: str,
    custom_width: int,
    custom_height: int,
) -> tuple[int, int]:
    if preset in ASPECT_RATIOS:
        return ASPECT_RATIOS[preset]
    if preset != RATIO_CUSTOM:
        raise ValueError(f"不支持的比例预设：{preset}")

    ratio_width = int(custom_width)
    ratio_height = int(custom_height)
    if ratio_width < 1 or ratio_height < 1:
        raise ValueError("使用自定义比例时，比例宽和比例高必须大于 0")
    divisor = math.gcd(ratio_width, ratio_height)
    return ratio_width // divisor, ratio_height // divisor


class DatangIdPhotoRatioCrop:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "图像": ("IMAGE",),
                "人脸矫正": ("BOOLEAN", {"default": True}),
                "比例预设": (
                    RATIO_OPTIONS,
                    {
                        "default": "3:4 常用证件照",
                        "tooltip": "原图比例只自动读取宽高比；原图尺寸会在同一比例构图后恢复输入图的精确宽高。",
                    },
                ),
                "自定义比例宽": ("INT", {"default": 3, "min": 1, "max": 1000, "step": 1}),
                "自定义比例高": ("INT", {"default": 4, "min": 1, "max": 1000, "step": 1}),
                "单位": (
                    ("厘米", "像素"),
                    {
                        "default": "厘米",
                        "tooltip": "比例本身不改变单位；保留该参数以延续证件照裁剪的完整配置合同。",
                    },
                ),
                "DPI": (
                    "INT",
                    {
                        "default": 600,
                        "min": 72,
                        "max": 2000,
                        "step": 1,
                        "tooltip": "作为第 4 个 DPI 输出传递；比例裁剪不会据此强制缩放像素。",
                    },
                ),
                "脸部大小": (
                    "FLOAT",
                    {"default": 0.42, "min": 0.3, "max": 0.8, "step": 0.05, "display": "slider"},
                ),
                "垂直偏移": (
                    "FLOAT",
                    {"default": 0.38, "min": 0.3, "max": 0.5, "step": 0.05, "display": "slider"},
                ),
                "尺寸限制": ("INT", {"default": 2000, "min": 512, "max": 5120, "step": 1}),
                "填充模式": (("自定义颜色", "边框颜色"), {"default": "边框颜色"}),
            },
            "optional": {
                "自定义填充色": ("STRING", {"default": "#364254", "multiline": False}),
            },
        }

    RETURN_TYPES = ("IMAGE", "BOOLEAN", "MASK", "INT")
    RETURN_NAMES = ("裁剪后图像", "是否扩图", "扩展遮罩", "DPI")
    FUNCTION = "crop_id_photo_by_ratio"
    CATEGORY = "大汤自制节点/图像"
    DESCRIPTION = "保留证件照快速裁剪的完整构图参数；支持自动识别原图比例、恢复原图尺寸或选择固定比例。"

    def crop_id_photo_by_ratio(
        self,
        图像: Any,
        人脸矫正: bool,
        比例预设: str,
        自定义比例宽: int,
        自定义比例高: int,
        单位: str,
        DPI: int,
        脸部大小: float,
        垂直偏移: float,
        尺寸限制: int,
        填充模式: str,
        自定义填充色: str = "#364254",
    ) -> tuple[Any, bool, Any, int]:
        import torch

        if 图像.ndim != 4 or 图像.shape[-1] < 3:
            raise ValueError("图像必须是 ComfyUI IMAGE 格式")
        if 图像.shape[0] != 1:
            raise ValueError("本节点一次只处理一张照片；批量请交给纳贝队列")
        if 单位 not in ("厘米", "像素"):
            raise ValueError(f"不支持的单位：{单位}")

        source = 图像[0, ..., :3].to(dtype=torch.float32).clamp(0.0, 1.0)
        source_height, source_width = [int(value) for value in source.shape[:2]]
        uses_source_ratio = 比例预设 in (RATIO_SOURCE, SIZE_SOURCE)
        if uses_source_ratio:
            ratio_width = ratio_height = None
        else:
            ratio_width, ratio_height = resolve_crop_ratio(
                比例预设,
                自定义比例宽,
                自定义比例高,
            )
        detection_source, scale_x, scale_y = _detection_preview(source, int(尺寸限制))
        detection = detect_face(detection_source)
        if detection is None:
            raise ValueError(
                "未检测到人脸，证件照比例裁剪已停止；请换用正面、清晰且人物占比更大的照片"
            )
        detection = _scale_detection(detection, scale_x, scale_y)

        if 填充模式 == "边框颜色":
            fill_color = estimate_border_color(source)
        elif 填充模式 == "自定义颜色":
            fill_color = _parse_hex_color(自定义填充色, source)
        else:
            raise ValueError(f"不支持的填充模式：{填充模式}")

        working, rotation_mask, eye_center, _ = _rotate_about_eyes(
            source,
            detection,
            bool(人脸矫正),
            fill_color,
        )
        face_width = max(1.0, detection.bbox[2] - detection.bbox[0])
        requested_crop_width = max(1, int(round(face_width / float(脸部大小))))
        if uses_source_ratio:
            source_divisor = math.gcd(source_width, source_height)
            source_ratio_width = source_width // source_divisor
            source_ratio_height = source_height // source_divisor
            if source_ratio_width <= requested_crop_width:
                ratio_unit = max(1, int(round(requested_crop_width / source_ratio_width)))
                crop_width = source_ratio_width * ratio_unit
                crop_height = source_ratio_height * ratio_unit
            else:
                crop_width = requested_crop_width
                crop_height = max(1, int(round(crop_width * source_height / source_width)))
        else:
            ratio_unit = max(1, int(round(requested_crop_width / ratio_width)))
            crop_width = ratio_width * ratio_unit
            crop_height = ratio_height * ratio_unit
        crop_x0 = int(round(eye_center[0] - crop_width * 0.5))
        crop_y0 = int(round(eye_center[1] - crop_height * float(垂直偏移)))
        crop_box = (crop_x0, crop_y0, crop_x0 + crop_width, crop_y0 + crop_height)
        result, final_mask = _crop_with_fill(working, rotation_mask, crop_box, fill_color)
        if 比例预设 == SIZE_SOURCE:
            result, final_mask = _resize_output(
                result,
                final_mask,
                source_width,
                source_height,
            )
        has_expansion = bool(torch.count_nonzero(final_mask).item())
        return result.unsqueeze(0), has_expansion, final_mask.unsqueeze(0), int(DPI)


NODE_CLASS_MAPPINGS = {NODE_ID: DatangIdPhotoRatioCrop}
NODE_DISPLAY_NAME_MAPPINGS = {NODE_ID: "大汤证件照比例裁剪"}
