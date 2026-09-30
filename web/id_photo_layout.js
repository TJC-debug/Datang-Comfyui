import { app } from "../../../scripts/app.js";
import {
    buildLayoutCandidates,
    DEFAULT_DPI,
    DEFAULT_SETTINGS,
    GRID_COUNT_OPTIONS,
    ID_PHOTO_PRESETS,
    MAX_DPI,
    MIN_DPI,
    normaliseSettings,
    ONE_TWO_MIXED_PRESET_ID,
    PAPER_PRESETS,
    previewFromLayout,
    settingsFromLayout,
    TOTAL_COUNT_OPTIONS,
} from "./id_photo_layout_core.js";

const NODE_CLASS = "DatangIdPhotoLayout";
const DATA_WIDGET_NAME = "排版数据";
const DPI_WIDGET_NAME = "DPI";
const USER_PRESET_STORAGE_KEY = "datang.id_photo_layout.user_presets.v1";
const MAX_USER_PRESETS = 20;
const MIN_NODE_WIDTH = 520;
const MIN_NODE_HEIGHT = 760;

const BUILT_IN_LAYOUT_PRESETS = Object.freeze([
    {
        id: "studio-five-one-inch-9",
        name: "5寸 · 9张1寸",
        note: "常用冲印 · 照片横排",
        settings: { photoPresetId: "one-inch", paperPresetId: "five-inch-paper", photoOrientation: "landscape", orientation: "landscape", layoutMode: "fixed_grid", count: 9, columns: 3, rows: 3, spacingPreset: "studio_tight", marginCm: 0, gapCm: 0, cropMarksEnabled: true },
    },
    {
        id: "studio-five-two-inch-4",
        name: "5寸 · 4张2寸",
        note: "常用冲印 · 2列 × 2行",
        settings: { photoPresetId: "two-inch", paperPresetId: "five-inch-paper", photoOrientation: "original", orientation: "portrait", layoutMode: "fixed_grid", count: 4, columns: 2, rows: 2, spacingPreset: "cutting_gap", marginCm: 0.4, gapCm: 0.2, cropMarksEnabled: true },
    },
    {
        id: "studio-six-one-inch-12",
        name: "6寸 · 12张1寸",
        note: "影楼常用 · 6列 × 2行",
        settings: { photoPresetId: "one-inch", paperPresetId: "six-inch-paper", photoOrientation: "original", orientation: "landscape", layoutMode: "fixed_grid", count: 12, columns: 6, rows: 2, spacingPreset: "studio_tight", marginCm: 0, gapCm: 0, cropMarksEnabled: true },
    },
    {
        id: "studio-six-two-inch-6",
        name: "6寸 · 6张2寸",
        note: "影楼常用 · 3列 × 2行",
        settings: { photoPresetId: "two-inch", paperPresetId: "six-inch-paper", photoOrientation: "original", orientation: "landscape", layoutMode: "fixed_grid", count: 6, columns: 3, rows: 2, spacingPreset: "studio_tight", marginCm: 0, gapCm: 0, cropMarksEnabled: true },
    },
    {
        id: "studio-seven-one-two-mixed",
        name: "7寸 · 1寸+2寸",
        note: "上8张竖版 · 下4张横放",
        settings: { photoPresetId: ONE_TWO_MIXED_PRESET_ID, paperPresetId: "seven-inch-paper", photoOrientation: "original", orientation: "portrait", layoutMode: "template", count: 12, columns: 0, rows: 0, spacingPreset: "custom", marginCm: 0, gapCm: 0.2, cropMarksEnabled: true },
    },
]);

function readUserPresets() {
    try {
        const value = JSON.parse(localStorage.getItem(USER_PRESET_STORAGE_KEY) || "[]");
        if (!Array.isArray(value)) return [];
        return value
            .filter((item) => item && typeof item.id === "string" && typeof item.name === "string" && item.settings && typeof item.settings === "object")
            .slice(0, MAX_USER_PRESETS)
            .map((item) => ({ id: item.id, name: item.name.slice(0, 24), settings: normaliseSettings(item.settings) }));
    } catch {
        return [];
    }
}

function writeUserPresets(presets) {
    try {
        localStorage.setItem(USER_PRESET_STORAGE_KEY, JSON.stringify(presets));
        return true;
    } catch {
        return false;
    }
}

function canConsumeWheel(element, deltaY) {
    if (!element || deltaY === 0 || element.scrollHeight <= element.clientHeight + 1) return false;
    if (deltaY < 0) return element.scrollTop > 1;
    return element.scrollTop + element.clientHeight < element.scrollHeight - 1;
}

function forwardWheelToCanvas(event) {
    const canvas = app.canvas?.canvas;
    if (!(canvas instanceof HTMLCanvasElement)) return;
    canvas.dispatchEvent(new WheelEvent("wheel", {
        bubbles: true,
        cancelable: true,
        clientX: event.clientX,
        clientY: event.clientY,
        deltaMode: event.deltaMode,
        deltaX: event.deltaX,
        deltaY: event.deltaY,
        ctrlKey: event.ctrlKey,
        shiftKey: event.shiftKey,
        altKey: event.altKey,
        metaKey: event.metaKey,
    }));
}

function orientedDisplaySize(presets, presetId, customUnit, customWidth, customHeight, orientation) {
    const preset = presets.find((item) => item.id === presetId) || presets[0];
    let width = preset.id === "custom" ? Number(customWidth) : preset.width;
    let height = preset.id === "custom" ? Number(customHeight) : preset.height;
    const unit = preset.id === "custom" ? customUnit : preset.unit;
    if ((orientation === "portrait" && width > height) || (orientation === "landscape" && width < height)) {
        [width, height] = [height, width];
    }
    return { width, height, unit };
}

function dimensionText(value, unit) {
    const number = Number(value);
    return `${Number.isInteger(number) ? number : Number(number.toFixed(2))} ${unit === "cm" ? "厘米" : "像素"}`;
}

function graphLinkSource(node, inputName) {
    const input = node.inputs?.find((item) => String(item?.name || item?.label || "") === inputName);
    if (input?.link === null || input?.link === undefined) return null;
    const link = app.graph?.links?.[input.link] ?? app.graph?.links?.[String(input.link)];
    const originId = Array.isArray(link) ? link[1] : link?.origin_id ?? link?.originId;
    const source = app.graph?.getNodeById?.(originId) || app.graph?._nodes_by_id?.[originId] || null;
    return { connected: true, source };
}

function graphLinkRecord(linkId) {
    return app.graph?.links?.[linkId] ?? app.graph?.links?.[String(linkId)] ?? null;
}

function linkEndpoint(link, arrayIndex, snakeName, camelName) {
    if (Array.isArray(link)) return link[arrayIndex];
    return link?.[snakeName] ?? link?.[camelName];
}

