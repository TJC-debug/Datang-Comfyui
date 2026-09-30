import assert from "node:assert/strict";
import test from "node:test";

import {
    applyBeautyDefaults,
    BEAUTY_NODE_DEFAULTS,
} from "../web/face_beauty_controls_core.js";

test("快速美颜和痘印精修分别保留稳定默认值", () => {
    assert.deepEqual(Object.keys(BEAUTY_NODE_DEFAULTS), [
        "DatangFastFaceBeauty",
        "DatangBlemishRetouch",
    ]);
    assert.equal(BEAUTY_NODE_DEFAULTS.DatangFastFaceBeauty.磨皮, 45);
    assert.equal(BEAUTY_NODE_DEFAULTS.DatangBlemishRetouch.五官边缘保护, 78);
});

test("恢复默认只重置参数控件并触发节点刷新", () => {
    const callbacks = [];
    const node = {
        widgets: [
            { name: "图像", value: "keep" },
            { name: "修复强度", value: 3, callback: (value) => callbacks.push(value) },
            { name: "检测灵敏度", value: 99 },
        ],
        setDirtyCanvas: (...args) => { node.dirty = args; },
    };
    assert.equal(
        applyBeautyDefaults(node, BEAUTY_NODE_DEFAULTS.DatangBlemishRetouch),
        true
    );
    assert.equal(node.widgets[0].value, "keep");
    assert.equal(node.widgets[1].value, 85);
    assert.equal(node.widgets[2].value, 58);
    assert.deepEqual(callbacks, [85]);
    assert.deepEqual(node.dirty, [true, true]);
});

test("无匹配控件时恢复默认不制造伪修改", () => {
    assert.equal(applyBeautyDefaults({ widgets: [] }, { 磨皮: 45 }), false);
});
