from __future__ import annotations

# Integrated from ComfyUI-NabeiPortraitComposition-V1.
# Copyright 2026 Nabei AI. Licensed under Apache License 2.0;
# see LICENSE-NabeiPortraitComposition and THIRD_PARTY_NOTICES.md.

import json
import threading
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


NODE_ID = "NabeiPortraitComposition"
MAX_CROP_SIDE = 8192
MAX_CROP_PIXELS = 24_000_000
MAX_SOURCE_EXPANSION = 2

ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "1:1 正方形": (1, 1),
    "3:4 常用证件照": (3, 4),
    "4:5 竖版证件照": (4, 5),
    "2:3 标准竖版": (2, 3),
}

FRAMING_PRESETS: dict[str, dict[str, float]] = {
    "头像照（头部约56%）": {"head_ratio": 0.56, "top_ratio": 0.065},
    "标准证件照（头部约46%）": {"head_ratio": 0.46, "top_ratio": 0.080},
    "胸部证件照（头部约36%）": {"head_ratio": 0.36, "top_ratio": 0.080},
    "半身证件照（头部约26%）": {"head_ratio": 0.26, "top_ratio": 0.080},
}

_DETECTOR: Any | None = None
_DETECTOR_LOCK = threading.Lock()


@dataclass(frozen=True)
class FaceDetection:
    bbox: tuple[float, float, float, float]
    confidence: float
    landmarks: tuple[float, ...] | None
    detector: str
    face_count: int
    warnings: tuple[str, ...] = ()


def _get_mtcnn() -> Any:
    global _DETECTOR
    if _DETECTOR is None:
        with _DETECTOR_LOCK:
            if _DETECTOR is None:
                from mtcnnruntime import MTCNN

                _DETECTOR = MTCNN()
    return _DETECTOR


def _as_rgb8(image: torch.Tensor) -> np.ndarray:
    import torch

    array = image.detach().to(device="cpu", dtype=torch.float32).clamp(0.0, 1.0).numpy()
    return np.rint(array[..., :3] * 255.0).astype(np.uint8)


def _detect_with_mtcnn(rgb: np.ndarray) -> FaceDetection | None:
    detector = _get_mtcnn()
    faces, landmarks = detector.detect(rgb)
    if faces is None or len(faces) == 0:
        return None

    candidates: list[tuple[float, int, np.ndarray]] = []
    for index, face in enumerate(np.asarray(faces)):
        if len(face) < 4:
            continue
        x0, y0, x1, y1 = [float(v) for v in face[:4]]
        confidence = float(face[4]) if len(face) > 4 else 1.0
        area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
        if confidence >= 0.70 and area > 1.0:
            candidates.append((area, index, face))
    if not candidates:
        return None

    candidates.sort(reverse=True, key=lambda item: item[0])
    _, index, face = candidates[0]
    x0, y0, x1, y1 = [float(v) for v in face[:4]]
    confidence = float(face[4]) if len(face) > 4 else 1.0
    selected_landmarks: tuple[float, ...] | None = None
    if landmarks is not None and index < len(landmarks):
        selected_landmarks = tuple(float(v) for v in np.asarray(landmarks[index]).reshape(-1))
    warnings: list[str] = []
    if len(candidates) > 1:
        warnings.append(f"检测到{len(candidates)}张人脸，已按单人照片规则选择面积最大的人脸")
    return FaceDetection(
        bbox=(x0, y0, x1, y1),
        confidence=confidence,
        landmarks=selected_landmarks,
        detector="mtcnn-runtime",
        face_count=len(candidates),
        warnings=tuple(warnings),
    )


