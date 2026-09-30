import assert from "node:assert/strict";
import test from "node:test";

import {
    applyAspectCropDisplayContract,
    FACE_COMPOSITION_INPUT_NAME,
    FACE_COMPOSITION_LABEL,
    CUSTOM_RATIO_LEGACY,
    LEGACY_RATIO_HEIGHT_NAME,
    LEGACY_RATIO_WIDTH_NAME,
    SQUARE_RATIO_LABEL,
    SQUARE_RATIO_LEGACY,
    SOURCE_RATIO_LABEL,
    SOURCE_RATIO_LEGACY,
} from "../web/aspect_crop_controls_core.js";

test("图像比例裁剪只改显示名并迁移旧原图比例文案", () => {
    const node = {
        widgets: [
            { name: FACE_COMPOSITION_INPUT_NAME, label: undefined, value: true },
            { name: "比例预设", value: SOURCE_RATIO_LEGACY },
            { name: LEGACY_RATIO_WIDTH_NAME, value: 3 },
            { name: LEGACY_RATIO_HEIGHT_NAME, value: 4 },
            { name: "脸部大小", value: 0.42 },
        ],
        setDirtyCanvas: (...args) => { node.dirty = args; },
    };

    assert.equal(applyAspectCropDisplayContract(node), true);
    assert.equal(node.widgets[0].name, FACE_COMPOSITION_INPUT_NAME);
    assert.equal(node.widgets[0].label, FACE_COMPOSITION_LABEL);
    assert.equal(node.widgets[0].value, true);
    assert.equal(node.widgets[1].value, SOURCE_RATIO_LABEL);
    assert.equal(node.widgets[2].value, 3);
    assert.equal(node.widgets[2].hidden, true);
    assert.equal(node.widgets[2].type, "converted-widget");
    assert.deepEqual(node.widgets[2].computeSize(), [0, -4]);
    assert.equal(node.widgets[3].hidden, true);
    assert.equal(node.widgets[4].value, 0.42);
    assert.deepEqual(node.dirty, [true, true]);
    assert.equal(applyAspectCropDisplayContract(node), false);
});

test("图像比例裁剪迁移旧正方形与自定义比例但不再显示自定义控件", () => {
    const buildNode = (ratio, width, height) => ({
        widgets: [
            { name: "比例预设", value: ratio },
            { name: LEGACY_RATIO_WIDTH_NAME, value: width },
            { name: LEGACY_RATIO_HEIGHT_NAME, value: height },
        ],
    });

    const square = buildNode(SQUARE_RATIO_LEGACY, 3, 4);
    applyAspectCropDisplayContract(square);
    assert.equal(square.widgets[0].value, SQUARE_RATIO_LABEL);

    const supportedCustom = buildNode(CUSTOM_RATIO_LEGACY, 8, 12);
    applyAspectCropDisplayContract(supportedCustom);
    assert.equal(supportedCustom.widgets[0].value, "2:3 标准竖版");

    const unsupportedCustom = buildNode(CUSTOM_RATIO_LEGACY, 5, 7);
    applyAspectCropDisplayContract(unsupportedCustom);
    assert.equal(unsupportedCustom.widgets[0].value, SOURCE_RATIO_LABEL);
    assert.equal(unsupportedCustom.widgets[1].type, "converted-widget");
    assert.equal(unsupportedCustom.widgets[2].type, "converted-widget");
});
