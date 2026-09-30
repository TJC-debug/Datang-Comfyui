import test from "node:test";
import assert from "node:assert/strict";

import {
    buildLayoutCandidates,
    clipCropMarksToWhitespace,
    DEFAULT_SETTINGS,
    GRID_COUNT_OPTIONS,
    ID_PHOTO_PRESETS,
    PAPER_PRESETS,
    previewFromLayout,
    settingsFromLayout,
    TOTAL_COUNT_OPTIONS,
} from "../web/id_photo_layout_core.js";

test("裁剪线只保留照片槽位之外的线段", () => {
    const safe = clipCropMarksToWhitespace(
        [{ x1: 0, y1: 50, x2: 200, y2: 50, width: 1 }],
        [{ x: 20, y: 30, width: 120, height: 160 }],
    );
    assert.deepEqual(safe, [
        { x1: 0, y1: 50, x2: 19, y2: 50, width: 1 },
        { x1: 140, y1: 50, x2: 200, y2: 50, width: 1 },
    ]);
});

test("ComfyUI 界面包含参考预设并保留自定义照片和画布", () => {
    assert.ok(ID_PHOTO_PRESETS.some((item) => item.label.includes("司法考试照")));
    assert.ok(ID_PHOTO_PRESETS.some((item) => item.id === "custom"));
    assert.ok(PAPER_PRESETS.some((item) => item.id === "six-inch-paper"));
    assert.ok(PAPER_PRESETS.some((item) => item.id === "seven-inch-paper"));
    assert.ok(PAPER_PRESETS.some((item) => item.id === "eight-by-twelve-paper"));
    assert.ok(PAPER_PRESETS.some((item) => item.id === "twelve-by-eighteen-paper"));
    assert.ok(PAPER_PRESETS.some((item) => item.id === "a3-paper"));
    assert.ok(PAPER_PRESETS.some((item) => item.id === "custom"));
});

test("总张数与行列枚举覆盖常用排版组合", () => {
    assert.deepEqual(TOTAL_COUNT_OPTIONS, [1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24, 25, 30, 36, 40, 50]);
    assert.deepEqual(GRID_COUNT_OPTIONS, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
});

test("默认界面使用六寸横版自动铺满十二张", () => {
    const candidates = buildLayoutCandidates(DEFAULT_SETTINGS);
    assert.equal(candidates.length, 1);
    assert.ok(candidates[0].valid);
    assert.equal(candidates[0].slotCount, 12);
    const contract = JSON.parse(candidates[0].json);
    assert.equal(contract.schemaVersion, 1);
    assert.equal(contract.slots.length, 12);
    assert.equal(contract._ui.settings.layoutMode, "auto_fill");
});

test("自定义像素尺寸、固定方向和数量会进入冻结布局", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        photoPresetId: "custom",
        customPhotoUnit: "px",
        customPhotoWidth: 200,
        customPhotoHeight: 300,
        paperPresetId: "custom",
        customPaperUnit: "px",
        customPaperWidth: 1200,
        customPaperHeight: 800,
        orientation: "landscape",
        layoutMode: "specified_count",
        count: 6,
        marginCm: 0,
        gapCm: 0,
        mode: "compact",
    });
    assert.equal(candidate.valid, true);
    assert.equal(candidate.canvasWidth, 1200);
    assert.equal(candidate.canvasHeight, 800);
    assert.equal(candidate.slotCount, 6);
    assert.deepEqual(candidate.slots[0].width, 200);
});

test("界面合同冻结 DPI 并可恢复手动设置和预览", () => {
    const first = buildLayoutCandidates(DEFAULT_SETTINGS).find((item) => item.valid);
    const contract = JSON.parse(first.json);
    assert.equal(contract.dpi, 300);
    assert.equal(contract._ui.settings.dpi, 300);
    assert.deepEqual(settingsFromLayout(first.json), DEFAULT_SETTINGS);
    const preview = previewFromLayout(first.json);
    assert.equal(preview.canvasWidth, first.canvasWidth);
    assert.equal(preview.slotCount, 12);
});

