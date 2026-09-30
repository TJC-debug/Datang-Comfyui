from __future__ import annotations

import cv2
import numpy as np


def _amount(value: float) -> float:
    return float(np.clip(float(value), 0.0, 100.0)) / 100.0


def _active_bounds(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    rows, columns = np.nonzero(mask > 1e-6)
    if rows.size == 0:
        return None
    height, width = mask.shape
    padding = max(8, min(32, int(round(min(height, width) * 0.015))))
    x0 = max(0, int(columns.min()) - padding)
    y0 = max(0, int(rows.min()) - padding)
    x1 = min(width, int(columns.max()) + padding + 1)
    y1 = min(height, int(rows.max()) + padding + 1)
    return x0, y0, x1, y1


def _locally_lift_dark_skin(candidate: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return candidate
    gray = cv2.cvtColor(np.clip(candidate, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gray = gray.astype(np.float32)
    sigma = float(np.clip(min(gray.shape) * 0.018, 3.0, 22.0))
    neighborhood = cv2.GaussianBlur(gray, (0, 0), sigma)
    deficit = np.maximum(neighborhood - gray - 3.0, 0.0)
    dark_weight = np.clip(deficit / 34.0, 0.0, 1.0)
    dark_weight = cv2.GaussianBlur(dark_weight, (0, 0), max(1.0, sigma * 0.32))
    dark_weight *= 0.72 * amount
    lifted = candidate + np.minimum(deficit[..., None] * 0.72, 18.0)
    return candidate * (1.0 - dark_weight[..., None]) + lifted * dark_weight[..., None]


def beautify_rgb(
    rgb: np.ndarray,
    skin_mask: np.ndarray,
    strength: float,
    smoothing: float,
    brightening: float,
    texture: float,
    dark_circle: float,
    blemish: float,
) -> np.ndarray:
    master = _amount(strength)
    effect_amounts = (
        _amount(smoothing),
        _amount(brightening),
        _amount(dark_circle),
        _amount(blemish),
    )
    mask = np.clip(np.asarray(skin_mask, dtype=np.float32), 0.0, 1.0)
    bounds = _active_bounds(mask)
    if master <= 0 or bounds is None or not any(effect_amounts):
        return rgb.copy()

    x0, y0, x1, y1 = bounds
    original = rgb[y0:y1, x0:x1]
    work_mask = mask[y0:y1, x0:x1]
    source = original.astype(np.float32)
    candidate = source.copy()

    smooth_amount = _amount(smoothing)
    if smooth_amount > 0:
        sigma_color = 12.0 + 42.0 * smooth_amount
        sigma_space = 5.0 + 20.0 * smooth_amount
        softened = cv2.bilateralFilter(original, 0, sigma_color, sigma_space).astype(np.float32)
        low_frequency = cv2.GaussianBlur(source, (0, 0), 1.15)
        high_frequency = source - low_frequency
        texture_ratio = _amount(texture)
        softened = np.clip(softened + high_frequency * (0.10 + 0.48 * texture_ratio), 0, 255)
        candidate = source * (1.0 - 0.78 * smooth_amount) + softened * (0.78 * smooth_amount)

    white_amount = _amount(brightening)
    if white_amount > 0:
        lab = cv2.cvtColor(
            np.clip(candidate, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB
        ).astype(np.float32)
        lab[..., 0] += (255.0 - lab[..., 0]) * (0.115 * white_amount)
        lab[..., 1:] = 128.0 + (lab[..., 1:] - 128.0) * (1.0 - 0.055 * white_amount)
        candidate = cv2.cvtColor(
            np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB
        ).astype(np.float32)

    blemish_amount = _amount(blemish)
    if blemish_amount > 0:
        repaired = cv2.medianBlur(np.clip(candidate, 0, 255).astype(np.uint8), 5).astype(
            np.float32
        )
        gray = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY).astype(np.float32)
        edge_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        edge_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        edge_guard = 1.0 - np.clip(cv2.magnitude(edge_x, edge_y) / 95.0, 0.0, 1.0)
        repair_weight = edge_guard * (0.52 * blemish_amount)
        candidate = candidate * (1.0 - repair_weight[..., None]) + repaired * repair_weight[
            ..., None
        ]

    candidate = _locally_lift_dark_skin(candidate, _amount(dark_circle))

    blend = np.clip(work_mask * master, 0.0, 1.0)[..., None]
    combined = source * (1.0 - blend) + candidate * blend
    output = rgb.copy()
    output[y0:y1, x0:x1] = np.clip(np.rint(combined), 0, 255).astype(np.uint8)
    return output


def _normalise_masks(mask, image_batch: int, height: int, width: int):
    import torch
    import torch.nn.functional as functional

    masks = mask.detach().to(dtype=torch.float32)
    if masks.ndim == 2:
        masks = masks.unsqueeze(0)
    elif masks.ndim == 4 and masks.shape[-1] == 1:
        masks = masks[..., 0]
    if masks.ndim != 3:
        raise ValueError("皮肤遮罩必须是 ComfyUI 标准 MASK。")
    if masks.shape[0] == 1 and image_batch > 1:
        masks = masks.expand(image_batch, -1, -1)
    elif masks.shape[0] != image_batch:
        raise ValueError("皮肤遮罩批次数量必须为 1，或与图像批次数量一致。")
    if tuple(masks.shape[-2:]) != (height, width):
        masks = functional.interpolate(
            masks.unsqueeze(1), size=(height, width), mode="bilinear", align_corners=False
        ).squeeze(1)
    return masks.clamp(0.0, 1.0)


class DatangFastFaceBeauty:
    @classmethod
    def INPUT_TYPES(cls):
        slider = {"default": 0.0, "min": 0.0, "max": 100.0, "step": 1.0, "display": "slider"}
        return {
            "required": {
                "图像": ("IMAGE",),
                "皮肤遮罩": ("MASK",),
                "美颜强度": ("FLOAT", {**slider, "default": 60.0}),
                "磨皮": ("FLOAT", {**slider, "default": 45.0}),
                "美白提亮": ("FLOAT", {**slider, "default": 18.0}),
                "纹理保留": ("FLOAT", {**slider, "default": 70.0}),
                "黑眼圈淡化": ("FLOAT", {**slider, "default": 30.0}),
                "瑕疵皱纹淡化": ("FLOAT", {**slider, "default": 25.0}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像",)
    FUNCTION = "beautify"
    CATEGORY = "大汤节点/图像"
    DESCRIPTION = "严格按外部皮肤遮罩执行传统图像美颜；不做人脸识别，不改变画布尺寸。"

    def beautify(
        self,
        图像,
        皮肤遮罩,
        美颜强度,
        磨皮,
        美白提亮,
        纹理保留,
        黑眼圈淡化,
        瑕疵皱纹淡化,
    ):
        import torch

        if float(美颜强度) <= 0 or not any(
            float(value) > 0
            for value in (磨皮, 美白提亮, 黑眼圈淡化, 瑕疵皱纹淡化)
        ):
            return (图像,)
        image_batch, height, width = 图像.shape[:3]
        masks = _normalise_masks(皮肤遮罩, image_batch, height, width)
        if not torch.any(masks > 0):
            return (图像,)

        output_images = []
        cpu_masks = masks.detach().cpu().numpy()
        for index, image in enumerate(图像):
            pixels = image.detach().cpu().numpy()
            channels = pixels.shape[-1]
            rgb = np.clip(np.rint(pixels[..., :3] * 255.0), 0, 255).astype(np.uint8)
            mask = cpu_masks[index]
            processed = beautify_rgb(
                rgb,
                mask,
                美颜强度,
                磨皮,
                美白提亮,
                纹理保留,
                黑眼圈淡化,
                瑕疵皱纹淡化,
            ).astype(np.float32) / 255.0
            result = pixels.copy()
            result[..., :3] = np.where(
                (mask > 0)[..., None], processed, pixels[..., :3]
            )
            if channels > 3:
                result[..., 3:] = pixels[..., 3:]
            output_images.append(torch.from_numpy(result))
        stacked = torch.stack(output_images).to(device=图像.device, dtype=图像.dtype)
        return (stacked,)


NODE_CLASS_MAPPINGS = {"DatangFastFaceBeauty": DatangFastFaceBeauty}
NODE_DISPLAY_NAME_MAPPINGS = {"DatangFastFaceBeauty": "大汤人像快速美颜"}
