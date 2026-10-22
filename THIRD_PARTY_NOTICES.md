# 第三方与来源说明

`portrait_composition.py` 整合自 `ComfyUI-NabeiPortraitComposition-V1`，版权归 Nabei AI 所有，并按 Apache License 2.0 使用；对应许可见 `LICENSE-NabeiPortraitComposition`。

该节点涉及以下运行组件：

- `mtcnn-runtime`：Apache License 2.0，https://github.com/SAKURA-CAT/mtcnn-runtime
- ONNX Runtime：MIT License，https://github.com/microsoft/onnxruntime
- OpenCV：Apache License 2.0，https://github.com/opencv/opencv
- PyTorch：BSD-style license，https://github.com/pytorch/pytorch

Datang 正式根依赖继续使用 `opencv-python-headless`。由于 `mtcnn-runtime 1.0.0` 的包元数据会额外依赖 `opencv-python`，本项目不自动把两个 OpenCV 发行包同时安装：环境已有 `mtcnn-runtime` 时优先使用；缺少或运行失败时，节点自动回退到现有 OpenCV Haar 检测。

本节点不包含 MTCNN、Qwen、CLIP、VAE、采样器或其他模型权重，也不自动联网下载模型。

## 0.4.59 痘印精修核心

`skin_retouch_core/` 适配自 Alibaba ModelScope 1.40.2 的 PyTorch皮肤修饰、局部检测/修补及RetinaFace代码。保留上游架构和阈值，移除ModelScope框架、TensorFlow美白阶段与在线权重下载，增加本地缓存、明确错误及真实检测MASK。具体源文件哈希和改动见该目录 `source-manifest.json` 与 `NOTICE.txt`。

- ModelScope：https://github.com/modelscope/modelscope ，Apache-2.0完整文本见 `licenses/MODELSCOPE-APACHE-2.0.txt`。
- RetinaFace组件来源：https://github.com/biubug6/Pytorch_Retinaface ，MIT许可见 `licenses/RETINAFACE-MIT.txt`。
- 运行环境使用PyTorch、torchvision（BSD-style）、einops（MIT）、NumPy（BSD）、Pillow（HPND）、OpenCV（Apache-2.0）；这些第三方Python包不随本源码包打包。

权重不在交付包内；模型来源与四项大小/SHA-256见 `SKIN_RETOUCH_INSTALL.md` 和 `skin-model-manifest.json`。