test("厘米规格随 DPI 改变像素，像素规格保持原值", () => {
    const at300 = buildLayoutCandidates({ ...DEFAULT_SETTINGS, dpi: 300 })[0];
    const at600 = buildLayoutCandidates({ ...DEFAULT_SETTINGS, dpi: 600 })[0];
    assert.ok(Math.abs(at600.canvasWidth - at300.canvasWidth * 2) <= 1);
    assert.ok(Math.abs(at600.canvasHeight - at300.canvasHeight * 2) <= 1);

    const pixelBased = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        dpi: 600,
        photoPresetId: "custom",
        customPhotoUnit: "px",
        customPhotoWidth: 200,
        customPhotoHeight: 300,
        paperPresetId: "custom",
        customPaperUnit: "px",
        customPaperWidth: 1200,
        customPaperHeight: 800,
        orientation: "landscape",
    })[0];
    assert.equal(pixelBased.canvasWidth, 1200);
    assert.equal(pixelBased.canvasHeight, 800);
    assert.equal(pixelBased.slots[0].width, 200);
});

test("相同参数的 layoutId 和像素坐标稳定一致", () => {
    const left = buildLayoutCandidates(DEFAULT_SETTINGS)[0];
    const right = buildLayoutCandidates({ ...DEFAULT_SETTINGS })[0];
    assert.equal(left.layoutId, right.layoutId);
    assert.deepEqual(left.slots, right.slots);
});

test("空间不足时明确返回不可执行候选", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        photoPresetId: "three-inch",
        paperPresetId: "five-inch-paper",
        orientation: "portrait",
        layoutMode: "specified_count",
        count: 20,
    });
    assert.equal(candidate.valid, false);
    assert.ok(candidate.slotCount > 0);
    assert.ok(candidate.slotCount < 20);
    assert.match(candidate.message, /最多放/);
});

test("固定列数和行数不会被算法擅自更改", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        orientation: "landscape",
        layoutMode: "fixed_grid",
        count: 6,
        columns: 3,
        rows: 2,
    });
    assert.equal(candidate.valid, true);
    assert.equal(candidate.columns, 3);
    assert.equal(candidate.rows, 2);
    assert.equal(candidate.slotCount, 6);
    const contract = JSON.parse(candidate.json);
    assert.equal(contract.settings.columns, 3);
    assert.equal(contract.settings.rows, 2);
});

test("固定行列直接以网格容量作为总张数", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        orientation: "landscape",
        layoutMode: "fixed_grid",
        count: 7,
        columns: 3,
        rows: 2,
    });
    assert.equal(candidate.valid, true);
    assert.equal(candidate.capacity, 6);
    assert.equal(candidate.requestedCount, 6);
    assert.equal(candidate.slotCount, 6);
});

test("只固定一项时另一项按总张数确定", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        orientation: "landscape",
        layoutMode: "fixed_grid",
        count: 8,
        columns: 4,
        rows: 0,
    });
    assert.equal(candidate.valid, true);
    assert.equal(candidate.columns, 4);
    assert.equal(candidate.rows, 2);
});

test("照片方向可独立于画布方向切换宽高", () => {
    const base = {
        ...DEFAULT_SETTINGS,
        paperPresetId: "custom",
        customPaperUnit: "px",
        customPaperWidth: 1200,
        customPaperHeight: 1200,
        orientation: "landscape",
        layoutMode: "specified_count",
        count: 1,
        marginCm: 0,
        gapCm: 0,
    };
    const [portrait] = buildLayoutCandidates({ ...base, photoOrientation: "portrait" });
    const [landscape] = buildLayoutCandidates({ ...base, photoOrientation: "landscape" });
    assert.equal(JSON.parse(portrait.json).imageOrientation, "portrait");
    assert.equal(JSON.parse(landscape.json).imageOrientation, "landscape");
    assert.ok(portrait.slots[0].width < portrait.slots[0].height);
    assert.ok(landscape.slots[0].width > landscape.slots[0].height);
    assert.equal(portrait.slots[0].width, landscape.slots[0].height);
    assert.equal(portrait.slots[0].height, landscape.slots[0].width);
});

test("照片间距独立控制疏密且裁切线开关不改变槽位", () => {
    const base = {
        ...DEFAULT_SETTINGS,
        orientation: "landscape",
        layoutMode: "fixed_grid",
        count: 4,
        columns: 2,
        rows: 2,
        gapCm: 0.35,
    };
    const [visible] = buildLayoutCandidates({ ...base, cropMarksEnabled: true });
    const [hidden] = buildLayoutCandidates({ ...base, cropMarksEnabled: false });
    assert.deepEqual(visible.slots, hidden.slots);
    assert.ok(visible.cropMarks.length > 0);
    assert.equal(hidden.cropMarks.length, 0);
});