def _detect_with_opencv(rgb: np.ndarray) -> FaceDetection | None:
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(32, 32))
    if faces is None or len(faces) == 0:
        return None
    faces = sorted(faces, key=lambda item: int(item[2]) * int(item[3]), reverse=True)
    x, y, width, height = [float(v) for v in faces[0]]
    warnings = ["MTCNN不可用，已回退到OpenCV基础检测"]
    if len(faces) > 1:
        warnings.append(f"检测到{len(faces)}张人脸，已选择面积最大的人脸")
    return FaceDetection(
        bbox=(x, y, x + width, y + height),
        confidence=1.0,
        landmarks=None,
        detector="opencv-haar",
        face_count=len(faces),
        warnings=tuple(warnings),
    )


def detect_face(image: torch.Tensor) -> FaceDetection | None:
    rgb = _as_rgb8(image)
    try:
        detected = _detect_with_mtcnn(rgb)
        if detected is not None:
            return detected
    except Exception:
        pass
    return _detect_with_opencv(rgb)


def estimate_head_box(
    detection: FaceDetection,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = detection.bbox
    face_width = max(1.0, x1 - x0)
    face_height = max(1.0, y1 - y0)

    # MTCNN detects the anatomical face rather than the hair silhouette. These
    # margins convert it to a stable hair-top-to-chin proxy without modifying
    # the person's pose or pixels.
    head_x0 = x0 - face_width * 0.17
    head_x1 = x1 + face_width * 0.17
    head_y0 = y0 - face_height * 0.38
    head_y1 = y1 + face_height * 0.04
    return (
        max(0.0, head_x0),
        max(0.0, head_y0),
        min(float(image_width), head_x1),
        min(float(image_height), head_y1),
    )


def _aspect_crop_size(
    input_width: int,
    input_height: int,
    aspect_ratio: str,
    requested_unit: int | None = None,
) -> tuple[int, int, int]:
    ratio_width, ratio_height = ASPECT_RATIOS[aspect_ratio]
    max_unit = min(input_width // ratio_width, input_height // ratio_height)
    if max_unit < 1:
        raise ValueError(f"输入图片尺寸过小，无法按 {aspect_ratio} 裁剪")
    unit = max_unit if requested_unit is None else min(max(1, int(requested_unit)), max_unit)
    return ratio_width * unit, ratio_height * unit, max_unit


def compute_crop_box(
    head_box: tuple[float, float, float, float],
    input_width: int,
    input_height: int,
    aspect_ratio: str,
    framing: str,
    head_size_adjust: float,
    vertical_adjust: float,
    horizontal_adjust: float,
) -> tuple[tuple[int, int, int, int], dict[str, float], dict[str, bool]]:
    preset = FRAMING_PRESETS[framing]
    head_x0, head_y0, head_x1, head_y1 = head_box
    head_width = max(1.0, head_x1 - head_x0)
    head_height = max(1.0, head_y1 - head_y0)
    target_head_ratio = preset["head_ratio"] * float(head_size_adjust)
    target_head_top_ratio = preset["top_ratio"] + float(vertical_adjust)
    target_head_center_x_ratio = 0.5 + float(horizontal_adjust)
    ratio_width, ratio_height = ASPECT_RATIOS[aspect_ratio]
    ideal_crop_height = head_height / max(target_head_ratio, 0.01)
    ideal_unit = max(1, int(round(ideal_crop_height / ratio_height)))
    minimum_head_unit = max(
        1,
        int(np.ceil(head_width / ratio_width)),
        int(np.ceil(head_height / ratio_height)),
    )
    requested_unit = max(ideal_unit, minimum_head_unit)
    maximum_safe_unit = max(
        1,
        min(
            max(1, input_width * MAX_SOURCE_EXPANSION // ratio_width),
            max(1, input_height * MAX_SOURCE_EXPANSION // ratio_height),
            max(1, MAX_CROP_SIDE // ratio_width),
            max(1, MAX_CROP_SIDE // ratio_height),
            max(1, int(np.sqrt(MAX_CROP_PIXELS / (ratio_width * ratio_height)))),
        ),
    )
    crop_unit = min(requested_unit, maximum_safe_unit)
    crop_width = ratio_width * crop_unit
    crop_height = ratio_height * crop_unit

    source_head_center_x = (head_x0 + head_x1) * 0.5
    desired_x0 = source_head_center_x - target_head_center_x_ratio * crop_width
    desired_y0 = head_y0 - target_head_top_ratio * crop_height
    crop_x0 = int(round(desired_x0))
    crop_y0 = int(round(desired_y0))
    crop_box = (crop_x0, crop_y0, crop_x0 + crop_width, crop_y0 + crop_height)
    target = {
        "head_ratio": target_head_ratio,
        "head_top_ratio": target_head_top_ratio,
        "head_center_x_ratio": target_head_center_x_ratio,
    }
    limits = {
        "framing_limited": minimum_head_unit > ideal_unit,
        "safety_limited": requested_unit > maximum_safe_unit,
        "fill_required": (
            crop_box[0] < 0
            or crop_box[1] < 0
            or crop_box[2] > input_width
            or crop_box[3] > input_height
        ),
    }
    return crop_box, target, limits


def estimate_border_color(image: torch.Tensor) -> torch.Tensor:
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


def crop_image(
    image: torch.Tensor,
    crop_box: tuple[int, int, int, int],
    fill_color: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    crop_x0, crop_y0, crop_x1, crop_y1 = crop_box
    crop_width = crop_x1 - crop_x0
    crop_height = crop_y1 - crop_y0
    if crop_width < 1 or crop_height < 1:
        raise ValueError("裁剪区域尺寸无效")
    border_color = estimate_border_color(image) if fill_color is None else fill_color
    result = border_color.reshape(1, 1, 3).expand(crop_height, crop_width, 3).clone()
    fill_mask = image.new_ones((crop_height, crop_width))

    source_x0 = max(0, crop_x0)
    source_y0 = max(0, crop_y0)
    source_x1 = min(int(image.shape[1]), crop_x1)
    source_y1 = min(int(image.shape[0]), crop_y1)
    if source_x1 > source_x0 and source_y1 > source_y0:
        destination_x0 = source_x0 - crop_x0
        destination_y0 = source_y0 - crop_y0
        destination_x1 = destination_x0 + source_x1 - source_x0
        destination_y1 = destination_y0 + source_y1 - source_y0
        result[destination_y0:destination_y1, destination_x0:destination_x1] = image[
            source_y0:source_y1, source_x0:source_x1, :3
        ]
        fill_mask[destination_y0:destination_y1, destination_x0:destination_x1] = 0.0
    return result, fill_mask


def _draw_hline(image: torch.Tensor, y: int, color: tuple[float, float, float], thickness: int = 3) -> None:
    height, width = image.shape[:2]
    y0 = max(0, y - thickness // 2)
    y1 = min(height, y0 + thickness)
    image[y0:y1, :width] = image.new_tensor(color)


def _draw_vline(image: torch.Tensor, x: int, color: tuple[float, float, float], thickness: int = 3) -> None:
    height, width = image.shape[:2]
    x0 = max(0, x - thickness // 2)
    x1 = min(width, x0 + thickness)
    image[:height, x0:x1] = image.new_tensor(color)


def _draw_rect(
    image: torch.Tensor,
    box: tuple[float, float, float, float],
    color: tuple[float, float, float],
    thickness: int = 3,
) -> None:
    height, width = image.shape[:2]
    x0, y0, x1, y1 = [int(round(value)) for value in box]
    x0, x1 = max(0, min(width - 1, x0)), max(0, min(width - 1, x1))
    y0, y1 = max(0, min(height - 1, y0)), max(0, min(height - 1, y1))
    if x1 <= x0 or y1 <= y0:
        return
    image[y0 : min(height, y0 + thickness), x0:x1] = image.new_tensor(color)
    image[max(0, y1 - thickness) : y1, x0:x1] = image.new_tensor(color)
    image[y0:y1, x0 : min(width, x0 + thickness)] = image.new_tensor(color)
    image[y0:y1, max(0, x1 - thickness) : x1] = image.new_tensor(color)


def make_preview(
    result: torch.Tensor,
    transformed_head_box: tuple[float, float, float, float] | None,
    target: dict[str, float],
    needs_review: bool,
) -> torch.Tensor:
    preview = result.clone()
    height, width = preview.shape[:2]
    border_color = (1.0, 0.05, 0.05) if needs_review else (0.1, 1.0, 0.2)
    _draw_rect(preview, (1, 1, width - 1, height - 1), border_color, max(3, min(width, height) // 240))
    _draw_vline(preview, int(round(target["head_center_x_ratio"] * width)), (1.0, 0.82, 0.0), 3)
    _draw_hline(preview, int(round(target["head_top_ratio"] * height)), (0.1, 0.75, 1.0), 3)
    if transformed_head_box is not None:
        _draw_rect(preview, transformed_head_box, (1.0, 0.1, 0.85), 4)
    return preview.clamp(0.0, 1.0)


def _fallback_crop(
    image: torch.Tensor,
    aspect_ratio: str,
) -> tuple[torch.Tensor, torch.Tensor, tuple[int, int, int, int]]:
    input_height, input_width = image.shape[:2]
    crop_width, crop_height, _ = _aspect_crop_size(input_width, input_height, aspect_ratio)
    crop_x0 = (input_width - crop_width) // 2
    crop_y0 = (input_height - crop_height) // 2
    crop_box = (crop_x0, crop_y0, crop_x0 + crop_width, crop_y0 + crop_height)
    result, mask = crop_image(image, crop_box)
    return result, mask, crop_box


class DatangPortraitCrop:
    @classmethod
    def INPUT_TYPES(cls) -> dict[str, Any]:
        return {
            "required": {
                "人物照片": ("IMAGE",),
                "画布比例": (tuple(ASPECT_RATIOS.keys()), {"default": "3:4 常用证件照"}),
                "人像构图": (tuple(FRAMING_PRESETS.keys()), {"default": "标准证件照（头部约46%）"}),
                "头部大小微调": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.70, "max": 1.30, "step": 0.01, "round": 0.001},
                ),
                "人物上下微调": (
                    "FLOAT",
                    {"default": 0.0, "min": -0.20, "max": 0.20, "step": 0.005, "round": 0.001},
                ),
                "人物左右微调": (
                    "FLOAT",
                    {"default": 0.0, "min": -0.20, "max": 0.20, "step": 0.005, "round": 0.001},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("裁剪结果", "裁剪预览", "填充区域遮罩", "状态信息")
    FUNCTION = "compose"
    CATEGORY = "大汤自制节点/图像"
    DESCRIPTION = "根据头部位置从原图直接裁剪目标比例；不缩放、不拉伸，超出原图时使用边框颜色填充。"

    def compose(
        self,
        人物照片: torch.Tensor,
        画布比例: str,
        人像构图: str,
        头部大小微调: float,
        人物上下微调: float,
        人物左右微调: float,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, str]:
        import torch

        if 人物照片.ndim != 4 or 人物照片.shape[-1] < 3:
            raise ValueError("人物照片必须是 ComfyUI IMAGE 格式")
        if 人物照片.shape[0] != 1:
            raise ValueError("本节点一次只处理一张照片；批量循环请交给纳贝执行")
        if 画布比例 not in ASPECT_RATIOS:
            raise ValueError(f"不支持的画布比例：{画布比例}")
        if 人像构图 not in FRAMING_PRESETS:
            raise ValueError(f"不支持的人像构图：{人像构图}")

        source = 人物照片[0, ..., :3].to(dtype=torch.float32).clamp(0.0, 1.0)
        input_height, input_width = [int(v) for v in source.shape[:2]]
        border_color = estimate_border_color(source)
        detection = detect_face(source)

        failed = detection is None
        if failed:
            result, fill_mask, crop_box = _fallback_crop(source, 画布比例)
            target = {
                "head_ratio": FRAMING_PRESETS[人像构图]["head_ratio"] * float(头部大小微调),
                "head_top_ratio": FRAMING_PRESETS[人像构图]["top_ratio"] + float(人物上下微调),
                "head_center_x_ratio": 0.5 + float(人物左右微调),
            }
            transformed_head_box = None
            status: dict[str, Any] = {
                "schema": "datang.portrait_crop.v1",
                "success": False,
                "needs_review": True,
                "message": "未检测到人脸，已按画布比例居中裁剪原图，未执行头部定位",
                "canvas_ratio": 画布比例,
                "framing": 人像构图,
                "input_size": [input_width, input_height],
                "output_size": [int(result.shape[1]), int(result.shape[0])],
                "crop_box": list(crop_box),
                "resampled": False,
                "fill_color": [round(float(value), 6) for value in border_color.tolist()],
                "filled_pixels": 0,
            }
        else:
            head_box = estimate_head_box(detection, input_width, input_height)
            crop_box, target, limits = compute_crop_box(
                head_box,
                input_width,
                input_height,
                画布比例,
                人像构图,
                头部大小微调,
                人物上下微调,
                人物左右微调,
            )
            result, fill_mask = crop_image(source, crop_box, border_color)
            crop_x0, crop_y0, _, _ = crop_box
            transformed_head_box = (
                head_box[0] - crop_x0,
                head_box[1] - crop_y0,
                head_box[2] - crop_x0,
                head_box[3] - crop_y0,
            )
            output_height, output_width = [int(value) for value in result.shape[:2]]
            actual_head_ratio = max(0.0, transformed_head_box[3] - transformed_head_box[1]) / output_height
            actual_head_top_ratio = transformed_head_box[1] / output_height
            needs_review = (
                detection.face_count != 1
                or limits["framing_limited"]
                or limits["safety_limited"]
            )
            if detection.face_count != 1:
                message = "裁剪完成，但检测到多张人脸，请复核"
            elif limits["safety_limited"]:
                message = "裁剪完成，但为防止异常大画布已限制输出尺寸，请复核"
            elif limits["framing_limited"]:
                message = "裁剪完成，但为保留完整头部已放宽目标头部占比，请复核"
            elif limits["fill_required"]:
                message = "裁剪完成，超出原图区域已使用边框颜色填充"
            else:
                message = "裁剪完成"
            status = {
                "schema": "datang.portrait_crop.v1",
                "success": True,
                "needs_review": needs_review,
                "message": message,
                "canvas_ratio": 画布比例,
                "framing": 人像构图,
                "input_size": [input_width, input_height],
                "output_size": [output_width, output_height],
                "crop_box": list(crop_box),
                "resampled": False,
                "fill_color": [round(float(value), 6) for value in border_color.tolist()],
                "filled_pixels": int(torch.count_nonzero(fill_mask).item()),
                "detector": detection.detector,
                "face_count": detection.face_count,
                "confidence": round(detection.confidence, 6),
                "face_bbox": [round(value, 3) for value in detection.bbox],
                "estimated_head_bbox": [round(value, 3) for value in head_box],
                "target_head_ratio": round(target["head_ratio"], 6),
                "actual_head_ratio": round(actual_head_ratio, 6),
                "target_head_top_ratio": round(target["head_top_ratio"], 6),
                "actual_head_top_ratio": round(actual_head_top_ratio, 6),
                "target_head_center_x_ratio": round(target["head_center_x_ratio"], 6),
                "limits": limits,
                "warnings": list(detection.warnings),
            }

        preview = make_preview(result, transformed_head_box, target, bool(status["needs_review"]))
        return (
            result.unsqueeze(0),
            preview.unsqueeze(0),
            fill_mask.unsqueeze(0),
            json.dumps(status, ensure_ascii=False, separators=(",", ":")),
        )


NODE_CLASS_MAPPINGS = {NODE_ID: DatangPortraitCrop}
NODE_DISPLAY_NAME_MAPPINGS = {NODE_ID: "大汤人物定比裁剪"}
