import json
import os
import re


STAGE_RESULT_ROOT = "datang-stage-result-v1"


def sanitize_stage_name(value):
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", str(value or ""))
    safe = re.sub(r"\s+", " ", safe).strip().rstrip(". ")[:60].rstrip(". ")
    if not safe or safe in {".", ".."}:
        safe = "阶段结果"
    if re.match(r"^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$", safe, re.I):
        safe = f"_{safe}"
    return safe


def build_stage_folder(stage_order, stage_name):
    order = max(1, min(999, int(stage_order)))
    return f"{STAGE_RESULT_ROOT}/{order:02d}_{sanitize_stage_name(stage_name)}"


def normalize_optional_dpi(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("输入 DPI 必须是 72 到 1200 的整数。")
    dpi = int(value)
    if dpi != value or not 72 <= dpi <= 1200:
        raise ValueError("输入 DPI 必须是 72 到 1200 的整数。")
    return dpi


def normalize_save_enabled(value):
    if value is None:
        return True
    if not isinstance(value, bool):
        raise ValueError("是否保存必须是布尔值。")
    return value


class DatangStageResultSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图片": ("IMAGE", {"lazy": True}),
                "阶段序号": ("INT", {"default": 1, "min": 1, "max": 999, "step": 1}),
                "阶段名称": ("STRING", {"default": "阶段结果", "multiline": False}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
            "optional": {
                "输入DPI": (
                    "INT",
                    {
                        "forceInput": True,
                        "tooltip": "可连接裁剪尺寸或排版节点输出的 DPI；连接后写入阶段 PNG 元数据。",
                    },
                ),
                "是否保存": (
                    "BOOLEAN",
                    {
                        "forceInput": True,
                        "tooltip": "连接对应阶段开关；关闭时不读取图片、不运行上游支路，也不生成阶段结果。",
                    },
                ),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_stage_images"
    OUTPUT_NODE = True
    CATEGORY = "大汤节点/图像"
    DESCRIPTION = "保存真实阶段结果；可按阶段开关跳过执行，可选写入 DPI，并让纳贝批量处理按阶段目录归档。"

    def check_lazy_status(
        self,
        图片,
        阶段序号=1,
        阶段名称="阶段结果",
        prompt=None,
        extra_pnginfo=None,
        是否保存=None,
        输入DPI=None,
    ):
        if not normalize_save_enabled(是否保存):
            return []
        if 图片 is None:
            return ["图片"]
        return []

    def save_stage_images(
        self,
        图片,
        阶段序号=1,
        阶段名称="阶段结果",
        prompt=None,
        extra_pnginfo=None,
        是否保存=None,
        输入DPI=None,
    ):
        if not normalize_save_enabled(是否保存):
            return {"ui": {"images": []}}

        import folder_paths
        import numpy as np
        from comfy.cli_args import args
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo

        if len(图片) == 0:
            raise ValueError("大汤阶段结果保存没有收到图片。")
        dpi = normalize_optional_dpi(输入DPI)

        output_dir = folder_paths.get_output_directory()
        stage_folder = build_stage_folder(阶段序号, 阶段名称)
        filename_prefix = f"{stage_folder}/result"
        full_output_folder, filename, counter, subfolder, _ = (
            folder_paths.get_save_image_path(
                filename_prefix,
                output_dir,
                图片[0].shape[1],
                图片[0].shape[0],
            )
        )
        results = []
        for batch_number, image in enumerate(图片):
            pixels = 255.0 * image.cpu().numpy()
            encoded = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for key, value in extra_pnginfo.items():
                        metadata.add_text(key, json.dumps(value))

            output_name = filename.replace("%batch_num%", str(batch_number))
            output_name = f"{output_name}_{counter:05}_.png"
            save_options = {
                "pnginfo": metadata,
                "compress_level": 4,
            }
            if dpi is not None:
                save_options["dpi"] = (dpi, dpi)
            encoded.save(
                os.path.join(full_output_folder, output_name),
                **save_options,
            )
            results.append({
                "filename": output_name,
                "subfolder": subfolder,
                "type": "output",
            })
            counter += 1

        return {"ui": {"images": results}}


NODE_CLASS_MAPPINGS = {"DatangStageResultSave": DatangStageResultSave}
NODE_DISPLAY_NAME_MAPPINGS = {"DatangStageResultSave": "大汤阶段结果保存"}
