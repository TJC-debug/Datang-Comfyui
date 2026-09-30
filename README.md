# Datang-Comfyui

大汤自制 ComfyUI 节点合集。当前版本：`0.4.57`。

## 安装

在 ComfyUI 的 `custom_nodes` 目录执行：

```bash
git clone https://github.com/TJC-debug/Datang-Comfyui.git
cd Datang-Comfyui
python -m pip install -r requirements.txt
```

安装完成后重启 ComfyUI。

更新节点：

```bash
git pull
python -m pip install -r requirements.txt
```

## 节点列表

### 工作流与分组

- 大汤节点组开关
- 大汤节点组状态标记
- 大汤布尔常量
- 大汤布尔与非
- 大汤惰性条件分支

### 提示词与模型

- 大汤重新打光提示词
- 提示词开关板（无限槽位）
- 模型选择器（单选多槽位）

### 人像与图像处理

- 大汤人物定比裁剪
- 大汤图像比例裁剪
- 大汤图像尺寸回正
- 大汤生活照打印裁剪
- 大汤人像快速美颜
- 大汤人像痘印精修

### 证件照与结果保存

- 大汤证件照快速裁剪
- 大汤证件照比例裁剪
- 大汤证件照智能排版
- 大汤证件照 DPI 保存
- 大汤阶段结果保存

## 运行说明

- Python 依赖见 `requirements.txt`。
- 仓库不包含模型权重，也不会自动联网下载模型。
- 个别节点需要工作流所使用的对应模型文件；缺少时会在执行阶段提示。
- 当前主要兼容目标为 ComfyUI `0.3.75`、前端 `1.30.6`。

## 许可证与第三方说明

人物定比裁剪组件许可见 `LICENSE-NabeiPortraitComposition`，第三方组件说明见 `THIRD_PARTY_NOTICES.md`。
