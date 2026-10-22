"""Local-only cached PyTorch adapter. See skin_retouch_core/NOTICE.txt."""
from __future__ import annotations
import contextlib
import gc
import importlib
import importlib.util
import os
from pathlib import Path
import sys
import threading

_LOCK = threading.RLock()
_CACHE = None
_KEY = None
REQUIRED = ("retouch/pytorch_model.pt", "retouch/joint_20210926.pth", "retinaface/pytorch_model.pt", "retinaface/configuration.json")

def model_root():
    configured = os.environ.get("DATANG_SKIN_RETOUCH_MODELS", "").strip()
    if configured:
        root = Path(configured).expanduser()
        if not root.is_absolute():
            raise ValueError("DATANG_SKIN_RETOUCH_MODELS必须是绝对路径。")
    else:
        try:
            import folder_paths
            root = Path(folder_paths.models_dir) / "nabei_skin_retouch"
        except ImportError as exc:
            raise RuntimeError("请在ComfyUI内运行，或用DATANG_SKIN_RETOUCH_MODELS指定模型根目录。") from exc
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("痘印精修模型缺失：" + "、".join(missing) + "。请按安装说明准备本地模型；节点不会自动联网下载。")
    return root.resolve()

def components():
    name = "_datang_skin_retouch_core_0459"
    if name not in sys.modules:
        path = Path(__file__).with_name("skin_retouch_core")
        spec = importlib.util.spec_from_file_location(name, path / "__init__.py", submodule_search_locations=[str(path)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    paths = {"utils":"utils", "unet":"unet_deploy", "detect":"detection_model.detection_unet_in", "inpaint":"inpainting_model.inpainting_unet", "face":"retinaface.detector", "methods":"retouch_methods"}
    return {key: importlib.import_module(name + "." + path) for key, path in paths.items()}

class Backend:
    def __init__(self, root, device):
        import torch
        try:
            modules = components()
        except (ImportError, ModuleNotFoundError) as exc:
            raise RuntimeError("痘印精修缺少兼容的torchvision或einops，请按安装说明配置；不需要ModelScope和TensorFlow。") from exc
        self.device, self.utils = device, modules["utils"]
        class Engine(modules["methods"].RetouchMethods):
            pass
        self.pipe = pipe = Engine()
        pipe.generator = modules["unet"].UNet(3, 3).to(device)
        state = torch.load(str(root / "retouch/pytorch_model.pt"), map_location="cpu", weights_only=True)
        pipe.generator.load_state_dict(state["generator"], strict=True)
        pipe.generator.eval()
        local = torch.load(str(root / "retouch/joint_20210926.pth"), map_location="cpu", weights_only=True)
        pipe.inpainting_net = modules["inpaint"].RetouchingNet(in_channels=4, out_channels=3).to(device)
        pipe.detection_net = modules["detect"].DetectionUNet(n_channels=3, n_classes=1).to(device)
        pipe.inpainting_net.load_state_dict(local["inpainting_net"], strict=True)
        pipe.detection_net.load_state_dict(local["detection_net"], strict=True)
        pipe.inpainting_net.eval(); pipe.detection_net.eval()
        pipe.patch_size = pipe.input_size = 512
        pipe.diffuse_mask = torch.from_numpy(self.utils.gen_diffuse_mask()).to(device).float().permute(2, 0, 1)[None, ...]
        self.detector = modules["face"].RetinaFaceDetection(root / "retinaface/pytorch_model.pt", root / "retinaface/configuration.json", device)

    def run(self, rgb, local=True, texture=0.35):
        import numpy as np
        import torch
        output = torch.from_numpy(rgb.copy()).to(self.device)
        detected = np.zeros(rgb.shape[:2], dtype=np.float32)
        with torch.inference_mode(), torch.backends.cudnn.flags(benchmark=False):
            # Match the upstream nested ndarray preprocessor: RetinaFace receives BGR, while retouching keeps RGB.
            boxes, _ = self.detector.forward({"img": torch.from_numpy(rgb[:, :, ::-1].copy())})
            crops = self.utils.get_crop_bbox([{"bbox": row[:4].astype(np.int32).tolist(), "score": float(row[4])} for row in boxes])
            faces = 0
            for box in crops:
                roi, _, crop = self.utils.get_roi_without_padding(rgb, box)
                if roi.size == 0:
                    continue
                faces += 1
                tensor = self.utils.preprocess_roi(self.utils.roi_to_tensor(roi).to(self.device))
                if local:
                    tensor, real_mask = self.pipe.retouch_local(tensor)
                    area = real_mask[0, 0].float().cpu().numpy()
                    np.maximum(detected[crop[0]:crop[1], crop[2]:crop[3]], area, out=detected[crop[0]:crop[1], crop[2]:crop[3]])
                prediction = self.pipe.predict_roi(tensor, degree=texture, smooth_border=True, return_mg=False)["pred"]
                output[crop[0]:crop[1], crop[2]:crop[3]] = prediction
        return output.cpu().numpy(), detected, faces

    def close(self):
        self.pipe = None
        self.detector = None

def release_backend():
    global _CACHE, _KEY
    with _LOCK:
        if _CACHE is not None:
            _CACHE.close()
        _CACHE = _KEY = None
        gc.collect()

@contextlib.contextmanager
def acquire():
    global _CACHE, _KEY
    import torch
    root = model_root()
    try:
        from comfy.model_management import get_torch_device
        device = get_torch_device()
    except ImportError:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type not in {"cuda", "cpu"}:
        raise RuntimeError("痘印精修仅支持PyTorch CPU/CUDA执行设备。")
    key = (str(root), str(device), tuple(((root / name).stat().st_size, (root / name).stat().st_mtime_ns) for name in REQUIRED))
    with _LOCK:
        try:
            if key != _KEY:
                release_backend()
                backend = Backend(root, device)
                _CACHE, _KEY = backend, key
            yield _CACHE
        except Exception:
            release_backend()
            raise
        finally:
            if os.environ.get("DATANG_SKIN_RETOUCH_KEEP_MODELS", "1") == "0":
                release_backend()
