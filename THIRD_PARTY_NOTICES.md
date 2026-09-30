# 第三方与来源说明

`portrait_composition.py` 整合自 `ComfyUI-NabeiPortraitComposition-V1`，版权归 Nabei AI 所有，并按 Apache License 2.0 使用；对应许可见 `LICENSE-NabeiPortraitComposition`。

该节点涉及以下运行组件：

- `mtcnn-runtime`：Apache License 2.0，https://github.com/SAKURA-CAT/mtcnn-runtime
- ONNX Runtime：MIT License，https://github.com/microsoft/onnxruntime
- OpenCV：Apache License 2.0，https://github.com/opencv/opencv
- PyTorch：BSD-style license，https://github.com/pytorch/pytorch

Datang 正式根依赖继续使用 `opencv-python-headless`。由于 `mtcnn-runtime 1.0.0` 的包元数据会额外依赖 `opencv-python`，本项目不自动把两个 OpenCV 发行包同时安装：环境已有 `mtcnn-runtime` 时优先使用；缺少或运行失败时，节点自动回退到现有 OpenCV Haar 检测。

本节点不包含 MTCNN、Qwen、CLIP、VAE、采样器或其他模型权重，也不自动联网下载模型。
