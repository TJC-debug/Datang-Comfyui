from __future__ import annotations

import math
import re
from dataclasses import replace
from typing import Any

import cv2
import numpy as np

try:
    from .portrait_composition import FaceDetection, detect_face, estimate_border_color
except ImportError:  # 允许测试从 Datang-Comfyui 根目录直接导入
    from portrait_composition import FaceDetection, detect_face, estimate_border_color


NODE_ID = "DatangQuickIdPhotoCrop"
MAX_OUTPUT_SIDE = 8192
MAX_OUTPUT_PIXELS = 24_000_000

SIZE_PRESETS: dict[str, tuple[float, float, str, int | None]] = {
    "1寸（2.5 x 3.5 厘米）": (2.5, 3.5, "厘米", None),
    "大1寸（3.3 x 4.8 厘米）": (3.3, 4.8, "厘米", None),
    "小2寸（3.5 x 4.5 厘米）": (3.5, 4.5, "厘米", None),
    "2寸（3.5 x 4.9 厘米）": (3.5, 4.9, "厘米", None),
    "大2寸（3.5 x 5.3 厘米）": (3.5, 5.3, "厘米", None),
    "3寸（5.5 x 8.5 厘米）": (5.5, 8.5, "厘米", None),
    "5寸（8.9 x 12.7 厘米）": (8.9, 12.7, "厘米", None),
    "6寸（10.1 x 15.2 厘米）": (10.1, 15.2, "厘米", None),
    "身份证社保（2.6 x 3.2 厘米）": (2.6, 3.2, "厘米", None),
    "驾驶证（2.2 x 3.2 厘米）": (2.2, 3.2, "厘米", None),
    "日签（4.5 x 4.5 厘米）": (4.5, 4.5, "厘米", None),
    "美签（5.1 x 5.1 厘米）": (5.1, 5.1, "厘米", None),
    "研究生考试（3.0 x 4.0 厘米）": (3.0, 4.0, "厘米", None),
    "身份证电子（358 x 441 像素 DPI: 350）": (358, 441, "像素", 350),
    "普通话考试（390 x 567 像素 DPI: 300）": (390, 567, "像素", 300),
    "教师资格证（480 x 640 像素 DPI: 300）": (480, 640, "像素", 300),
    "护士资格证（160 x 210 像素 DPI: 300）": (160, 210, "像素", 300),
    "司法考试照（413 x 626 像素 DPI: 300）": (413, 626, "像素", 300),
    "执业医考照（354 x 472 像素 DPI: 300）": (354, 472, "像素", 300),
}
SIZE_OPTIONS = (*SIZE_PRESETS.keys(), "自定义尺寸")


def resolve_output_size(
    preset: str,
    custom_width: float,
    custom_height: float,
    unit: str,
    dpi: int,
) -> tuple[int, int, int]:
    if preset == "自定义尺寸":
        width, height, final_unit, final_dpi = custom_width, custom_height, unit, int(dpi)
        if width <= 0 or height <= 0:
            raise ValueError("使用自定义尺寸时，自定义宽和自定义高必须大于 0")
    elif preset in SIZE_PRESETS:
        width, height, final_unit, preset_dpi = SIZE_PRESETS[preset]
        final_dpi = int(preset_dpi if preset_dpi is not None else dpi)
    else:
        raise ValueError(f"不支持的预设尺寸：{preset}")

    if final_unit == "厘米":
        output_width = int(round(float(width) * final_dpi / 2.54))
        output_height = int(round(float(height) * final_dpi / 2.54))
    elif final_unit == "像素":
        output_width = int(round(float(width)))
        output_height = int(round(float(height)))
    else:
        raise ValueError(f"不支持的尺寸单位：{final_unit}")

    if output_width < 1 or output_height < 1:
        raise ValueError("输出尺寸必须至少为 1 x 1 像素")
    if (
        output_width > MAX_OUTPUT_SIDE
        or output_height > MAX_OUTPUT_SIDE
        or output_width * output_height > MAX_OUTPUT_PIXELS
    ):
        raise ValueError(
            f"输出尺寸 {output_width} x {output_height} 过大；"
            f"单边上限 {MAX_OUTPUT_SIDE}px，总像素上限约 {MAX_OUTPUT_PIXELS // 1_000_000}MP"
        )
    return output_width, output_height, final_dpi


