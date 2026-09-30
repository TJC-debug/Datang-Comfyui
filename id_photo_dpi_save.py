import json
import os


class DatangIdPhotoDpiSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图片": ("IMAGE",),
                "DPI": ("INT", {"default": 300, "min": 72, "max": 1200, "step": 1}),
                "文件名前缀": ("STRING", {"default": "证件照", "multiline": False}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "大汤节点/图像"
    DESCRIPTION = "将证件照保存为真实 PNG，并写入指定 DPI 元数据。"

    def save_images(
        self,
        图片,
        DPI=300,
        文件名前缀="证件照",
        prompt=None,
        extra_pnginfo=None,
    ):
        import folder_paths
        import numpy as np
        from comfy.cli_args import args
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo

        if len(图片) == 0:
            raise ValueError("大汤证件照 DPI 保存没有收到图片。")
        if isinstance(DPI, bool) or not isinstance(DPI, (int, float)):
            raise ValueError("DPI 必须是 72 到 1200 的整数。")
        dpi = int(DPI)
        if dpi != DPI or not 72 <= dpi <= 1200:
            raise ValueError("DPI 必须是 72 到 1200 的整数。")

        output_dir = folder_paths.get_output_directory()
        prefix = str(文件名前缀 or "证件照").strip() or "证件照"
        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            prefix,
            output_dir,
            图片[0].shape[1],
            图片[0].shape[0],
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
            encoded.save(
                os.path.join(full_output_folder, output_name),
                pnginfo=metadata,
                dpi=(dpi, dpi),
                compress_level=4,
            )
            results.append({
                "filename": output_name,
                "subfolder": subfolder,
                "type": "output",
            })
            counter += 1

        return {"ui": {"images": results}}


NODE_CLASS_MAPPINGS = {"DatangIdPhotoDpiSave": DatangIdPhotoDpiSave}
NODE_DISPLAY_NAME_MAPPINGS = {"DatangIdPhotoDpiSave": "大汤证件照 DPI 保存"}
