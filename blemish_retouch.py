from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def _amount(value: float) -> float:
    return float(np.clip(float(value), 0.0, 100.0)) / 100.0


def detect_blemishes(
    rgb: np.ndarray,
    skin_mask: np.ndarray,
    sensitivity: float,
    maximum_size: int,
    dark_spots: float,
    red_marks: float,
    structure_protection: float = 75.0,
) -> np.ndarray:
    """Return a conservative blemish mask inside an externally supplied skin mask."""
    mask = np.clip(np.asarray(skin_mask, dtype=np.float32), 0.0, 1.0)
    if not np.any(mask > 1e-6):
        return np.zeros(mask.shape, dtype=np.float32)

    maximum_size = int(np.clip(int(maximum_size), 3, 160))
    sensitivity_ratio = _amount(sensitivity)
    lab = cv2.cvtColor(np.asarray(rgb, dtype=np.uint8), cv2.COLOR_RGB2LAB).astype(
        np.float32
    )
    sigma = float(np.clip(maximum_size * 0.32, 2.5, 18.0))
    local = cv2.GaussianBlur(lab, (0, 0), sigma)

    dark_delta = local[..., 0] - lab[..., 0]
    red_delta = lab[..., 1] - local[..., 1]
    dark_threshold = 13.0 - 7.5 * sensitivity_ratio
    red_threshold = 8.0 - 4.5 * sensitivity_ratio
    dark_score = np.clip((dark_delta - dark_threshold) / 18.0, 0.0, 1.0)
    red_score = np.clip((red_delta - red_threshold) / 13.0, 0.0, 1.0)
    score = np.maximum(
        dark_score * _amount(dark_spots), red_score * _amount(red_marks)
    )

    luminance = lab[..., 0]
    gradient_x = cv2.Sobel(luminance, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(luminance, cv2.CV_32F, 0, 1, ksize=3)
    gradient = cv2.magnitude(gradient_x, gradient_y)
    edge_guard = 1.0 - np.clip((gradient - 28.0) / 78.0, 0.0, 1.0)

    skin_binary = (mask >= 0.12).astype(np.uint8)
    protection_ratio = _amount(structure_protection)
    distance_to_mask_edge = cv2.distanceTransform(skin_binary, cv2.DIST_L2, 5)
    protected_radius = max(
        1.0,
        protection_ratio
        * (maximum_size * 0.30 + min(mask.shape) * 0.012),
    )
    mask_edge_guard = np.clip(
        (distance_to_mask_edge - protected_radius) / max(2.0, protected_radius * 0.45),
        0.0,
        1.0,
    )

    strong_edges = ((gradient >= (72.0 - 18.0 * protection_ratio)) * skin_binary).astype(
        np.uint8
    )
    strong_edges = cv2.morphologyEx(
        strong_edges,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )
    edge_count, edge_labels, edge_stats, _ = cv2.connectedComponentsWithStats(
        strong_edges, 8
    )
    structural_regions = np.zeros(mask.shape, dtype=np.uint8)
    minimum_span = max(10, int(round(maximum_size * 0.48)))
    for label in range(1, edge_count):
        _, _, width, height, area = edge_stats[label]
        aspect = max(width, height) / max(1, min(width, height))
        if max(width, height) >= minimum_span and (area >= 8 or aspect >= 2.2):
            structural_regions[edge_labels == label] = 1
    if protection_ratio > 0 and np.any(structural_regions):
        structure_radius = max(
            1, int(round(protection_ratio * (2.0 + min(mask.shape) * 0.006)))
        )
        structural_regions = cv2.dilate(
            structural_regions,
            cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (structure_radius * 2 + 1, structure_radius * 2 + 1)
            ),
            iterations=1,
        )
    structure_guard = 1.0 - structural_regions.astype(np.float32) * protection_ratio

    raw = (
        (score * edge_guard * mask_edge_guard * structure_guard) >= 0.12
    ).astype(np.uint8) * skin_binary
    raw = cv2.morphologyEx(
        raw,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )

    count, labels, statistics, _ = cv2.connectedComponentsWithStats(raw, 8)
    accepted = np.zeros(raw.shape, dtype=np.uint8)
    maximum_area = max(9, int(round(np.pi * (maximum_size * 0.5) ** 2)))
    for label in range(1, count):
        x, y, width, height, area = statistics[label]
        if area < 2 or area > maximum_area:
            continue
        if width > maximum_size or height > maximum_size:
            continue
        aspect = max(width, height) / max(1, min(width, height))
        if aspect > 3.6:
            continue
        accepted[labels == label] = 1

    if not np.any(accepted):
        return np.zeros(mask.shape, dtype=np.float32)
    expansion = max(1, min(4, int(round(maximum_size * 0.08))))
    expanded = cv2.dilate(
        accepted,
        cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (expansion * 2 + 1, expansion * 2 + 1)
        ),
        iterations=1,
    )
    return expanded.astype(np.float32) * mask


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


