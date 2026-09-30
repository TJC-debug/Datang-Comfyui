export const ASPECT_CROP_NODE_ID = "DatangAspectCrop";
export const FACE_COMPOSITION_INPUT_NAME = "启用人脸识别";
export const FACE_COMPOSITION_LABEL = "按人脸构图";
export const SOURCE_RATIO_LEGACY = "保持原图比例";
export const SOURCE_RATIO_LABEL = "保持原图比例（不裁剪）";
export const SQUARE_RATIO_LEGACY = "1:1";
export const SQUARE_RATIO_LABEL = "1:1 正方形";
export const CUSTOM_RATIO_LEGACY = "自定义比例";
export const LEGACY_RATIO_WIDTH_NAME = "自定义比例宽";
export const LEGACY_RATIO_HEIGHT_NAME = "自定义比例高";

const SUPPORTED_LEGACY_RATIOS = new Map([
    ["1:1", SQUARE_RATIO_LABEL],
    ["3:4", "3:4 常用证件照"],
    ["4:5", "4:5 竖版证件照"],
    ["2:3", "2:3 标准竖版"],
]);

function hideLegacyRatioWidget(widget) {
    if (!widget || widget.__datangAspectCropHidden) return false;
    widget.__datangAspectCropHidden = true;
    widget.hidden = true;
    widget.type = "converted-widget";
    widget.computeSize = () => [0, -4];
    widget.computeLayoutSize = () => ({ minHeight: 0, maxHeight: 0, minWidth: 0 });
    widget.options ||= {};
    widget.options.getMinHeight = () => 0;
    widget.options.getMaxHeight = () => 0;
    const element = widget.element ?? widget.inputEl;
    if (element?.style) element.style.display = "none";
    element?.setAttribute?.("aria-hidden", "true");
    return true;
}

function greatestCommonDivisor(left, right) {
    let a = Math.max(1, Math.round(Math.abs(Number(left) || 1)));
    let b = Math.max(1, Math.round(Math.abs(Number(right) || 1)));
    while (b) [a, b] = [b, a % b];
    return a;
}

function migrateLegacyCustomRatio(width, height) {
    const divisor = greatestCommonDivisor(width, height);
    const key = `${Math.round(Number(width) || 1) / divisor}:${Math.round(Number(height) || 1) / divisor}`;
    return SUPPORTED_LEGACY_RATIOS.get(key) || SOURCE_RATIO_LABEL;
}

export function applyAspectCropDisplayContract(node) {
    let changed = false;
    const faceWidget = node?.widgets?.find(
        (widget) => widget?.name === FACE_COMPOSITION_INPUT_NAME
    );
    if (faceWidget && faceWidget.label !== FACE_COMPOSITION_LABEL) {
        faceWidget.label = FACE_COMPOSITION_LABEL;
        changed = true;
    }

    const ratioWidget = node?.widgets?.find((widget) => widget?.name === "比例预设");
    const widthWidget = node?.widgets?.find((widget) => widget?.name === LEGACY_RATIO_WIDTH_NAME);
    const heightWidget = node?.widgets?.find((widget) => widget?.name === LEGACY_RATIO_HEIGHT_NAME);
    if (ratioWidget?.value === SOURCE_RATIO_LEGACY) {
        ratioWidget.value = SOURCE_RATIO_LABEL;
        changed = true;
    } else if (ratioWidget?.value === SQUARE_RATIO_LEGACY) {
        ratioWidget.value = SQUARE_RATIO_LABEL;
        changed = true;
    } else if (ratioWidget?.value === CUSTOM_RATIO_LEGACY) {
        ratioWidget.value = migrateLegacyCustomRatio(widthWidget?.value, heightWidget?.value);
        changed = true;
    }
    changed = hideLegacyRatioWidget(widthWidget) || changed;
    changed = hideLegacyRatioWidget(heightWidget) || changed;

    if (changed) node?.setDirtyCanvas?.(true, true);
    return changed;
}
