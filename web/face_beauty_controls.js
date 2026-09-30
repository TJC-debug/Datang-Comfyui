import { app } from "../../../scripts/app.js";
import { applyBeautyDefaults, BEAUTY_NODE_DEFAULTS } from "./face_beauty_controls_core.js";

const RESET_WIDGET_NAME = "恢复默认";

app.registerExtension({
    name: "Datang.FaceBeautyControls",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const defaults = BEAUTY_NODE_DEFAULTS[nodeData?.name];
        if (!defaults) return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function onNodeCreated() {
            const result = originalOnNodeCreated?.apply(this, arguments);
            const existing = this.widgets?.find(
                (widget) => widget?.name === RESET_WIDGET_NAME && widget.__datangBeautyReset
            );
            if (!existing) {
                const resetWidget = this.addWidget(
                    "button",
                    RESET_WIDGET_NAME,
                    null,
                    () => applyBeautyDefaults(this, defaults),
                    { serialize: false }
                );
                resetWidget.__datangBeautyReset = true;
            }
            return result;
        };
    },
});
