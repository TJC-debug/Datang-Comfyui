export const BEAUTY_NODE_DEFAULTS = Object.freeze({
    DatangFastFaceBeauty: Object.freeze({
        美颜强度: 60,
        磨皮: 45,
        美白提亮: 18,
        纹理保留: 70,
        黑眼圈淡化: 30,
        瑕疵皱纹淡化: 25,
    }),
    DatangBlemishRetouch: Object.freeze({
        修复强度: 85,
        检测灵敏度: 58,
        最大瑕疵尺寸: 36,
        深色斑点修复: 85,
        红印修复: 70,
        五官边缘保护: 78,
        边缘羽化: 6,
    }),
});

export function applyBeautyDefaults(node, defaults) {
    if (!node || !defaults) return false;
    let changed = false;
    for (const [name, value] of Object.entries(defaults)) {
        const widget = node.widgets?.find((candidate) => candidate?.name === name);
        if (!widget) continue;
        widget.value = value;
        widget.callback?.(value);
        changed = true;
    }
    if (changed) {
        node.setDirtyCanvas?.(true, true);
        node.graph?.setDirtyCanvas?.(true, true);
    }
    return changed;
}