def _find_lama_model() -> Path:
    candidates: list[Path] = []
    try:
        import folder_paths

        base_path = Path(folder_paths.base_path)
        candidates.extend(
            [
                Path(folder_paths.models_dir) / "inpaint" / "big-lama.pt",
                base_path
                / "custom_nodes"
                / "comfyui-lama-remover"
                / "ckpts"
                / "big-lama.pt",
            ]
        )
    except ImportError:
        pass
    candidates.append(
        Path(__file__).resolve().parent.parent
        / "comfyui-lama-remover"
        / "ckpts"
        / "big-lama.pt"
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "未找到 big-lama.pt。请安装 comfyui-lama-remover，或把模型放到 "
        "ComfyUI/models/inpaint/big-lama.pt；节点不会自动联网下载模型。"
    )


def _run_lama(images, masks):
    import torch
    import torch.nn.functional as functional

    try:
        from comfy.model_management import get_torch_device

        device = get_torch_device()
    except ImportError:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = torch.jit.load(str(_find_lama_model()), map_location=device)
    model.eval().to(device)
    batch = images[..., :3].permute(0, 3, 1, 2).to(device=device, dtype=torch.float32)
    repair_masks = masks.unsqueeze(1).to(device=device, dtype=torch.float32)
    height, width = batch.shape[-2:]
    padding_bottom = (-height) % 8
    padding_right = (-width) % 8
    if padding_bottom or padding_right:
        batch = functional.pad(batch, (0, padding_right, 0, padding_bottom), mode="replicate")
        repair_masks = functional.pad(
            repair_masks, (0, padding_right, 0, padding_bottom), mode="constant", value=0
        )
    with torch.inference_mode():
        result = model(batch, (repair_masks > 0.01).to(dtype=torch.float32))
        if isinstance(result, (tuple, list)):
            result = result[0]
    return result[..., :height, :width].permute(0, 2, 3, 1).to(images.device)


def _feather_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return np.clip(mask, 0.0, 1.0)
    return np.clip(
        cv2.GaussianBlur(mask.astype(np.float32), (0, 0), max(0.5, radius * 0.55)),
        0.0,
        1.0,
    )


class DatangBlemishRetouch:
    @classmethod
    def INPUT_TYPES(cls):
        slider = {
            "default": 0.0,
            "min": 0.0,
            "max": 100.0,
            "step": 1.0,
            "display": "slider",
        }
        return {
            "required": {
                "图像": ("IMAGE",),
                "皮肤遮罩": ("MASK",),
                "修复强度": ("FLOAT", {**slider, "default": 85.0}),
                "检测灵敏度": ("FLOAT", {**slider, "default": 58.0}),
                "最大瑕疵尺寸": (
                    "INT",
                    {"default": 36, "min": 3, "max": 160, "step": 1, "display": "slider"},
                ),
                "深色斑点修复": ("FLOAT", {**slider, "default": 85.0}),
                "红印修复": ("FLOAT", {**slider, "default": 70.0}),
                "五官边缘保护": ("FLOAT", {**slider, "default": 78.0}),
                "边缘羽化": (
                    "INT",
                    {"default": 6, "min": 0, "max": 30, "step": 1, "display": "slider"},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("精修图像", "痘印遮罩")
    FUNCTION = "retouch"
    CATEGORY = "大汤节点/图像"
    DESCRIPTION = (
        "仅在外部皮肤遮罩内检测局部痘印，并复用本机 Big LaMa 进行精修；"
        "第二输出用于检查实际修复范围。"
    )

    def retouch(
        self,
        图像,
        皮肤遮罩,
        修复强度,
        检测灵敏度,
        最大瑕疵尺寸,
        深色斑点修复,
        红印修复,
        五官边缘保护,
        边缘羽化,
    ):
        import torch

        image_batch, height, width = 图像.shape[:3]
        masks = _normalise_masks(皮肤遮罩, image_batch, height, width)
        output_masks = []
        cpu_masks = masks.detach().cpu().numpy()
        for index, image in enumerate(图像):
            pixels = image.detach().cpu().numpy()
            rgb = np.clip(np.rint(pixels[..., :3] * 255.0), 0, 255).astype(np.uint8)
            output_masks.append(
                torch.from_numpy(
                    detect_blemishes(
                        rgb,
                        cpu_masks[index],
                        检测灵敏度,
                        最大瑕疵尺寸,
                        深色斑点修复,
                        红印修复,
                        五官边缘保护,
                    )
                )
            )
        blemish_masks = torch.stack(output_masks).to(
            device=图像.device, dtype=torch.float32
        )
        if float(修复强度) <= 0 or not torch.any(blemish_masks > 0):
            return (图像, blemish_masks)

        repaired = _run_lama(图像, blemish_masks)
        blend_masks = []
        for index, mask in enumerate(blemish_masks.detach().cpu().numpy()):
            feathered = _feather_mask(mask, int(边缘羽化)) * cpu_masks[index]
            blend_masks.append(torch.from_numpy(feathered))
        blend = (
            torch.stack(blend_masks)
            .to(device=图像.device, dtype=图像.dtype)
            .mul(_amount(修复强度))
            .clamp(0.0, 1.0)
            .unsqueeze(-1)
        )
        result = 图像.clone()
        result[..., :3] = 图像[..., :3] * (1.0 - blend) + repaired[..., :3].to(
            dtype=图像.dtype
        ) * blend
        return (result, blemish_masks)


NODE_CLASS_MAPPINGS = {"DatangBlemishRetouch": DatangBlemishRetouch}
NODE_DISPLAY_NAME_MAPPINGS = {"DatangBlemishRetouch": "大汤人像痘印精修"}