function inferredSourceType(link) {
    const originId = linkEndpoint(link, 1, "origin_id", "originId");
    const originSlot = linkEndpoint(link, 2, "origin_slot", "originSlot");
    const source = app.graph?.getNodeById?.(originId) || app.graph?._nodes_by_id?.[originId] || null;
    const output = source?.outputs?.[originSlot];
    const directType = String(output?.type || "");
    if (directType && directType !== "*") return { source, originSlot, type: directType };
    const siblingTypes = [];
    for (const siblingId of output?.links || []) {
        const sibling = graphLinkRecord(siblingId);
        const targetId = linkEndpoint(sibling, 3, "target_id", "targetId");
        const targetSlot = linkEndpoint(sibling, 4, "target_slot", "targetSlot");
        const target = app.graph?.getNodeById?.(targetId) || app.graph?._nodes_by_id?.[targetId] || null;
        const targetType = String(target?.inputs?.[targetSlot]?.type || "");
        if (targetType && targetType !== "*") siblingTypes.push(targetType);
    }
    if (siblingTypes.includes("IMAGE")) return { source, originSlot, type: "IMAGE" };
    if (siblingTypes.length) return { source, originSlot, type: siblingTypes[0] };
    return { source, originSlot, type: String(linkEndpoint(link, 5, "type", "type") || "") };
}

function repairLegacyConvertedDpiInput(node) {
    if (!node.graph) return false;
    const legacyIndex = node.inputs?.findIndex((input) => (
        String(input?.name || input?.label || "") === DPI_WIDGET_NAME
        && String(input?.widget?.name || "") === DPI_WIDGET_NAME
    )) ?? -1;
    if (legacyIndex < 0) return false;
    const legacyInput = node.inputs[legacyIndex];
    const link = legacyInput?.link === null || legacyInput?.link === undefined
        ? null
        : graphLinkRecord(legacyInput.link);
    if (!link) return false;
    const inferred = link ? inferredSourceType(link) : null;
    const targetName = inferred?.type === "IMAGE" ? "图片" : "输入DPI";
    const targetInput = node.inputs?.find((input) => String(input?.name || input?.label || "") === targetName);
    const canMove = Boolean(link && inferred?.source && targetInput && (targetInput.link === null || targetInput.link === undefined));
    node.disconnectInput?.(legacyIndex);
    node.removeInput?.(legacyIndex);
    if (canMove) {
        const targetIndex = node.inputs?.findIndex((input) => String(input?.name || input?.label || "") === targetName) ?? -1;
        if (targetIndex >= 0) inferred.source.connect?.(inferred.originSlot, node, targetIndex);
    }
    node.setDirtyCanvas?.(true, true);
    return true;
}

function sourceWidgetValue(source, name) {
    return source?.widgets?.find((widget) => String(widget?.name || "") === name)?.value;
}

function resolvePresetSizeSource(widthSource, heightSource) {
    if (!widthSource?.source || widthSource.source !== heightSource?.source) return null;
    const source = widthSource.source;
    if (String(source.comfyClass || source.type || "") !== "LoneSeaPresetSize") return null;
    const presetLabel = String(sourceWidgetValue(source, "预设尺寸") || "");
    const dpi = Math.round(Number(sourceWidgetValue(source, "dpi")));
    if (!Number.isFinite(dpi) || dpi < 1) return null;
    let width;
    let height;
    let unit = "cm";
    if (presetLabel === "自定义尺寸") {
        width = Number(sourceWidgetValue(source, "自定义宽度"));
        height = Number(sourceWidgetValue(source, "自定义高度"));
        const sourceUnit = String(sourceWidgetValue(source, "单位") || "像素");
        unit = sourceUnit === "厘米" ? "cm" : sourceUnit === "英寸" ? "inch" : "px";
    } else {
        const match = presetLabel.match(/([0-9]+(?:\.[0-9]+)?)\s*[x×]\s*([0-9]+(?:\.[0-9]+)?)\s*cm/i);
        if (!match) return null;
        width = Number(match[1]);
        height = Number(match[2]);
    }
    if (!(width > 0 && height > 0)) return null;
    const toPixels = (value) => unit === "cm" ? Math.round(value * dpi / 2.54) : unit === "inch" ? Math.round(value * dpi) : Math.round(value);
    return { width: toPixels(width), height: toPixels(height), dpi, presetLabel };
}

function resolveExternalInputs(node) {
    const dpiSource = graphLinkSource(node, "输入DPI");
    const widthSource = graphLinkSource(node, "输入照片宽度");
    const heightSource = graphLinkSource(node, "输入照片高度");
    const dpiNode = dpiSource?.source;
    let dpi = null;
    if (dpiNode && String(dpiNode.comfyClass || dpiNode.type || "") === "LoneSeaPresetSize") {
        dpi = Math.round(Number(sourceWidgetValue(dpiNode, "dpi")));
    } else if (dpiNode && String(dpiNode.comfyClass || dpiNode.type || "") === "PrimitiveNode") {
        dpi = Math.round(Number(dpiNode.widgets?.[0]?.value));
    }
    if (!Number.isFinite(dpi)) dpi = null;
    const size = widthSource && heightSource ? resolvePresetSizeSource(widthSource, heightSource) : null;
    return {
        dpi: { connected: Boolean(dpiSource), resolved: dpi !== null, value: dpi },
        photoSize: {
            connected: Boolean(widthSource || heightSource),
            paired: Boolean(widthSource) === Boolean(heightSource),
            resolved: Boolean(size),
            ...size,
        },
    };
}

function externalFingerprint(value) {
    return JSON.stringify(value);
}

