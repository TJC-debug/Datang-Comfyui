from __future__ import annotations
import importlib.util
import logging
import math
from pathlib import Path
import sys
import numpy as np

_ENGINE = None
_LOG = logging.getLogger(__name__)

def _engine():
    global _ENGINE
    if _ENGINE is None:
        name = "_datang_skin_engine_0459"
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name("skin_retouch_engine.py"))
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        _ENGINE = sys.modules[name]
    return _ENGINE

def _number(value, minimum, maximum, name):
    if isinstance(value, bool):
        raise ValueError(name + "必须为数值。")
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{name}必须在{minimum}～{maximum}之间。")
    return number

def _normalise_masks(mask, image_batch, height, width, device):
    import torch
    import torch.nn.functional as functional
    if mask is None:
        return torch.ones((image_batch, height, width), device=device, dtype=torch.float32)
    masks = mask.detach().to(device=device, dtype=torch.float32)
    if masks.ndim == 2:
        masks = masks.unsqueeze(0)
    elif masks.ndim == 4 and masks.shape[-1] == 1:
        masks = masks[..., 0]
    if masks.ndim != 3 or not torch.isfinite(masks).all():
        raise ValueError("皮肤遮罩必须是有效的ComfyUI标准MASK。")
    if masks.shape[0] == 1 and image_batch > 1:
        masks = masks.expand(image_batch, -1, -1)
    elif masks.shape[0] != image_batch:
        raise ValueError("皮肤遮罩批次数量必须为1，或与图像批次一致。")
    if tuple(masks.shape[-2:]) != (height, width):
        masks = functional.interpolate(masks.unsqueeze(1), size=(height, width), mode="bilinear", align_corners=False).squeeze(1)
    return masks.clamp(0, 1)

class DatangBlemishRetouch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"图像": ("IMAGE",)}, "optional": {
            "皮肤遮罩": ("MASK",),
            "祛痘修补": ("BOOLEAN", {"default": True}),
            "肤质强度": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 1.0, "step": 0.05, "display": "slider"}),
            "修复强度": ("FLOAT", {"default": 85.0, "min": 0.0, "max": 100.0, "step": 1.0, "display": "slider"}),
        }}
    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("精修图像", "痘印遮罩")
    FUNCTION = "retouch"
    CATEGORY = "大汤节点/图像"
    DESCRIPTION = "ModelScope人像局部祛痘与肤质修饰；遮罩可选，连接后限制改动范围。保留Alpha，不做美白或五官形变。"

    def retouch(self, 图像, 皮肤遮罩=None, 修复强度=85.0, 祛痘修补=True, 肤质强度=0.35, **旧参数):
        import torch
        if 图像.ndim != 4 or 图像.shape[-1] not in (3, 4) or min(图像.shape[:3]) <= 0 or not torch.isfinite(图像).all():
            raise ValueError("图像必须为有效的RGB/RGBA IMAGE批次。")
        if not isinstance(祛痘修补, bool):
            raise ValueError("祛痘修补必须为开关值；旧工作流请重新加载以迁移参数。")
        strength = _number(修复强度, 0, 100, "修复强度") / 100
        texture = _number(肤质强度, 0, 1, "肤质强度")
        batch, height, width = 图像.shape[:3]
        masks = _normalise_masks(皮肤遮罩, batch, height, width, 图像.device)
        output_masks = torch.zeros((batch, height, width), device=图像.device, dtype=torch.float32)
        if strength == 0 or (not 祛痘修补 and texture == 0) or not torch.any(masks > 0):
            return 图像, output_masks
        if 旧参数:
            _LOG.warning("旧痘印检测控件已退役；保留修复强度，祛痘与肤质使用新算法参数。请重新保存工作流。")
        result = 图像.clone()
        try:
            with _engine().acquire() as backend:
                for index in range(batch):
                    if not torch.any(masks[index] > 0):
                        continue
                    rgb = np.clip(np.rint(图像[index, ..., :3].detach().cpu().numpy() * 255), 0, 255).astype(np.uint8)
                    repaired, detected, faces = backend.run(rgb, local=祛痘修补, texture=texture)
                    if faces == 0:
                        raise ValueError("未检测到人脸，未执行痘印精修；请使用清晰人像或旁路此节点。")
                    repaired = np.asarray(repaired)
                    detected = np.asarray(detected)
                    if repaired.shape != rgb.shape or detected.shape != rgb.shape[:2] or not np.isfinite(repaired).all() or not np.isfinite(detected).all():
                        raise RuntimeError("痘印精修模型返回了无效图像或检测遮罩。")
                    model_mask = torch.from_numpy(np.ascontiguousarray(detected)).to(device=图像.device, dtype=torch.float32).clamp(0, 1)
                    output_masks[index] = model_mask * masks[index]
                    pixels = torch.from_numpy(np.ascontiguousarray(repaired)).to(device=图像.device, dtype=图像.dtype) / 255
                    blend = masks[index].to(图像.dtype).mul(strength).unsqueeze(-1)
                    mixed = 图像[index, ..., :3] * (1 - blend) + pixels * blend
                    result[index, ..., :3] = torch.where(blend > 0, mixed, 图像[index, ..., :3])
        except torch.cuda.OutOfMemoryError as exc:
            raise RuntimeError("痘印精修显存不足，请释放其他模型或降低单张输入尺寸后重试；未返回伪精修结果。") from exc
        return result, output_masks

NODE_CLASS_MAPPINGS = {"DatangBlemishRetouch": DatangBlemishRetouch}
NODE_DISPLAY_NAME_MAPPINGS = {"DatangBlemishRetouch": "大汤人像痘印精修"}