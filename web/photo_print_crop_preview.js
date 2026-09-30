import { app } from "../../../scripts/app.js";
import { VISIBLE_CROP_METHODS } from "./photo_print_crop_preview_core.js";

const NODE_CLASS = "DatangPhotoPrintCrop";
const LEGACY_CROP_METHOD = "指定焦点裁剪";
const LEGACY_PREVIEW_MIN_HEIGHT = 560;

function widgetByName(node, name) {
    return node.widgets?.find((widget) => String(widget?.name || "") === name);
}

function hideNativeWidget(widget) {
    if (!widget || widget.__datangPhotoCropHidden) return;
    widget.__datangPhotoCropHidden = true;
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
}

export function simplifyPhotoCropWidgets(node) {
    const methodWidget = widgetByName(node, "裁剪方式");
    const focusWidget = widgetByName(node, "焦点位置");
    let migrated = false;
    if (Array.isArray(methodWidget?.options?.values)) {
        methodWidget.options.values = methodWidget.options.values.filter((value) => VISIBLE_CROP_METHODS.includes(value));
    }
    if (methodWidget?.value === LEGACY_CROP_METHOD) {
        methodWidget.value = "居中裁剪";
        migrated = true;
    }
    if (focusWidget) {
        if (focusWidget.value !== "居中") {
            focusWidget.value = "居中";
            migrated = true;
        }
        hideNativeWidget(focusWidget);
    }
    if (migrated) node.setDirtyCanvas?.(true, true);
    return migrated;
}

function restoreCompactNodeSize(node) {
    requestAnimationFrame(() => {
        const currentWidth = Number(node.size?.[0]) || 0;
        const currentHeight = Number(node.size?.[1]) || 0;
        const computed = node.computeSize?.();
        const computedWidth = Number(computed?.[0]) || currentWidth;
        const computedHeight = Number(computed?.[1]) || currentHeight;
        if (currentHeight >= LEGACY_PREVIEW_MIN_HEIGHT && computedHeight > 0 && computedHeight < currentHeight) {
            node.setSize?.([Math.max(currentWidth, computedWidth), computedHeight]);
            node.setDirtyCanvas?.(true, true);
        }
    });
}

app.registerExtension({
    name: "Datang.PhotoPrintCropControls",
    async nodeCreated(node) {
        if (node.comfyClass !== NODE_CLASS) return;
        try {
            simplifyPhotoCropWidgets(node);
            restoreCompactNodeSize(node);
            const previousOnConfigure = node.onConfigure;
            node.onConfigure = function onConfigure(info) {
                const result = previousOnConfigure?.apply(this, arguments);
                simplifyPhotoCropWidgets(this);
                restoreCompactNodeSize(this);
                return result;
            };
        } catch (error) {
            console.error("[Datang.PhotoPrintCropControls] nodeCreated failed", error);
        }
    },
});