function installStyles() {
    if (document.getElementById("datang-id-photo-layout-styles")) return;
    const style = document.createElement("style");
    style.id = "datang-id-photo-layout-styles";
    style.textContent = `
        .datang-id-photo { box-sizing: border-box; display: flex; flex-direction: column; gap: 10px; width: 100%; height: 100%; padding: 10px; color: #e9e7df; font: 12px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; overflow: auto; }
        .datang-id-photo *, .datang-id-photo *::before, .datang-id-photo *::after { box-sizing: border-box; }
        .datang-id-photo__grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
        .datang-id-photo__grid--primary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .datang-id-photo__field { display: flex; flex-direction: column; gap: 4px; min-width: 0; color: #bdb9ae; }
        .datang-id-photo__size-row { grid-column: 1 / -1; display: grid; grid-template-columns: minmax(0, 1fr); gap: 6px; align-items: end; }
        .datang-id-photo__size-row.is-custom { grid-template-columns: minmax(185px, 1.9fr) 78px minmax(72px, .72fr) minmax(72px, .72fr); }
        .datang-id-photo select, .datang-id-photo input, .datang-id-photo textarea, .datang-id-photo button { border: 1px solid #575446; border-radius: 5px; color: #eee9dc; background: #1d1e1a; font: inherit; }
        .datang-id-photo select, .datang-id-photo input { width: 100%; min-width: 0; height: 32px; padding: 0 8px; }
        .datang-id-photo select:focus, .datang-id-photo input:focus, .datang-id-photo button:focus-visible { border-color: #d4a62a; outline: 1px solid #d4a62a; }
        .datang-id-photo select:disabled, .datang-id-photo input:disabled { color: #8d8a82; border-color: #44433d; background: #252520; opacity: .82; }
        .datang-id-photo__quick { padding-bottom: 10px; border-bottom: 1px solid #45433b; }
        .datang-id-photo__quick[hidden] { display: none !important; }
        .datang-id-photo__external { padding: 8px 10px; border: 1px solid #796221; border-radius: 6px; color: #eadcae; background: #292616; }
        .datang-id-photo__external[hidden] { display: none !important; }
        .datang-id-photo__external.is-error { border-color: #a8544d; color: #f0a39c; background: #382321; }
        .datang-id-photo__external strong { display: block; margin-bottom: 3px; color: #ffd65b; }
        .datang-id-photo__quick-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
        .datang-id-photo__quick-head strong { color: #f2eddc; font-size: 13px; }
        .datang-id-photo__quick-head button { min-height: 28px; padding: 3px 9px; color: #d7bd68; background: transparent; }
        .datang-id-photo__quick-actions { display: flex; align-items: center; gap: 5px; }
        .datang-id-photo__preset-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
        [data-built-in-presets] > :last-child:nth-child(odd) { grid-column: 1 / -1; }
        .datang-id-photo__preset { display: flex; flex-direction: column; align-items: flex-start; justify-content: center; min-height: 46px !important; padding: 6px 9px !important; text-align: left; }
        .datang-id-photo__preset strong { color: inherit; font-size: 12px; line-height: 1.25; }
        .datang-id-photo__preset small { margin-top: 2px; color: #979389; font-size: 10px; line-height: 1.2; }
        .datang-id-photo__save-row { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 6px; margin-top: 7px; }
        .datang-id-photo__save-row[hidden], .datang-id-photo__mine[hidden], .datang-id-photo__field[hidden], .datang-id-photo details[hidden] { display: none !important; }
        .datang-id-photo__save-row button { min-height: 32px; }
        .datang-id-photo__mine { margin-top: 9px; }
        .datang-id-photo__mine-label { display: block; margin-bottom: 5px; color: #aaa69b; font-size: 11px; }
        .datang-id-photo__user-item { display: grid; grid-template-columns: minmax(0, 1fr) 30px; gap: 4px; }
        .datang-id-photo__user-item > button:last-child { min-height: 34px; padding: 0; color: #9e9990; }
        .datang-id-photo__schemes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }
        .datang-id-photo button { min-height: 34px; padding: 6px 9px; cursor: pointer; }
        .datang-id-photo button:hover { border-color: #8d762f; background: #302918; }
        .datang-id-photo button.is-active { border-color: #d4a62a; color: #ffe28a; background: #3a311c; box-shadow: inset 0 0 0 1px rgba(255, 200, 61, .16); }
        .datang-id-photo button:disabled { cursor: not-allowed; opacity: .45; }
        .datang-id-photo__preview-shell { display: grid; grid-template-columns: minmax(300px, 1.5fr) minmax(140px, .5fr); gap: 10px; min-height: 260px; padding: 8px; border: 1px solid #46443c; border-radius: 8px; background: #24241f; }
        .datang-id-photo__paper-wrap { display: flex; align-items: center; justify-content: center; min-height: 238px; padding: 10px 6px 24px 30px; border-radius: 6px; background: #171815; }
        .datang-id-photo__paper { position: relative; max-width: 100%; max-height: 255px; border: 1px solid #aaa89f; background: #f8f7f2; box-shadow: 0 8px 22px rgba(0,0,0,.28); }
        .datang-id-photo__paper::before { content: attr(data-width-label); position: absolute; left: 0; right: 0; bottom: -22px; color: #aaa69b; text-align: center; font-size: 10px; white-space: nowrap; }
        .datang-id-photo__paper::after { content: attr(data-height-label); position: absolute; top: 0; bottom: 0; left: -27px; display: flex; align-items: center; justify-content: center; color: #aaa69b; font-size: 10px; white-space: nowrap; writing-mode: vertical-rl; transform: rotate(180deg); }
        .datang-id-photo__slot { position: absolute; display: flex; align-items: center; justify-content: center; min-width: 3px; min-height: 3px; border: 1px solid #77756f; color: #66645f; background: linear-gradient(180deg, #e4e7e5 0%, #d7dbd8 100%); font-size: 9px; overflow: hidden; }
        .datang-id-photo__slot-number { position: absolute; z-index: 2; top: 1px; left: 2px; color: #77746e; font-size: 8px; line-height: 1; }
        .datang-id-photo__person { position: relative; width: 62%; height: 78%; opacity: .72; transform-origin: center; }
        .datang-id-photo__person.is-landscape { transform: rotate(90deg); }
        .datang-id-photo__person::before { content: ""; position: absolute; top: 8%; left: 50%; width: 34%; aspect-ratio: 1; border-radius: 50%; background: #aaaead; transform: translateX(-50%); }
        .datang-id-photo__person::after { content: ""; position: absolute; left: 8%; right: 8%; bottom: -8%; height: 54%; border-radius: 55% 55% 12% 12%; background: #a2a7a5; }
        .datang-id-photo__crop-mark { position: absolute; z-index: 2; min-width: 1px; min-height: 1px; background: #242424; pointer-events: none; }
        .datang-id-photo__summary { display: flex; flex-direction: column; justify-content: flex-start; gap: 6px; min-width: 0; padding-top: 20px; }
        .datang-id-photo__summary strong { color: #f5efd9; font-size: 13px; }
        .datang-id-photo__summary p { display: flex; flex-direction: column; gap: 2px; margin: 0; color: #b6b2a7; }
        .datang-id-photo__summary-line { display: block; }
        .datang-id-photo__status { padding: 8px; border-left: 3px solid #5f956f; border-radius: 3px; color: #9ee0b3; background: #203026; }
        .datang-id-photo__status.is-error { border-color: #c05d55; color: #f0a39c; background: #382321; }
        .datang-id-photo__status.is-external { border-color: #6c7fa9; color: #afc4ef; background: #222a3a; }
        .datang-id-photo__status[hidden], .datang-id-photo__schemes[hidden] { display: none !important; }
        .datang-id-photo details { border-top: 1px solid #414039; padding-top: 7px; color: #aaa69b; }
        .datang-id-photo summary { cursor: pointer; user-select: none; }
        .datang-id-photo__advanced-grid { margin-top: 8px; }
        .datang-id-photo textarea { width: 100%; height: 88px; margin-top: 7px; padding: 7px; resize: vertical; color: #aaa79e; font: 10px/1.35 ui-monospace, Consolas, monospace; }
    `;
    document.head.appendChild(style);
}

