# 痘印精修0.4.59：模型、依赖与安装核查

本说明只适用于Datang-Comfyui现有 `DatangBlemishRetouch`。不要同时安装此前实验包来重复注册同名节点。本轮没有安装/重启ComfyUI或更新RunningHub；按平台实际环境准备好模型和兼容依赖后，仍须验收。

## 本地模型

默认根目录为 `ComfyUI/models/nabei_skin_retouch/`；也可由执行环境变量 `DATANG_SKIN_RETOUCH_MODELS` 指定绝对路径。不要把开发电脑路径写进客户工作流。

```
nabei_skin_retouch/
  retouch/pytorch_model.pt
  retouch/joint_20210926.pth
  retinaface/pytorch_model.pt
  retinaface/configuration.json
```

美肤来源：[iic/cv_unet_skin-retouching](https://www.modelscope.cn/models/iic/cv_unet_skin-retouching)。人脸检测来源：[damo/cv_resnet50_face-detection_retinaface](https://www.modelscope.cn/models/damo/cv_resnet50_face-detection_retinaface)。本包不附权重、不下载模型，不需要TensorFlow美白图。四项文件大小和SHA-256冻结在 `skin-model-manifest.json`，约391MB（十进制）；同名但不同权重不能直接记为已验证。

只读校验（使用目标ComfyUI的Python）：

```
python verify_skin_models.py --model-root <模型根目录>
```

## 依赖与缓存

沿用ComfyUI现有PyTorch及其匹配的torchvision，另需einops；根依赖仍为NumPy、OpenCV Headless、Pillow。可选 `requirements-skin.txt` 只列einops，不自动安装/升级Torch、CUDA或第二份OpenCV。torchvision与Torch必须按目标环境成套匹配；缺少或ABI错误需先处理，不能为了一个节点强行升级整套ComfyUI。

本轮真实验证：Python3.11.9、Torch2.7.1+cu128、RTX5060Ti；其他版本及CPU性能未实测。执行设备取ComfyUI的CPU/CUDA设备；不需要单独模型加载节点。权重只从本地加载，使用 `weights_only=True` 和严格state_dict。第一次载入较慢，之后同模型/设备按进程常驻；文件大小或mtime改变后重新加载。环境变量 `DATANG_SKIN_RETOUCH_KEEP_MODELS=0` 可在调用后释放模型，代价是下次重新加载。缺模型、无脸、显存不足均明确报错，整个节点包不会因缺少可选依赖而无法导入。

## 旧工作流与输出

图像输入和原皮肤MASK名称不变，MASK变可选；IMAGE/MASK输出类型及顺序不变。旧GUI七项 `[85,58,36,85,70,78,6]` 明确迁移为 `[true,0.35,85]` 并写入 `datang_blemish_schema=2`，不能按新控件位置直接套值。旧修复强度沿用，其余废弃值不转换为无关参数。旧API新增参数可缺省；删除控件不意味着继续发布无效字段。

输出MASK是局部瑕疵检测结果与可选外部MASK的交集，不是图像差值，也不代表肤质阶段全部变化范围。关闭祛痘阶段、全黑外部MASK、整体强度0或算法全关时输出全黑MASK。Alpha、画布尺寸和外部MASK黑区原像素必须保持。

## 安装与平台验收

取得具体安装授权并确认ComfyUI停止后，先完整备份现有Datang目录，再同步同一个Datang-Comfyui包；保留user、models、input/output、发布资料与其他节点。核对版本/数量/哈希后重启，依次验证旧GUI加载→连线→新参数→运行→保存重载，以及旧API prompt。已有PS_AI/纳贝链路单独验收。

RunningHub须先确认平台收录的真实仓库/分支，再经授权发布，核查平台实际拉取版本、节点导入、模型与依赖及真实任务。当前Git无remote，本轮未提交、推送或请求付费任务；不保证固定次日同步或免平台材料。

## 来源与许可

纯PyTorch核心取自ModelScope1.40.2并保留算法结构，适配点及源哈希见 `skin_retouch_core/NOTICE.txt`、`source-manifest.json`。Apache-2.0与RetinaFace MIT完整文本在 `licenses/`。权重遵循各自模型资料；不要把源码许可等同于所有上游训练数据或业务用途保证。

## 云端零字节上传兼容补充（2026-10-20）

用户实测上传工具对零字节文件提示‘暂未发现分片数据’，导致缺少核心入口。正式源码中skin_retouch_core及其子目录的5个__init__.py现加入一行无执行逻辑的注释，source-manifest.json同步更新。算法、参数、模型和节点版本0.4.59不变；旧交付不覆盖。新的非空入口补齐包解压到/root/ComfyUI/custom_nodes/并合并现有Datang-Comfyui；不要多套目录，也不要放到models。上传前备份同名核心目录，保存工作流后重启云端ComfyUI验证。本次未替换本机安装、未重启或操作云端。自动校验不能代替平台实际上传和推理验收。