test("旧版紧凑模式合同恢复为不显示裁切线", () => {
    const restored = settingsFromLayout(JSON.stringify({
        schemaVersion: 1,
        layoutId: "legacy-compact",
        canvas: { width: 600, height: 400 },
        slots: [{ x: 0, y: 0, width: 100, height: 100 }],
        cropMarks: [],
        _ui: { settings: { ...DEFAULT_SETTINGS, cropMarksEnabled: undefined, mode: "compact" } },
    }));
    assert.equal(restored.cropMarksEnabled, false);
});

test("影楼紧密方案在六寸纸上排十二张一寸照", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        photoPresetId: "one-inch",
        paperPresetId: "six-inch-paper",
        orientation: "landscape",
        layoutMode: "specified_count",
        count: 12,
        columns: 0,
        rows: 0,
        spacingPreset: "studio_tight",
        marginCm: 0,
        gapCm: 0,
    });
    assert.equal(candidate.valid, true);
    assert.equal(candidate.columns, 6);
    assert.equal(candidate.rows, 2);
    assert.equal(candidate.slotCount, 12);
});

test("影楼紧密方案在六寸纸上优先完整三乘二的六张二寸照", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        photoPresetId: "two-inch",
        paperPresetId: "six-inch-paper",
        orientation: "landscape",
        layoutMode: "specified_count",
        count: 6,
        columns: 0,
        rows: 0,
        spacingPreset: "studio_tight",
        marginCm: 0,
        gapCm: 0,
    });
    assert.equal(candidate.valid, true);
    assert.equal(candidate.columns, 3);
    assert.equal(candidate.rows, 2);
    assert.equal(candidate.slotCount, 6);
});

test("五寸纸按留缝方案固定排四张二寸照", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        photoPresetId: "two-inch",
        paperPresetId: "five-inch-paper",
        photoOrientation: "original",
        orientation: "portrait",
        layoutMode: "fixed_grid",
        count: 4,
        columns: 2,
        rows: 2,
        spacingPreset: "cutting_gap",
        marginCm: 0.4,
        gapCm: 0.2,
        cropMarksEnabled: true,
    });
    assert.equal(candidate.valid, true);
    assert.equal(candidate.columns, 2);
    assert.equal(candidate.rows, 2);
    assert.equal(candidate.slotCount, 4);
    assert.ok(candidate.slots.every((slot) => slot.width === 413 && slot.height === 579));
    assert.ok(candidate.cropMarks.length > 0);
});

test("七寸纸单人混排固定生成八张一寸竖版和四张二寸横放", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        photoPresetId: "one-two-mixed",
        paperPresetId: "seven-inch-paper",
        orientation: "portrait",
        cropMarksEnabled: true,
    });
    assert.equal(candidate.valid, true);
    assert.equal(candidate.mixed, true);
    assert.equal(candidate.canvasWidth, 1500);
    assert.equal(candidate.canvasHeight, 2102);
    assert.equal(candidate.slotCount, 12);
    assert.equal(candidate.photoSummary, "1寸竖版 8张 + 2寸横放 4张");
    const sizes = candidate.slots.reduce((result, slot) => {
        const key = `${slot.width}x${slot.height}@${slot.rotation}`;
        result[key] = (result[key] || 0) + 1;
        return result;
    }, {});
    assert.deepEqual(sizes, { "295x413@0": 8, "579x413@90": 4 });
    assert.ok(candidate.cropMarks.length > 0);
});

test("六寸纸十二张一寸照在留缝参数下预览十张并报告未排入数量", () => {
    const [candidate] = buildLayoutCandidates({
        ...DEFAULT_SETTINGS,
        photoPresetId: "one-inch",
        paperPresetId: "six-inch-paper",
        orientation: "landscape",
        layoutMode: "specified_count",
        count: 12,
        spacingPreset: "cutting_gap",
        marginCm: 0.4,
        gapCm: 0.2,
    });
    assert.equal(candidate.valid, false);
    assert.equal(candidate.slotCount, 10);
    assert.equal(candidate.previewColumns, 5);
    assert.equal(candidate.previewRows, 2);
});
