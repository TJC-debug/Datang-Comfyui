from __future__ import annotations

import math
from typing import Any

try:
    from .id_photo_quick_crop import _detection_preview, _eye_points, _scale_detection
    from .portrait_composition import ASPECT_RATIOS, detect_face
except ImportError:  # 允许在节点目录中直接运行专项测试
    from id_photo_quick_crop import _detection_preview, _eye_points, _scale_detection
    from portrait_composition import ASPECT_RATIOS, detect_face


NODE_ID = "DatangAspectCrop"
RATIO_SOURCE = "保持原图比例（不裁剪）"
RATIO_SOURCE_LEGACY = "保持原图比例"
RATIO_CUSTOM = "自定义比例"
RATIO_SQUARE = "1:1 正方形"
RATIO_SQUARE_LEGACY = "1:1"
RATIO_PRESETS = {
    RATIO_SQUARE: (1, 1),
    **{
        label: ratio
        for label, ratio in ASPECT_RATIOS.items()
        if label != RATIO_SQUARE_LEGACY
    },
}
RATIO_OPTIONS = (RATIO_SOURCE, *RATIO_PRESETS.keys())
FACE_DETECTION_SIZE_LIMIT = 2000

OUTPUT_SIZE_KEEP = "保持裁剪后尺寸（不缩放）"
OUTPUT_SIZE_LONGEST = "按最长边"
OUTPUT_SIZE_SHORTEST = "按最短边"
OUTPUT_SIZE_WIDTH = "按宽度"
OUTPUT_SIZE_HEIGHT = "按高度"
OUTPUT_SIZE_OPTIONS = (
    OUTPUT_SIZE_KEEP,
    OUTPUT_SIZE_LONGEST,
    OUTPUT_SIZE_SHORTEST,
    OUTPUT_SIZE_WIDTH,
    OUTPUT_SIZE_HEIGHT,
)
DEFAULT_TARGET_PIXELS = 1536


def resolve_crop_ratio(
    ratio_preset: str,
    custom_ratio_width: int,
    custom_ratio_height: int,
) -> tuple[int, int] | None:
    if ratio_preset in (RATIO_SOURCE, RATIO_SOURCE_LEGACY):
        return None
    if ratio_preset == RATIO_SQUARE_LEGACY:
        return RATIO_PRESETS[RATIO_SQUARE]
    if ratio_preset in RATIO_PRESETS:
        return RATIO_PRESETS[ratio_preset]
    if ratio_preset != RATIO_CUSTOM:
        raise ValueError(f"不支持的比例预设：{ratio_preset}")

    ratio_width = int(custom_ratio_width)
    ratio_height = int(custom_ratio_height)
    if ratio_width <= 0 or ratio_height <= 0:
        raise ValueError("自定义比例的宽和高必须大于 0")
    common_divisor = math.gcd(ratio_width, ratio_height)
    return ratio_width // common_divisor, ratio_height // common_divisor