def _parse_hex_color(value: str, reference: torch.Tensor) -> torch.Tensor:
    text = str(value or "").strip()
    short_match = re.fullmatch(r"#([0-9a-fA-F]{3})", text)
    if short_match:
        text = "#" + "".join(character * 2 for character in short_match.group(1))
    match = re.fullmatch(r"#([0-9a-fA-F]{6})", text)
    if not match:
        raise ValueError("自定义填充色必须是 #RRGGBB 或 #RGB 格式")
    raw = match.group(1)
    return reference.new_tensor([int(raw[index : index + 2], 16) / 255.0 for index in (0, 2, 4)])


def _detection_preview(source: torch.Tensor, size_limit: int) -> tuple[torch.Tensor, float, float]:
    import torch.nn.functional as functional

    height, width = [int(value) for value in source.shape[:2]]
    longest = max(height, width)
    if longest <= size_limit:
        return source, 1.0, 1.0
    scale = float(size_limit) / float(longest)
    preview_height = max(1, int(round(height * scale)))
    preview_width = max(1, int(round(width * scale)))
    preview = functional.interpolate(
        source.permute(2, 0, 1).unsqueeze(0),
        size=(preview_height, preview_width),
        mode="bilinear",
        align_corners=False,
        antialias=True,
    )[0].permute(1, 2, 0)
    return preview, width / preview_width, height / preview_height


def _scale_detection(detection: FaceDetection, scale_x: float, scale_y: float) -> FaceDetection:
    x0, y0, x1, y1 = detection.bbox
    landmarks = detection.landmarks
    scaled_landmarks: tuple[float, ...] | None = None
    if landmarks:
        values = list(landmarks)
        if len(values) >= 10:
            scaled_landmarks = tuple(
                [float(value) * scale_x for value in values[:5]]
                + [float(value) * scale_y for value in values[5:10]]
                + [float(value) for value in values[10:]]
            )
        elif len(values) % 2 == 0:
            scaled_landmarks = tuple(
                float(value) * (scale_x if index % 2 == 0 else scale_y)
                for index, value in enumerate(values)
            )
    return replace(
        detection,
        bbox=(x0 * scale_x, y0 * scale_y, x1 * scale_x, y1 * scale_y),
        landmarks=scaled_landmarks,
    )


def _eye_points(detection: FaceDetection) -> tuple[tuple[float, float], tuple[float, float], bool]:
    x0, y0, x1, y1 = detection.bbox
    width = max(1.0, x1 - x0)
    height = max(1.0, y1 - y0)
    landmarks = detection.landmarks
    if landmarks and len(landmarks) >= 10:
        values = np.asarray(landmarks[:10], dtype=np.float64)
        left = (float(values[0]), float(values[5]))
        right = (float(values[1]), float(values[6]))
        points_are_finite = all(math.isfinite(value) for point in (left, right) for value in point)
        points_are_plausible = (
            abs(right[0] - left[0]) >= width * 0.08
            and x0 - width * 0.35 <= left[0] <= x1 + width * 0.35
            and x0 - width * 0.35 <= right[0] <= x1 + width * 0.35
            and y0 - height * 0.35 <= left[1] <= y1 + height * 0.35
            and y0 - height * 0.35 <= right[1] <= y1 + height * 0.35
        )
        if points_are_finite and points_are_plausible:
            return (*sorted((left, right), key=lambda point: point[0]), True)

    eye_y = y0 + height * 0.42
    return ((x0 + width * 0.32, eye_y), (x0 + width * 0.68, eye_y), False)


