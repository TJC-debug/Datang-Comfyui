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
        祛痘修补: true,
        肤质强度: 0.35,
        修复强度: 85,
    }),
});

export const BLEMISH_SCHEMA = 2;
export const BLEMISH_WIDGETS = Object.freeze(["祛痘修补", "肤质强度", "修复强度"]);
export function migrateBlemishValues(data) {
    const raw = data?.widgets_values;
    const defaults = [true, 0.35, 85];
    if (!Array.isArray(raw)) return { values: defaults, legacy: false };
    const legacy = data?.properties?.datang_blemish_schema !== BLEMISH_SCHEMA && raw.length === 7 && raw.every(Number.isFinite);
    if (legacy) return { values: [true, 0.35, Math.min(100, Math.max(0, raw[0]))], legacy: true };
    if (raw.length !== 3 || typeof raw[0] !== "boolean") return { values: defaults, legacy: false };
    const values = [
        typeof raw[0] === "boolean" ? raw[0] : defaults[0],
        Number.isFinite(raw[1]) && raw[1] >= 0 && raw[1] <= 1 ? raw[1] : defaults[1],
        Number.isFinite(raw[2]) && raw[2] >= 0 && raw[2] <= 100 ? raw[2] : defaults[2],
    ];
    return { values, legacy: false };
}

export function applyBlemishMigration(node, data) {
    const migrated = migrateBlemishValues(data);
    node.properties ??= {};
    node.properties.datang_blemish_schema = BLEMISH_SCHEMA;
    BLEMISH_WIDGETS.forEach((name, index) => {
        const widget = node.widgets?.find(item => item?.name === name);
        if (widget) { widget.value = migrated.values[index]; widget.callback?.(widget.value); }
    });
    return migrated;
}

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
