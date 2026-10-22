import { app } from "../../../scripts/app.js";
import { applyBeautyDefaults, BEAUTY_NODE_DEFAULTS, applyBlemishMigration, BLEMISH_SCHEMA, BLEMISH_WIDGETS } from "./face_beauty_controls_core.js";

const RESET_WIDGET_NAME = "恢复默认";

app.registerExtension({
    name: "Datang.FaceBeautyControls",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        const defaults = BEAUTY_NODE_DEFAULTS[nodeData?.name];
        if (!defaults) return;

        if (nodeData.name === "DatangBlemishRetouch") {
            const configure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function(info) {
                const result = configure?.apply(this, arguments);
                const migration = applyBlemishMigration(this, info);
                if (migration.legacy) console.info("大汤痘印精修：旧检测控件已退役，已保留修复强度并载入新的祛痘和肤质默认值。");
                return result;
            };
            const serialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function(info) {
                const result = serialize?.apply(this, arguments);
                info.properties ??= {};
                info.properties.datang_blemish_schema = BLEMISH_SCHEMA;
                info.widgets_values = BLEMISH_WIDGETS.map(name => this.widgets?.find(widget => widget.name === name)?.value ?? defaults[name]);
                return result;
            };
        }

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function onNodeCreated() {
            const result = originalOnNodeCreated?.apply(this, arguments);
            if (nodeData.name === "DatangBlemishRetouch") {
                this.properties ??= {};
                this.properties.datang_blemish_schema = BLEMISH_SCHEMA;
            }
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
