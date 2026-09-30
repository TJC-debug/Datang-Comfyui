import { app } from "../../../scripts/app.js";
import {
    migrateRemovedRelightingDegree,
    RELIGHTING_PROMPT_NODE_ID,
} from "./relighting_prompt_controls_core.js";

function restoreCompactNodeSize(node) {
    const schedule = globalThis.requestAnimationFrame || ((callback) => setTimeout(callback, 0));
    schedule(() => {
        const width = Number(node.size?.[0]) || 0;
        const computed = node.computeSize?.();
        const computedHeight = Number(computed?.[1]) || 0;
        if (computedHeight > 0) {
            node.setSize?.([Math.max(width, Number(computed?.[0]) || width), computedHeight]);
            node.setDirtyCanvas?.(true, true);
        }
    });
}

app.registerExtension({
    name: "Datang.RelightingPromptControls",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== RELIGHTING_PROMPT_NODE_ID) return;

        const originalOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function onConfigure(serializedNode) {
            const result = originalOnConfigure?.apply(this, arguments);
            if (migrateRemovedRelightingDegree(this, serializedNode)) {
                restoreCompactNodeSize(this);
            }
            return result;
        };
    },
});