function hideDataWidget(node, originalWidget, onExternalValue) {
    const index = node.widgets?.indexOf(originalWidget) ?? -1;
    if (index < 0) return null;
    let storedValue = originalWidget.value;
    let internalWrite = false;
    const widget = {
        ...originalWidget,
        hidden: true,
        datangHidden: true,
        computeSize: () => [0, -4],
        computeLayoutSize: () => ({ minHeight: 0, maxHeight: 0, minWidth: 0 }),
        draw: () => {},
        serializeValue: () => storedValue,
        writeFromUi(value) {
            internalWrite = true;
            this.value = value;
            internalWrite = false;
        },
    };
    Object.defineProperty(widget, "value", {
        configurable: true,
        enumerable: true,
        get: () => storedValue,
        set: (value) => {
            storedValue = value;
            originalWidget.callback?.(storedValue);
            if (!internalWrite) onExternalValue?.(storedValue);
        },
    });
    node.widgets[index] = widget;
    originalWidget.hidden = true;
    originalWidget.datangHidden = true;
    if (originalWidget.inputEl?.style) originalWidget.inputEl.style.display = "none";
    return widget;
}

function optionMarkup(items) {
    return items.map((item) => `<option value="${item.id}">${item.label}</option>`).join("");
}

function numericOptionMarkup(items, automatic = false) {
    return items.map((value) => `<option value="${value}">${automatic && value === 0 ? "自动" : value}</option>`).join("");
}