def _rotate_about_eyes(
    source: torch.Tensor,
    detection: FaceDetection,
    enabled: bool,
    fill_color: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, tuple[float, float], float]:
    import torch

    left_eye, right_eye, has_landmarks = _eye_points(detection)
    eye_center = ((left_eye[0] + right_eye[0]) * 0.5, (left_eye[1] + right_eye[1]) * 0.5)
    angle = math.degrees(math.atan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0]))
    if not enabled or not has_landmarks or abs(angle) < 0.05:
        mask = source.new_zeros(source.shape[:2])
        return source, mask, eye_center, 0.0

    source_rgb = np.rint(source.detach().cpu().clamp(0.0, 1.0).numpy() * 255.0).astype(np.uint8)
    height, width = source_rgb.shape[:2]
    matrix = cv2.getRotationMatrix2D(eye_center, angle, 1.0)
    corners = np.asarray(
        [[[0.0, 0.0]], [[float(width), 0.0]], [[float(width), float(height)]], [[0.0, float(height)]]],
        dtype=np.float64,
    )
    rotated_corners = cv2.transform(corners, matrix).reshape(-1, 2)
    minimum = np.floor(rotated_corners.min(axis=0))
    maximum = np.ceil(rotated_corners.max(axis=0))
    output_width = max(1, int(maximum[0] - minimum[0]))
    output_height = max(1, int(maximum[1] - minimum[1]))
    matrix[0, 2] -= minimum[0]
    matrix[1, 2] -= minimum[1]
    fill_rgb = tuple(int(round(float(value) * 255.0)) for value in fill_color.tolist())
    rotated_rgb = cv2.warpAffine(
        source_rgb,
        matrix,
        (output_width, output_height),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=fill_rgb,
    )
    coverage = cv2.warpAffine(
        np.ones((height, width), dtype=np.uint8),
        matrix,
        (output_width, output_height),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    transformed_eye_center = cv2.transform(
        np.asarray([[[eye_center[0], eye_center[1]]]], dtype=np.float64), matrix
    )[0, 0]
    rotated = torch.from_numpy(rotated_rgb).to(device=source.device, dtype=source.dtype) / 255.0
    expansion_mask = torch.from_numpy((coverage == 0).astype(np.float32)).to(
        device=source.device,
        dtype=source.dtype,
    )
    return (
        rotated,
        expansion_mask,
        (float(transformed_eye_center[0]), float(transformed_eye_center[1])),
        angle,
    )


def _crop_with_fill(
    source: torch.Tensor,
    source_mask: torch.Tensor,
    crop_box: tuple[int, int, int, int],
    fill_color: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    x0, y0, x1, y1 = crop_box
    crop_width = x1 - x0
    crop_height = y1 - y0
    if crop_width < 1 or crop_height < 1:
        raise ValueError("裁剪区域尺寸无效")
    if (
        crop_width > MAX_OUTPUT_SIDE
        or crop_height > MAX_OUTPUT_SIDE
        or crop_width * crop_height > MAX_OUTPUT_PIXELS
    ):
        raise ValueError("按当前脸部大小计算出的裁剪区域过大，请提高脸部大小或换用更近的人像")

    result = fill_color.reshape(1, 1, 3).expand(crop_height, crop_width, 3).clone()
    mask = source.new_ones((crop_height, crop_width))
    source_height, source_width = [int(value) for value in source.shape[:2]]
    source_x0 = max(0, x0)
    source_y0 = max(0, y0)
    source_x1 = min(source_width, x1)
    source_y1 = min(source_height, y1)
    if source_x1 > source_x0 and source_y1 > source_y0:
        destination_x0 = source_x0 - x0
        destination_y0 = source_y0 - y0
        destination_x1 = destination_x0 + source_x1 - source_x0
        destination_y1 = destination_y0 + source_y1 - source_y0
        result[destination_y0:destination_y1, destination_x0:destination_x1] = source[
            source_y0:source_y1,
            source_x0:source_x1,
            :3,
        ]
        mask[destination_y0:destination_y1, destination_x0:destination_x1] = source_mask[
            source_y0:source_y1,
            source_x0:source_x1,
        ]
    return result, mask


def _resize_output(
    image: torch.Tensor,
    mask: torch.Tensor,
    output_width: int,
    output_height: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    import torch.nn.functional as functional

    if tuple(image.shape[:2]) == (output_height, output_width):
        return image, mask
    resized_image = functional.interpolate(
        image.permute(2, 0, 1).unsqueeze(0),
        size=(output_height, output_width),
        mode="bicubic",
        align_corners=False,
        antialias=True,
    )[0].permute(1, 2, 0).clamp(0.0, 1.0)
    resized_mask = functional.interpolate(
        mask.unsqueeze(0).unsqueeze(0),
        size=(output_height, output_width),
        mode="nearest",
    )[0, 0]
    return resized_image, (resized_mask > 0.5).to(dtype=image.dtype)


class DatangQuickIdPhotoCrop:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "图像": ("IMAGE",),
                "人脸矫正": ("BOOLEAN", {"default": True}),
                "预设尺寸": (SIZE_OPTIONS, {"default": "1寸（2.5 x 3.5 厘米）"}),
                "自定义宽": (
                    "FLOAT",
                    {"default": 0.0, "min": 0.0, "max": 4096.0, "step": 0.01, "round": 0.01},
                ),
                "自定义高": (
                    "FLOAT",
                    {"default": 0.0, "min": 0.0, "max": 4096.0, "step": 0.01, "round": 0.01},
                ),
                "单位": (("厘米", "像素"), {"default": "厘米"}),
                "DPI": ("INT", {"default": 600, "min": 72, "max": 2000, "step": 1}),
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
    FUNCTION = "crop_id_photo"
    CATEGORY = "大汤自制节点/图像"
    DESCRIPTION = "按主要人脸和证件照规格裁剪到精确像素；支持水平矫正、DPI 与边框颜色填充。"

    def crop_id_photo(
        self,
        图像: torch.Tensor,
        人脸矫正: bool,
        预设尺寸: str,
        自定义宽: float,
        自定义高: float,
        单位: str,
        DPI: int,
        脸部大小: float,
        垂直偏移: float,
        尺寸限制: int,
        填充模式: str,
        自定义填充色: str = "#364254",
    ) -> tuple[torch.Tensor, bool, torch.Tensor, int]:
        import torch

        if 图像.ndim != 4 or 图像.shape[-1] < 3:
            raise ValueError("图像必须是 ComfyUI IMAGE 格式")
        if 图像.shape[0] != 1:
            raise ValueError("本节点一次只处理一张照片；批量请交给纳贝队列")
        output_width, output_height, final_dpi = resolve_output_size(
            预设尺寸,
            自定义宽,
            自定义高,
            单位,
            DPI,
        )

        source = 图像[0, ..., :3].to(dtype=torch.float32).clamp(0.0, 1.0)
        detection_source, scale_x, scale_y = _detection_preview(source, int(尺寸限制))
        detection = detect_face(detection_source)
        if detection is None:
            raise ValueError(
                "未检测到人脸，证件照裁剪已停止；请换用正面、清晰且人物占比更大的照片"
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
        crop_width = max(1, int(round(face_width / float(脸部大小))))
        crop_height = max(1, int(round(crop_width * output_height / output_width)))
        crop_x0 = int(round(eye_center[0] - crop_width * 0.5))
        crop_y0 = int(round(eye_center[1] - crop_height * float(垂直偏移)))
        crop_box = (crop_x0, crop_y0, crop_x0 + crop_width, crop_y0 + crop_height)
        cropped, expansion_mask = _crop_with_fill(working, rotation_mask, crop_box, fill_color)
        result, final_mask = _resize_output(
            cropped,
            expansion_mask,
            output_width,
            output_height,
        )
        has_expansion = bool(torch.count_nonzero(final_mask).item())
        return result.unsqueeze(0), has_expansion, final_mask.unsqueeze(0), final_dpi


NODE_CLASS_MAPPINGS = {NODE_ID: DatangQuickIdPhotoCrop}
NODE_DISPLAY_NAME_MAPPINGS = {NODE_ID: "大汤证件照快速裁剪"}
