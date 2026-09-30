import { app } from "../../../scripts/app.js";
import {
    applyAspectCropDisplayContract,
    ASPECT_CROP_NODE_ID,
} from "./aspect_crop_controls_core.js";

function restoreCompactNodeSize(node) {
    const schedule = globalThis.requestAnimationFrame || ((callback) => setTimeout(callback, 0));
    schedule(() => {
        const currentWidth = Number(node.size?.[0]) || 0;
        const computed = node.computeSize?.();
        const computedWidth = Number(computed?.[0]) || currentWidth;
        const computedHeight = Number(computed?.[1]) || Number(node.size?.[1]) || 0;
        if (computedHeight > 0) {
            node.setSize?.([Math.max(currentWidth, computedWidth), computedHeight]);
            node.setDirtyCanvas?.(true, true);
        }
    });
}

app.registerExtension({
    name: "Datang.AspectCropControls",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== ASPECT_CROP_NODE_ID) return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function onNodeCreated() {
            const result = originalOnNodeCreated?.apply(this, arguments);
            applyAspectCropDisplayContract(this);
            restoreCompactNodeSize(this);
            return result;
        };

        const originalOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function onConfigure() {
            const result = originalOnConfigure?.apply(this, arguments);
            applyAspectCropDisplayContract(this);
            restoreCompactNodeSize(this);
            return result;
        };
    },
});