function createUi(node, originalDataWidget, originalDpiWidget) {
    const root = document.createElement("div");
    root.className = "datang-id-photo";
    root.innerHTML = `
        <section class="datang-id-photo__quick" data-quick-layout>
            <div class="datang-id-photo__quick-head">
                <strong>快捷排版</strong>
                <div class="datang-id-photo__quick-actions">
                    <button type="button" data-preset-action="reset">恢复默认</button>
                    <button type="button" data-preset-action="show-save">＋ 保存当前参数</button>
                </div>
            </div>
            <div class="datang-id-photo__preset-grid" data-built-in-presets></div>
            <div class="datang-id-photo__save-row" data-save-row hidden>
                <input data-preset-name type="text" maxlength="24" placeholder="输入预设名称">
                <button type="button" data-preset-action="save">保存</button>
                <button type="button" data-preset-action="cancel">取消</button>
            </div>
            <div class="datang-id-photo__mine" data-user-presets-wrap hidden>
                <span class="datang-id-photo__mine-label">我的预设</span>
                <div class="datang-id-photo__preset-grid" data-user-presets></div>
            </div>
        </section>
        <section class="datang-id-photo__external" data-external-spec hidden></section>
        <div class="datang-id-photo__grid datang-id-photo__grid--primary">
            <div class="datang-id-photo__size-row" data-size-row="photo">
                <label class="datang-id-photo__field"><span>证件照尺寸</span><select data-field="photoPresetId">${optionMarkup(ID_PHOTO_PRESETS)}</select></label>
                <label class="datang-id-photo__field" data-custom-control="photo"><span>单位</span><select data-field="customPhotoUnit"><option value="cm">厘米</option><option value="px">像素</option></select></label>
                <label class="datang-id-photo__field" data-custom-control="photo"><span>宽</span><input data-field="customPhotoWidth" type="number" min="0.1" step="0.1"></label>
                <label class="datang-id-photo__field" data-custom-control="photo"><span>高</span><input data-field="customPhotoHeight" type="number" min="0.1" step="0.1"></label>
            </div>
            <div class="datang-id-photo__size-row" data-size-row="paper">
                <label class="datang-id-photo__field"><span>输出画布</span><select data-field="paperPresetId">${optionMarkup(PAPER_PRESETS)}</select></label>
                <label class="datang-id-photo__field" data-custom-control="paper"><span>单位</span><select data-field="customPaperUnit"><option value="cm">厘米</option><option value="px">像素</option></select></label>
                <label class="datang-id-photo__field" data-custom-control="paper"><span>宽</span><input data-field="customPaperWidth" type="number" min="0.1" step="0.1"></label>
                <label class="datang-id-photo__field" data-custom-control="paper"><span>高</span><input data-field="customPaperHeight" type="number" min="0.1" step="0.1"></label>
            </div>
            <label class="datang-id-photo__field"><span>照片方向</span><select data-field="photoOrientation"><option value="original">保持规格</option><option value="portrait">竖版</option><option value="landscape">横版</option></select></label>
            <label class="datang-id-photo__field"><span>画布方向</span><select data-field="orientation"><option value="auto">自动比较横/竖</option><option value="portrait">竖版</option><option value="landscape">横版</option></select></label>
            <label class="datang-id-photo__field"><span>排版方式</span><select data-field="layoutMode"><option value="auto_fill">自动铺满</option><option value="specified_count">指定张数</option><option value="fixed_grid">固定行列</option><option value="template" disabled>固定混排模板</option></select></label>
            <label class="datang-id-photo__field"><span>裁切线</span><select data-field="cropMarksEnabled"><option value="true">显示（避开照片）</option><option value="false">不显示</option></select></label>
        </div>
        <details data-layout-advanced>
            <summary>高级排版设置</summary>
            <div class="datang-id-photo__grid datang-id-photo__advanced-grid">
                <label class="datang-id-photo__field" data-layout-control="count"><span>总张数</span><select data-field="count">${numericOptionMarkup(TOTAL_COUNT_OPTIONS)}</select></label>
                <label class="datang-id-photo__field" data-layout-control="columns"><span>每行张数</span><select data-field="columns">${numericOptionMarkup(GRID_COUNT_OPTIONS, true)}</select></label>
                <label class="datang-id-photo__field" data-layout-control="rows"><span>每列张数</span><select data-field="rows">${numericOptionMarkup(GRID_COUNT_OPTIONS, true)}</select></label>
                <label class="datang-id-photo__field" data-layout-control="spacing"><span>间距方案</span><select data-field="spacingPreset"><option value="studio_tight">影楼紧密</option><option value="cutting_gap">留缝裁切</option><option value="custom">自定义</option></select></label>
                <label class="datang-id-photo__field" data-layout-control="margin"><span>外边距（厘米）</span><input data-field="marginCm" type="number" min="0" max="10" step="0.1"></label>
                <label class="datang-id-photo__field" data-layout-control="gap"><span>照片间距（厘米）</span><input data-field="gapCm" type="number" min="0" max="10" step="0.1"></label>
                <label class="datang-id-photo__field" data-layout-control="dpi"><span>排版 DPI（未连接时）</span><input data-field="dpi" type="number" min="${MIN_DPI}" max="${MAX_DPI}" step="1"></label>
            </div>
        </details>
        <div class="datang-id-photo__schemes" aria-label="候选方案"></div>
        <div class="datang-id-photo__preview-shell">
            <div class="datang-id-photo__paper-wrap"><div class="datang-id-photo__paper"></div></div>
            <div class="datang-id-photo__summary">
                <strong data-summary-title>等待布局</strong>
                <p data-summary-detail></p>
                <div class="datang-id-photo__status" data-status hidden></div>
            </div>
        </div>
        <details><summary>高级：查看当前排版数据</summary><textarea data-json readonly spellcheck="false"></textarea></details>
    `;

    const elements = {
        builtInPresets: root.querySelector("[data-built-in-presets]"),
        quickLayout: root.querySelector("[data-quick-layout]"),
        externalSpec: root.querySelector("[data-external-spec]"),
        userPresets: root.querySelector("[data-user-presets]"),
        userPresetsWrap: root.querySelector("[data-user-presets-wrap]"),
        saveRow: root.querySelector("[data-save-row]"),
        presetName: root.querySelector("[data-preset-name]"),
        schemes: root.querySelector(".datang-id-photo__schemes"),
        paper: root.querySelector(".datang-id-photo__paper"),
        title: root.querySelector("[data-summary-title]"),
        detail: root.querySelector("[data-summary-detail]"),
        status: root.querySelector("[data-status]"),
        advanced: root.querySelector("[data-layout-advanced]"),
        json: root.querySelector("[data-json]"),
    };

    function setSummaryLines(lines) {
        elements.detail.replaceChildren(...lines.map((text) => {
            const line = document.createElement("span");
            line.className = "datang-id-photo__summary-line";
            line.textContent = text;
            return line;
        }));
    }

    const initialStoredSettings = settingsFromLayout(originalDataWidget.value);
    const initialPreview = previewFromLayout(originalDataWidget.value);
    const initialIsPlaceholder = initialPreview?.layoutId === "preview-default";
    let settings = normaliseSettings({
        ...(initialStoredSettings || DEFAULT_SETTINGS),
        dpi: Number(originalDpiWidget?.value ?? initialStoredSettings?.dpi ?? DEFAULT_DPI),
    });
    let selectedOrientation = settings.orientation === "auto" ? "" : settings.orientation;
    let externalLayout = initialStoredSettings || initialIsPlaceholder ? null : initialPreview;
    let userPresets = readUserPresets();
    let dataWidget = null;
    let dpiWidget = null;
    let uiFailed = false;
    let externalInputs = resolveExternalInputs(node);
    let externalInputsFingerprint = "";
    let manualPhotoSettings = {
        photoPresetId: settings.photoPresetId,
        customPhotoUnit: settings.customPhotoUnit,
        customPhotoWidth: settings.customPhotoWidth,
        customPhotoHeight: settings.customPhotoHeight,
    };
    let manualDpi = settings.dpi;

    function applyExternalValues(value = settings) {
        const next = { ...value };
        if (externalInputs.dpi.connected && externalInputs.dpi.resolved) next.dpi = externalInputs.dpi.value;
        if (externalInputs.photoSize.connected && externalInputs.photoSize.resolved) {
            Object.assign(next, {
                photoPresetId: "custom",
                customPhotoUnit: "px",
                customPhotoWidth: externalInputs.photoSize.width,
                customPhotoHeight: externalInputs.photoSize.height,
            });
        }
        return normaliseSettings(next);
    }

    function synchronizeExternalInputs({ force = false } = {}) {
        if (repairLegacyConvertedDpiInput(node)) force = true;
        const nextExternal = resolveExternalInputs(node);
        const nextFingerprint = externalFingerprint(nextExternal);
        if (!force && nextFingerprint === externalInputsFingerprint) return;
        const previous = externalInputs;
        if (!previous.photoSize.connected && nextExternal.photoSize.connected) {
            manualPhotoSettings = {
                photoPresetId: settings.photoPresetId,
                customPhotoUnit: settings.customPhotoUnit,
                customPhotoWidth: settings.customPhotoWidth,
                customPhotoHeight: settings.customPhotoHeight,
            };
        }
        if (!previous.dpi.connected && nextExternal.dpi.connected) manualDpi = settings.dpi;
        let nextSettings = { ...settings };
        if (previous.photoSize.connected && !nextExternal.photoSize.connected) Object.assign(nextSettings, manualPhotoSettings);
        if (previous.dpi.connected && !nextExternal.dpi.connected) nextSettings.dpi = manualDpi;
        externalInputs = nextExternal;
        externalInputsFingerprint = nextFingerprint;
        settings = applyExternalValues(nextSettings);
        if (externalInputs.photoSize.connected && externalInputs.photoSize.resolved) {
            const hasValidLayout = buildLayoutCandidates(settings).some((candidate) => candidate.valid);
            if (!hasValidLayout) {
                settings = applyExternalValues({ ...settings, layoutMode: "auto_fill", columns: 0, rows: 0 });
                selectedOrientation = "";
            }
        }
        renderManual();
    }

    function applyPreset(preset) {
        settings = applyExternalValues({ ...settings, ...preset.settings });
        selectedOrientation = settings.orientation === "auto" ? "" : settings.orientation;
        renderManual();
    }

    function createPresetButton(preset, userPreset = false) {
        const item = document.createElement(userPreset ? "div" : "button");
        if (userPreset) item.className = "datang-id-photo__user-item";
        const button = userPreset ? document.createElement("button") : item;
        button.type = "button";
        button.className = "datang-id-photo__preset";
        const title = document.createElement("strong");
        title.textContent = preset.name;
        const note = document.createElement("small");
        note.textContent = userPreset ? "我的预设" : preset.note;
        button.append(title, note);
        button.addEventListener("click", () => applyPreset(preset));
        if (!userPreset) return button;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.title = `删除“${preset.name}”`;
        remove.setAttribute("aria-label", remove.title);
        remove.textContent = "×";
        remove.addEventListener("click", () => {
            userPresets = userPresets.filter((item) => item.id !== preset.id);
            writeUserPresets(userPresets);
            renderPresets();
        });
        item.append(button, remove);
        return item;
    }

    function renderPresets() {
        elements.builtInPresets.replaceChildren(...BUILT_IN_LAYOUT_PRESETS.map((preset) => createPresetButton(preset)));
        elements.userPresets.replaceChildren(...userPresets.map((preset) => createPresetButton(preset, true)));
        elements.userPresetsWrap.hidden = userPresets.length === 0;
    }

    function previewDisplaySizes(preview) {
        const paperOrientation = preview.canvasWidth >= preview.canvasHeight ? "landscape" : "portrait";
        return {
            photo: orientedDisplaySize(
                ID_PHOTO_PRESETS,
                settings.photoPresetId,
                settings.customPhotoUnit,
                settings.customPhotoWidth,
                settings.customPhotoHeight,
                settings.photoOrientation,
            ),
            paper: orientedDisplaySize(
                PAPER_PRESETS,
                settings.paperPresetId,
                settings.customPaperUnit,
                settings.customPaperWidth,
                settings.customPaperHeight,
                paperOrientation,
            ),
        };
    }

    const resizeNode = () => {
        requestAnimationFrame(() => {
            node.setSize?.([
                Math.max(Number(node.size?.[0]) || 0, MIN_NODE_WIDTH),
                Math.max(Number(node.size?.[1]) || 0, MIN_NODE_HEIGHT),
            ]);
            node.setDirtyCanvas?.(true, true);
            app.graph?.setDirtyCanvas?.(true, true);
        });
    };

    function paintPreview(preview) {
        elements.paper.replaceChildren();
        if (!preview) {
            elements.paper.style.width = "100%";
            elements.paper.style.height = "160px";
            elements.paper.dataset.widthLabel = "";
            elements.paper.dataset.heightLabel = "";
            return;
        }
        const maxWidth = 320;
        const maxHeight = 255;
        const scale = Math.min(maxWidth / preview.canvasWidth, maxHeight / preview.canvasHeight);
        elements.paper.style.width = `${Math.max(12, Math.round(preview.canvasWidth * scale))}px`;
        elements.paper.style.height = `${Math.max(12, Math.round(preview.canvasHeight * scale))}px`;
        const displaySizes = previewDisplaySizes(preview);
        elements.paper.dataset.widthLabel = dimensionText(displaySizes.paper.width, displaySizes.paper.unit);
        elements.paper.dataset.heightLabel = dimensionText(displaySizes.paper.height, displaySizes.paper.unit);
        for (let index = 0; index < preview.slots.length; index += 1) {
            const slot = preview.slots[index];
            const block = document.createElement("span");
            block.className = "datang-id-photo__slot";
            const number = document.createElement("span");
            number.className = "datang-id-photo__slot-number";
            number.textContent = String(index + 1);
            const person = document.createElement("span");
            person.className = "datang-id-photo__person";
            person.classList.toggle("is-landscape", slot.width > slot.height);
            block.append(number, person);
            block.title = slot.sizeLabel
                ? `第 ${index + 1} 张 · ${slot.sizeLabel}`
                : `第 ${index + 1} 张 · ${dimensionText(displaySizes.photo.width, displaySizes.photo.unit)} × ${dimensionText(displaySizes.photo.height, displaySizes.photo.unit)}`;
            block.style.left = `${slot.x / preview.canvasWidth * 100}%`;
            block.style.top = `${slot.y / preview.canvasHeight * 100}%`;
            block.style.width = `${slot.width / preview.canvasWidth * 100}%`;
            block.style.height = `${slot.height / preview.canvasHeight * 100}%`;
            elements.paper.appendChild(block);
        }
        for (const mark of preview.cropMarks || []) {
            const line = document.createElement("span");
            line.className = "datang-id-photo__crop-mark";
            const left = Math.min(mark.x1, mark.x2);
            const top = Math.min(mark.y1, mark.y2);
            const horizontal = mark.y1 === mark.y2;
            line.style.left = `${left / preview.canvasWidth * 100}%`;
            line.style.top = `${top / preview.canvasHeight * 100}%`;
            line.style.width = horizontal ? `${(Math.abs(mark.x2 - mark.x1) + 1) / preview.canvasWidth * 100}%` : "1px";
            line.style.height = horizontal ? "1px" : `${(Math.abs(mark.y2 - mark.y1) + 1) / preview.canvasHeight * 100}%`;
            elements.paper.appendChild(line);
        }
    }

    function renderControls() {
        for (const input of root.querySelectorAll("[data-field]")) {
            const key = input.dataset.field;
            input.value = String(settings[key]);
            if (key.startsWith("custom") && (key.endsWith("Width") || key.endsWith("Height"))) {
                const unitKey = key.includes("Photo") ? "customPhotoUnit" : "customPaperUnit";
                input.step = settings[unitKey] === "px" ? "1" : "0.1";
                input.min = settings[unitKey] === "px" ? "1" : "0.1";
            }
        }
        const photoPreset = ID_PHOTO_PRESETS.find((item) => item.id === settings.photoPresetId) || ID_PHOTO_PRESETS[0];
        const paperPreset = PAPER_PRESETS.find((item) => item.id === settings.paperPresetId) || PAPER_PRESETS[0];
        const sizeDisplays = [
            {
                custom: photoPreset.id === "custom",
                preset: photoPreset,
                unit: "customPhotoUnit",
                width: "customPhotoWidth",
                height: "customPhotoHeight",
            },
            {
                custom: paperPreset.id === "custom",
                preset: paperPreset,
                unit: "customPaperUnit",
                width: "customPaperWidth",
                height: "customPaperHeight",
            },
        ];
        for (const display of sizeDisplays) {
            const unit = root.querySelector(`[data-field="${display.unit}"]`);
            const width = root.querySelector(`[data-field="${display.width}"]`);
            const height = root.querySelector(`[data-field="${display.height}"]`);
            const group = display.unit.includes("Photo") ? "photo" : "paper";
            const row = root.querySelector(`[data-size-row="${group}"]`);
            row?.classList.toggle("is-custom", display.custom);
            for (const control of root.querySelectorAll(`[data-custom-control="${group}"]`)) {
                control.hidden = !display.custom;
            }
            unit.disabled = !display.custom;
            width.disabled = !display.custom;
            height.disabled = !display.custom;
            if (!display.custom) {
                unit.value = display.preset.unit;
                width.value = String(display.preset.width);
                height.value = String(display.preset.height);
            }
        }
        const mixedPreset = settings.photoPresetId === ONE_TWO_MIXED_PRESET_ID;
        const photoLocked = externalInputs.photoSize.connected;
        const dpiLocked = externalInputs.dpi.connected;
        const externalInvalid = (photoLocked && (!externalInputs.photoSize.paired || !externalInputs.photoSize.resolved))
            || (dpiLocked && !externalInputs.dpi.resolved);
        elements.quickLayout.hidden = photoLocked;
        elements.externalSpec.hidden = !photoLocked && !dpiLocked;
        elements.externalSpec.classList.toggle("is-error", externalInvalid);
        if (!elements.externalSpec.hidden) {
            elements.externalSpec.replaceChildren();
            const title = document.createElement("strong");
            title.textContent = externalInvalid ? "外部规格暂不可用" : "外部规格已接管";
            const detail = document.createElement("span");
            detail.textContent = externalInvalid
                ? "请同时连接宽度和高度，并确认来源是可解析的尺寸预设节点。"
                : [
                    photoLocked ? `${externalInputs.photoSize.presetLabel || "外部尺寸"} · ${externalInputs.photoSize.width} × ${externalInputs.photoSize.height} 像素` : "",
                    dpiLocked ? `${externalInputs.dpi.value} DPI` : "",
                ].filter(Boolean).join(" · ");
            elements.externalSpec.append(title, detail);
        }
        const photoPresetInput = root.querySelector('[data-field="photoPresetId"]');
        if (photoPresetInput) photoPresetInput.disabled = photoLocked;
        for (const input of root.querySelectorAll('[data-field="customPhotoUnit"], [data-field="customPhotoWidth"], [data-field="customPhotoHeight"]')) {
            if (photoLocked) input.disabled = true;
        }
        const dpiInput = root.querySelector('[data-field="dpi"]');
        if (dpiInput) dpiInput.disabled = dpiLocked;
        const photoOrientation = root.querySelector('[data-field="photoOrientation"]');
        const paperPresetInput = root.querySelector('[data-field="paperPresetId"]');
        const canvasOrientation = root.querySelector('[data-field="orientation"]');
        const layoutMode = root.querySelector('[data-field="layoutMode"]');
        if (photoOrientation) photoOrientation.disabled = mixedPreset;
        if (paperPresetInput) paperPresetInput.disabled = mixedPreset;
        if (canvasOrientation) canvasOrientation.disabled = mixedPreset;
        if (layoutMode) layoutMode.disabled = mixedPreset;
        if (photoOrientation?.closest("label")) photoOrientation.closest("label").hidden = mixedPreset;
        if (canvasOrientation?.closest("label")) canvasOrientation.closest("label").hidden = mixedPreset;
        const visibility = {
            count: !mixedPreset && settings.layoutMode === "specified_count",
            columns: !mixedPreset && settings.layoutMode === "fixed_grid",
            rows: !mixedPreset && settings.layoutMode === "fixed_grid",
            spacing: !mixedPreset,
            margin: !mixedPreset && settings.spacingPreset === "custom",
            gap: !mixedPreset && settings.spacingPreset === "custom",
        };
        for (const [name, visible] of Object.entries(visibility)) {
            const control = root.querySelector(`[data-layout-control="${name}"]`);
            if (control) control.hidden = !visible;
        }
        elements.advanced.hidden = mixedPreset;
    }

    function renderManual({ write = true } = {}) {
        externalLayout = null;
        const candidates = buildLayoutCandidates(settings);
        let selected = candidates.find((candidate) => candidate.orientation === selectedOrientation && candidate.valid)
            || candidates.find((candidate) => candidate.valid)
            || candidates[0];
        if (selected?.valid) selectedOrientation = selected.orientation;
        elements.schemes.replaceChildren();
        for (const candidate of candidates) {
            const button = document.createElement("button");
            button.type = "button";
            button.disabled = !candidate.valid;
            button.classList.toggle("is-active", candidate.orientation === selected?.orientation);
            button.textContent = `${candidate.orientation === "portrait" ? "竖版" : "横版"} · ${candidate.columns} 列 × ${candidate.rows} 行`;
            button.addEventListener("click", () => {
                selectedOrientation = candidate.orientation;
                renderManual();
            });
            elements.schemes.appendChild(button);
        }
        elements.schemes.hidden = settings.orientation !== "auto" || candidates.length < 2;
        if (selected?.valid) {
            paintPreview(selected);
            const displaySizes = previewDisplaySizes(selected);
            elements.title.textContent = `${selected.canvasWidth} × ${selected.canvasHeight} 像素`;
            setSummaryLines(selected.mixed
                ? [
                    `画布 ${dimensionText(displaySizes.paper.width, displaySizes.paper.unit)} × ${dimensionText(displaySizes.paper.height, displaySizes.paper.unit)}`,
                    `照片 ${selected.photoSummary}`,
                    "单人混合排版",
                ]
                : [
                    `画布 ${dimensionText(displaySizes.paper.width, displaySizes.paper.unit)} × ${dimensionText(displaySizes.paper.height, displaySizes.paper.unit)}`,
                    `照片 ${dimensionText(displaySizes.photo.width, displaySizes.photo.unit)} × ${dimensionText(displaySizes.photo.height, displaySizes.photo.unit)}`,
                    `${selected.columns} 列 × ${selected.rows} 行 · ${selected.slotCount} 张`,
                ]);
            elements.status.hidden = true;
            elements.status.textContent = "";
            elements.json.value = selected.json;
            if (write) {
                dpiWidget?.writeFromUi(settings.dpi);
                dataWidget?.writeFromUi(selected.json);
            }
        } else {
            paintPreview(selected);
            elements.title.textContent = `当前最多预览 ${selected?.slotCount || 0} 张`;
            setSummaryLines(selected?.slotCount
                ? [
                    `${selected.previewColumns} 列 × ${selected.previewRows} 行`,
                    `已预览 ${selected.slotCount} 张`,
                    `还有 ${Math.max(0, selected.requestedCount - selected.slotCount)} 张未排入`,
                ]
                : ["当前纸张内没有可用照片位置"]);
            elements.status.className = "datang-id-photo__status is-error";
            elements.status.textContent = selected?.message || "没有可用布局。";
            elements.status.hidden = false;
            elements.json.value = "";
            if (write) dataWidget?.writeFromUi("");
        }
        renderControls();
        renderPresets();
        resizeNode();
    }

    function renderExternal(value) {
        const storedSettings = settingsFromLayout(value);
        if (storedSettings) {
            settings = storedSettings;
            selectedOrientation = settings.orientation === "auto" ? "" : settings.orientation;
            renderManual({ write: false });
            return;
        }
        externalLayout = previewFromLayout(value);
        if (!externalLayout) return;
        paintPreview(externalLayout);
        elements.schemes.replaceChildren();
        elements.schemes.hidden = true;
        elements.title.textContent = `${externalLayout.canvasWidth} × ${externalLayout.canvasHeight} 像素`;
        setSummaryLines([`${externalLayout.slotCount} 张`, "外部冻结布局"]);
        elements.status.hidden = true;
        elements.status.textContent = "";
        elements.json.value = String(value || "");
        renderControls();
        renderPresets();
        resizeNode();
    }

    dataWidget = hideDataWidget(node, originalDataWidget, renderExternal);
    dpiWidget = hideDataWidget(node, originalDpiWidget, (value) => {
        if (uiFailed) return;
        settings = normaliseSettings({ ...settings, dpi: value });
        renderManual();
    });
    if (!dataWidget || !dpiWidget) return null;

    const domWidget = node.addDOMWidget("证件照排版面板", "datang-id-photo", root, {
        getValue: () => "",
        setValue: () => {},
        getMinHeight: () => 590,
        getMaxHeight: () => Number.MAX_SAFE_INTEGER,
        hideOnZoom: false,
    });
    domWidget.serialize = false;

    for (const input of root.querySelectorAll("[data-field]")) {
        input.addEventListener("change", () => {
            const key = input.dataset.field;
            const numeric = input.type === "number" || ["count", "columns", "rows"].includes(key);
            const value = key === "cropMarksEnabled" ? input.value === "true" : numeric ? Number(input.value) : input.value;
            let patch = { [key]: value };
            if (key === "photoPresetId" && value === ONE_TWO_MIXED_PRESET_ID) {
                patch = { ...patch, paperPresetId: "seven-inch-paper", orientation: "portrait", photoOrientation: "original" };
            }
            if (key === "layoutMode" && value !== "auto_fill") elements.advanced.open = true;
            if (key === "spacingPreset" && value === "studio_tight") patch = { ...patch, marginCm: 0, gapCm: 0 };
            if (key === "spacingPreset" && value === "cutting_gap") patch = { ...patch, marginCm: 0.4, gapCm: 0.2 };
            if (key === "marginCm" || key === "gapCm") patch.spacingPreset = "custom";
            settings = applyExternalValues({ ...settings, ...patch });
            if (key === "orientation") selectedOrientation = settings.orientation === "auto" ? "" : settings.orientation;
            renderManual();
        });
    }
    root.querySelector('[data-preset-action="reset"]').addEventListener("click", () => {
        settings = applyExternalValues(DEFAULT_SETTINGS);
        selectedOrientation = "";
        renderManual();
    });
    root.querySelector('[data-preset-action="show-save"]').addEventListener("click", () => {
        elements.saveRow.hidden = false;
        elements.presetName.focus();
    });
    root.querySelector('[data-preset-action="cancel"]').addEventListener("click", () => {
        elements.saveRow.hidden = true;
        elements.presetName.value = "";
    });
    root.querySelector('[data-preset-action="save"]').addEventListener("click", () => {
        const name = elements.presetName.value.trim().slice(0, 24);
        if (!name) {
            elements.presetName.focus();
            return;
        }
        const existing = userPresets.find((item) => item.name === name);
        if (existing) {
            existing.settings = normaliseSettings(settings);
        } else if (userPresets.length < MAX_USER_PRESETS) {
            const preset = {
                id: globalThis.crypto?.randomUUID?.() || `preset-${Date.now()}-${Math.random().toString(16).slice(2)}`,
                name,
                settings: normaliseSettings(settings),
            };
            userPresets.push(preset);
        } else {
            elements.presetName.value = "最多保存 20 个预设";
            return;
        }
        if (!writeUserPresets(userPresets)) {
            elements.presetName.value = "浏览器未允许保存";
            return;
        }
        elements.saveRow.hidden = true;
        elements.presetName.value = "";
        renderPresets();
    });
    elements.presetName.addEventListener("keydown", (event) => {
        if (event.key === "Enter") root.querySelector('[data-preset-action="save"]').click();
        if (event.key === "Escape") root.querySelector('[data-preset-action="cancel"]').click();
    });
    let activeCanvasPointerId = null;
    root.addEventListener("pointerdown", (event) => {
        if (event.button !== 1) return;
        event.preventDefault();
        event.stopPropagation();
        activeCanvasPointerId = event.pointerId;
        root.setPointerCapture?.(event.pointerId);
        app.canvas?.processMouseDown?.(event);
    });
    root.addEventListener("pointermove", (event) => {
        if (event.pointerId !== activeCanvasPointerId || (event.buttons & 4) !== 4) return;
        event.preventDefault();
        event.stopPropagation();
        app.canvas?.processMouseMove?.(event);
    });
    const finishCanvasPan = (event) => {
        if (event.pointerId !== activeCanvasPointerId) return;
        if (event.type !== "pointercancel" && event.button !== 1) return;
        event.preventDefault();
        event.stopPropagation();
        app.canvas?.processMouseUp?.(event);
        if (root.hasPointerCapture?.(event.pointerId)) root.releasePointerCapture(event.pointerId);
        activeCanvasPointerId = null;
    };
    root.addEventListener("pointerup", finishCanvasPan);
    root.addEventListener("pointercancel", finishCanvasPan);
    root.addEventListener("auxclick", (event) => {
        if (event.button !== 1) return;
        event.preventDefault();
        event.stopPropagation();
    });
    root.addEventListener("wheel", (event) => {
        const target = event.target instanceof Element ? event.target : null;
        const textArea = target?.closest("textarea");
        if (canConsumeWheel(textArea, event.deltaY)) {
            event.stopPropagation();
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        forwardWheelToCanvas(event);
    }, { passive: false });
    try {
        if (externalLayout) renderExternal(dataWidget.value);
        else synchronizeExternalInputs({ force: true });
    } catch (error) {
        uiFailed = true;
        root.replaceChildren();
        const message = document.createElement("div");
        message.className = "datang-id-photo__status is-error";
        message.textContent = `证件照排版界面初始化失败：${error?.message || "未知错误"}`;
        root.appendChild(message);
        console.error("[Datang.IdPhotoLayout] initial render failed", error);
    }
    const externalTimer = globalThis.setInterval(() => {
        if (!uiFailed && node.graph) synchronizeExternalInputs();
    }, 350);
    domWidget.onRemove = () => globalThis.clearInterval(externalTimer);
    resizeNode();
    return domWidget;
}

app.registerExtension({
    name: "Datang.IdPhotoLayout",
    async nodeCreated(node) {
        if (node.comfyClass !== NODE_CLASS) return;
        try {
            installStyles();
            const originalDataWidget = node.widgets?.find((widget) => widget.name === DATA_WIDGET_NAME);
            const originalDpiWidget = node.widgets?.find((widget) => widget.name === DPI_WIDGET_NAME);
            if (!originalDataWidget || !originalDpiWidget) return;
            createUi(node, originalDataWidget, originalDpiWidget);
        } catch (error) {
            console.error("[Datang.IdPhotoLayout] nodeCreated failed", error);
        }
    },
});