def calculate_crop_box(
    source_width: int,
    source_height: int,
    ratio_width: int,
    ratio_height: int,
    focus: tuple[float, float] | None = None,
) -> tuple[int, int, int, int]:
    unit = min(source_width // ratio_width, source_height // ratio_height)
    if unit < 1:
        raise ValueError(
            f"输入图像 {source_width}×{source_height} 像素过小，"
            f"无法按 {ratio_width}:{ratio_height} 的精确整数比例裁剪"
        )

    crop_width = ratio_width * unit
    crop_height = ratio_height * unit
    max_x0 = source_width - crop_width
    max_y0 = source_height - crop_height
    if focus is None:
        x0 = max_x0 // 2
        y0 = max_y0 // 2
    else:
        focus_x, focus_y = focus
        x0 = int(round(float(focus_x) - crop_width * 0.5))
        y0 = int(round(float(focus_y) - crop_height * 0.5))
        x0 = max(0, min(max_x0, x0))
        y0 = max(0, min(max_y0, y0))
    return x0, y0, x0 + crop_width, y0 + crop_height


def crop_without_resampling(
    image: Any,
    ratio_width: int,
    ratio_height: int,
    focus: tuple[float, float] | None = None,
) -> Any:
    source_height, source_width = [int(value) for value in image.shape[1:3]]
    x0, y0, x1, y1 = calculate_crop_box(
        source_width,
        source_height,
        ratio_width,
        ratio_height,
        focus,
    )
    return image[:, y0:y1, x0:x1, :]


def calculate_output_size(
    source_width: int,
    source_height: int,
    output_size_mode: str,
    target_pixels: int,
) -> tuple[int, int]:
    if output_size_mode not in OUTPUT_SIZE_OPTIONS:
        raise ValueError(f"不支持的输出尺寸方式：{output_size_mode}")
    if output_size_mode == OUTPUT_SIZE_KEEP:
        return source_width, source_height

    target = int(target_pixels)
    if target < 1:
        raise ValueError("目标像素必须大于 0")

    def scaled(value: int, reference: int) -> int:
        return max(1, int(math.floor(value * target / reference + 0.5)))

    if output_size_mode == OUTPUT_SIZE_LONGEST:
        if source_width >= source_height:
            return target, scaled(source_height, source_width)
        return scaled(source_width, source_height), target
    if output_size_mode == OUTPUT_SIZE_SHORTEST:
        if source_width <= source_height:
            return target, scaled(source_height, source_width)
        return scaled(source_width, source_height), target
    if output_size_mode == OUTPUT_SIZE_WIDTH:
        return target, scaled(source_height, source_width)
    return scaled(source_width, source_height), target


def resize_for_output(image: Any, output_size_mode: str, target_pixels: int) -> Any:
    source_height, source_width = [int(value) for value in image.shape[1:3]]
    target_width, target_height = calculate_output_size(
        source_width,
        source_height,
        output_size_mode,
        target_pixels,
    )
    if (target_width, target_height) == (source_width, source_height):
        return image

    import torch.nn.functional as functional

    return functional.interpolate(
        image.movedim(-1, 1),
        size=(target_height, target_width),
        mode="bicubic",
        align_corners=False,
        antialias=True,
    ).movedim(1, -1).clamp(0.0, 1.0)


def calculate_face_crop_box(
    source_width: int,
    source_height: int,
    ratio_width: int,
    ratio_height: int,
    face_width: float,
    eye_center: tuple[float, float],
    face_size: float,
    vertical_offset: float,
) -> tuple[int, int, int, int]:
    if not math.isfinite(float(face_size)) or not 0.0 < float(face_size) <= 1.0:
        raise ValueError("脸部大小必须大于 0 且不超过 1")
    if not math.isfinite(float(vertical_offset)) or not 0.0 <= float(vertical_offset) <= 1.0:
        raise ValueError("垂直偏移必须在 0 到 1 之间")
    if ratio_width < 1 or ratio_height < 1:
        raise ValueError("裁剪比例的宽和高必须大于 0")

    requested_width = max(1.0, float(face_width) / float(face_size))
    max_unit = min(source_width // ratio_width, source_height // ratio_height)
    if max_unit < 1:
        raise ValueError(
            f"输入图像 {source_width}×{source_height} 像素过小，"
            f"无法按 {ratio_width}:{ratio_height} 的精确整数比例裁剪"
        )
    requested_unit = max(1, int(round(requested_width / float(ratio_width))))
    unit = min(max_unit, requested_unit)
    crop_width = ratio_width * unit
    crop_height = ratio_height * unit

    max_x0 = source_width - crop_width
    max_y0 = source_height - crop_height
    crop_x0 = int(round(float(eye_center[0]) - crop_width * 0.5))
    crop_y0 = int(round(float(eye_center[1]) - crop_height * float(vertical_offset)))
    crop_x0 = max(0, min(max_x0, crop_x0))
    crop_y0 = max(0, min(max_y0, crop_y0))
    return crop_x0, crop_y0, crop_x0 + crop_width, crop_y0 + crop_height


def detect_face_layout(source: Any) -> tuple[float, tuple[float, float]] | None:
    detection_source, scale_x, scale_y = _detection_preview(
        source[..., :3].float().clamp(0.0, 1.0),
        FACE_DETECTION_SIZE_LIMIT,
    )
    detection = detect_face(detection_source)
    if detection is None:
        return None
    detection = _scale_detection(detection, scale_x, scale_y)
    left_eye, right_eye, _ = _eye_points(detection)
    eye_center = (
        (left_eye[0] + right_eye[0]) * 0.5,
        (left_eye[1] + right_eye[1]) * 0.5,
    )
    face_width = max(1.0, detection.bbox[2] - detection.bbox[0])
    return face_width, eye_center


class DatangAspectCrop:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "图像": ("IMAGE",),
                "启用人脸识别": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "关闭时按整张画面中心最大裁剪；打开时识别主要人脸，并按脸部大小和垂直偏移决定裁剪框。",
                    },
                ),
                "比例预设": (
                    RATIO_OPTIONS,
                    {
                        "default": RATIO_SOURCE,
                        "tooltip": "两种模式共用同一比例；保持原图比例（不裁剪）会直接保留整张输入图。",
                    },
                ),
                "自定义比例宽": ("INT", {"default": 3, "min": 1, "max": 8192, "step": 1}),
                "自定义比例高": ("INT", {"default": 4, "min": 1, "max": 8192, "step": 1}),
            },
            "optional": {
                "脸部大小": (
                    "FLOAT",
                    {
                        "default": 0.42,
                        "min": 0.3,
                        "max": 0.8,
                        "step": 0.05,
                        "display": "slider",
                        "tooltip": "仅在按人脸构图时生效；数值越大，裁剪构图中的脸越大。",
                    },
                ),
                "垂直偏移": (
                    "FLOAT",
                    {
                        "default": 0.38,
                        "min": 0.3,
                        "max": 0.5,
                        "step": 0.05,
                        "display": "slider",
                        "tooltip": "仅在按人脸构图时生效；控制双眼在裁剪画面中的垂直位置。",
                    },
                ),
                "输出尺寸方式": (
                    OUTPUT_SIZE_OPTIONS,
                    {
                        "default": OUTPUT_SIZE_KEEP,
                        "tooltip": "仅对四种实际裁剪比例生效；保持原图比例（不裁剪）始终原样旁路。",
                    },
                ),
                "目标像素": (
                    "INT",
                    {
                        "default": DEFAULT_TARGET_PIXELS,
                        "min": 1,
                        "max": 8192,
                        "step": 1,
                        "tooltip": "指定最长边、最短边、宽度或高度的像素值，另一边按裁剪比例自动计算。",
                    },
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("裁剪后图像",)
    FUNCTION = "crop_aspect"
    CATEGORY = "大汤自制节点/图像"
    DESCRIPTION = "按目标比例裁剪，并可把实际裁剪结果等比缩放到指定边长；保持原图比例时始终原样旁路。"

    def crop_aspect(
        self,
        图像: Any,
        启用人脸识别: bool,
        比例预设: str,
        自定义比例宽: int,
        自定义比例高: int,
        脸部大小: float = 0.42,
        垂直偏移: float = 0.38,
        输出尺寸方式: str = OUTPUT_SIZE_KEEP,
        目标像素: int = DEFAULT_TARGET_PIXELS,
    ) -> tuple[Any]:
        if 图像.ndim != 4 or 图像.shape[-1] < 3:
            raise ValueError("图像必须是至少三通道的 ComfyUI IMAGE 格式")
        if 图像.shape[0] < 1 or 图像.shape[1] < 1 or 图像.shape[2] < 1:
            raise ValueError("输入图像的批次、宽和高必须大于 0")

        ratio = resolve_crop_ratio(比例预设, 自定义比例宽, 自定义比例高)
        source_height, source_width = [int(value) for value in 图像.shape[1:3]]
        if ratio is None:
            return (图像,)
        if not bool(启用人脸识别):
            if calculate_crop_box(source_width, source_height, *ratio) == (
                0,
                0,
                source_width,
                source_height,
            ):
                cropped = 图像
            else:
                cropped = crop_without_resampling(图像, *ratio)
            return (resize_for_output(cropped, 输出尺寸方式, 目标像素),)

        import torch

        results: list[Any] = []
        result_size: tuple[int, int] | None = None
        for index in range(int(图像.shape[0])):
            source = 图像[index]
            face_layout = detect_face_layout(source)
            if face_layout is None:
                raise ValueError(
                    f"第 {index + 1} 张图片未检测到人脸；"
                    "请关闭“按人脸构图”改用画面中心裁剪，或换用正面清晰照片"
                )
            face_width, eye_center = face_layout
            x0, y0, x1, y1 = calculate_face_crop_box(
                source_width,
                source_height,
                *ratio,
                face_width,
                eye_center,
                float(脸部大小),
                float(垂直偏移),
            )
            current = 图像[index : index + 1, y0:y1, x0:x1, :]
            current = resize_for_output(current, 输出尺寸方式, 目标像素)
            current_size = tuple(int(value) for value in current.shape[1:3])
            if result_size is None:
                result_size = current_size
            elif current_size != result_size:
                raise ValueError(
                    "同一 IMAGE 批次中的人脸大小不同，无法在不缩放、不补边的前提下合并输出；"
                    "请逐张处理或关闭“按人脸构图”"
                )
            results.append(current)
        return (torch.cat(results, dim=0),)


NODE_CLASS_MAPPINGS = {NODE_ID: DatangAspectCrop}
NODE_DISPLAY_NAME_MAPPINGS = {NODE_ID: "大汤图像比例裁剪"}
