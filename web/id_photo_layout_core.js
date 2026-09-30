export const DEFAULT_DPI = 300;
export const MIN_DPI = 72;
export const MAX_DPI = 1200;
const CUSTOM_ID = "custom";
export const ONE_TWO_MIXED_PRESET_ID = "one-two-mixed";

export const ID_PHOTO_PRESETS = [
    { id: "one-inch", label: "1寸（2.5 × 3.5 厘米）", unit: "cm", width: 2.5, height: 3.5 },
    { id: "large-one-inch", label: "大1寸（3.3 × 4.8 厘米）", unit: "cm", width: 3.3, height: 4.8 },
    { id: "small-two-inch", label: "小2寸（3.5 × 4.5 厘米）", unit: "cm", width: 3.5, height: 4.5 },
    { id: "two-inch", label: "2寸（3.5 × 4.9 厘米）", unit: "cm", width: 3.5, height: 4.9 },
    { id: ONE_TWO_MIXED_PRESET_ID, label: "1寸 + 2寸混合（8张 + 4张）", unit: "cm", width: 2.5, height: 3.5 },
    { id: "large-two-inch", label: "大2寸（3.5 × 5.3 厘米）", unit: "cm", width: 3.5, height: 5.3 },
    { id: "three-inch", label: "3寸（5.5 × 8.5 厘米）", unit: "cm", width: 5.5, height: 8.5 },
    { id: "id-social", label: "身份证/社保（2.6 × 3.2 厘米）", unit: "cm", width: 2.6, height: 3.2 },
    { id: "driver-license", label: "驾驶证（2.2 × 3.2 厘米）", unit: "cm", width: 2.2, height: 3.2 },
    { id: "japan-visa", label: "日签（4.5 × 4.5 厘米）", unit: "cm", width: 4.5, height: 4.5 },
    { id: "us-visa", label: "美签（5.1 × 5.1 厘米）", unit: "cm", width: 5.1, height: 5.1 },
    { id: "graduate-exam", label: "研究生考试（3.0 × 4.0 厘米）", unit: "cm", width: 3, height: 4 },
    { id: "id-electronic", label: "身份证电子（358 × 441 像素）", unit: "px", width: 358, height: 441 },
    { id: "mandarin-exam", label: "普通话考试（390 × 567 像素）", unit: "px", width: 390, height: 567 },
    { id: "teacher-exam", label: "教师资格证（480 × 640 像素）", unit: "px", width: 480, height: 640 },
    { id: "nurse-exam", label: "护士资格证（160 × 210 像素）", unit: "px", width: 160, height: 210 },
    { id: "judicial-exam", label: "司法考试照（413 × 626 像素）", unit: "px", width: 413, height: 626 },
    { id: "medical-exam", label: "执业医考照（354 × 472 像素）", unit: "px", width: 354, height: 472 },
    { id: CUSTOM_ID, label: "自定义尺寸", unit: "cm", width: 2.5, height: 3.5 },
];

export const PAPER_PRESETS = [
    { id: "wallet-paper", label: "钱包照（5.0 × 8.9 厘米）", unit: "cm", width: 5, height: 8.9 },
    { id: "five-inch-paper", label: "3R / 5寸（8.9 × 12.7 厘米）", unit: "cm", width: 8.9, height: 12.7 },
    { id: "six-inch-paper", label: "4R / 6寸（10.2 × 15.2 厘米）", unit: "cm", width: 10.2, height: 15.2 },
    { id: "seven-inch-paper", label: "5R / 7寸（12.7 × 17.8 厘米）", unit: "cm", width: 12.7, height: 17.8 },
    { id: "eight-inch-paper", label: "6R / 8寸（15.2 × 20.3 厘米）", unit: "cm", width: 15.2, height: 20.3 },
    { id: "ten-inch-paper", label: "8R / 10寸（20.3 × 25.4 厘米）", unit: "cm", width: 20.3, height: 25.4 },
    { id: "eight-by-twelve-paper", label: "8 × 12 英寸（20.3 × 30.5 厘米）", unit: "cm", width: 20.3, height: 30.5 },
    { id: "ten-by-twelve-paper", label: "10 × 12 英寸（25.4 × 30.5 厘米）", unit: "cm", width: 25.4, height: 30.5 },
    { id: "twelve-by-eighteen-paper", label: "12 × 18 英寸（30.5 × 45.7 厘米）", unit: "cm", width: 30.5, height: 45.7 },
    { id: "square-five-paper", label: "5 × 5 方形相纸（12.7 × 12.7 厘米）", unit: "cm", width: 12.7, height: 12.7 },
    { id: "a5-paper", label: "A5（14.8 × 21.0 厘米）", unit: "cm", width: 14.8, height: 21 },
    { id: "a4-paper", label: "A4（21.0 × 29.7 厘米）", unit: "cm", width: 21, height: 29.7 },
    { id: "a3-paper", label: "A3（29.7 × 42.0 厘米）", unit: "cm", width: 29.7, height: 42 },
    { id: CUSTOM_ID, label: "自定义画布", unit: "cm", width: 10.1, height: 15.2 },
];

export const DEFAULT_SETTINGS = Object.freeze({
    dpi: DEFAULT_DPI,
    photoPresetId: "one-inch",
    customPhotoUnit: "cm",
    customPhotoWidth: 2.5,
    customPhotoHeight: 3.5,
    paperPresetId: "six-inch-paper",
    customPaperUnit: "cm",
    customPaperWidth: 10.1,
    customPaperHeight: 15.2,
    photoOrientation: "original",
    orientation: "landscape",
    layoutMode: "auto_fill",
    count: 12,
    columns: 0,
    rows: 0,
    mode: "easy_cut",
    cropMarksEnabled: true,
    spacingPreset: "studio_tight",
    marginCm: 0,
    gapCm: 0,
});

export const TOTAL_COUNT_OPTIONS = Object.freeze([
    1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24, 25, 30, 36, 40, 50,
]);

export const GRID_COUNT_OPTIONS = Object.freeze([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);

function finiteNumber(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
}

export function normaliseSettings(value = {}) {
    const raw = value && typeof value === "object" ? value : {};
    const settings = { ...DEFAULT_SETTINGS, ...raw };
    const photoIds = new Set(ID_PHOTO_PRESETS.map((item) => item.id));
    const paperIds = new Set(PAPER_PRESETS.map((item) => item.id));
    const hasCropMarksSetting = Object.prototype.hasOwnProperty.call(raw, "cropMarksEnabled");
    const cropMarksEnabled = hasCropMarksSetting
        ? raw.cropMarksEnabled === true || raw.cropMarksEnabled === "true"
        : settings.mode !== "compact";
    const rawMargin = Math.max(0, Math.min(10, finiteNumber(settings.marginCm, DEFAULT_SETTINGS.marginCm)));
    const rawGap = Math.max(0, Math.min(10, finiteNumber(settings.gapCm, DEFAULT_SETTINGS.gapCm)));
    const spacingPreset = ["studio_tight", "cutting_gap", "custom"].includes(raw.spacingPreset)
        ? raw.spacingPreset
        : rawMargin === 0 && rawGap === 0
            ? "studio_tight"
            : rawMargin === 0.4 && rawGap === 0.2
                ? "cutting_gap"
                : "custom";
    const photoPresetId = photoIds.has(settings.photoPresetId) ? settings.photoPresetId : DEFAULT_SETTINGS.photoPresetId;
    const storedLayoutMode = ["auto_fill", "specified_count", "fixed_grid", "template"].includes(raw.layoutMode)
        ? raw.layoutMode
        : null;
    const inferredLayoutMode = Number(settings.columns) > 0 || Number(settings.rows) > 0
        ? "fixed_grid"
        : "specified_count";
    const layoutMode = photoPresetId === ONE_TWO_MIXED_PRESET_ID
        ? "template"
        : storedLayoutMode === "template"
            ? "auto_fill"
            : storedLayoutMode || inferredLayoutMode;
    return {
        dpi: Math.max(MIN_DPI, Math.min(MAX_DPI, Math.round(finiteNumber(settings.dpi, DEFAULT_DPI)))),
        photoPresetId,
        customPhotoUnit: settings.customPhotoUnit === "px" ? "px" : "cm",
        customPhotoWidth: Math.max(0.1, finiteNumber(settings.customPhotoWidth, DEFAULT_SETTINGS.customPhotoWidth)),
        customPhotoHeight: Math.max(0.1, finiteNumber(settings.customPhotoHeight, DEFAULT_SETTINGS.customPhotoHeight)),
        paperPresetId: paperIds.has(settings.paperPresetId) ? settings.paperPresetId : DEFAULT_SETTINGS.paperPresetId,
        customPaperUnit: settings.customPaperUnit === "px" ? "px" : "cm",
        customPaperWidth: Math.max(0.1, finiteNumber(settings.customPaperWidth, DEFAULT_SETTINGS.customPaperWidth)),
        customPaperHeight: Math.max(0.1, finiteNumber(settings.customPaperHeight, DEFAULT_SETTINGS.customPaperHeight)),
        photoOrientation: ["original", "portrait", "landscape"].includes(settings.photoOrientation)
            ? settings.photoOrientation
            : "original",
        orientation: ["auto", "portrait", "landscape"].includes(settings.orientation) ? settings.orientation : "auto",
        layoutMode,
        count: Math.max(1, Math.min(200, Math.round(finiteNumber(settings.count, DEFAULT_SETTINGS.count)))),
        columns: Math.max(0, Math.min(50, Math.round(finiteNumber(settings.columns, DEFAULT_SETTINGS.columns)))),
        rows: Math.max(0, Math.min(50, Math.round(finiteNumber(settings.rows, DEFAULT_SETTINGS.rows)))),
        mode: cropMarksEnabled ? "easy_cut" : "compact",
        cropMarksEnabled,
        spacingPreset,
        marginCm: rawMargin,
        gapCm: rawGap,
    };
}

function pixelsPerCm(dpi) {
    return dpi / 2.54;
}

function positivePixels(value, unit, dpi) {
    return Math.max(1, Math.round(finiteNumber(value, 1) * (unit === "cm" ? pixelsPerCm(dpi) : 1)));
}

function distancePixels(value, dpi) {
    return Math.max(0, Math.round(finiteNumber(value, 0) * pixelsPerCm(dpi)));
}

function resolveSize(presets, presetId, customUnit, customWidth, customHeight, dpi) {
    const preset = presets.find((item) => item.id === presetId) || presets[0];
    if (preset.id === CUSTOM_ID) {
        return {
            width: positivePixels(customWidth, customUnit, dpi),
            height: positivePixels(customHeight, customUnit, dpi),
        };
    }
    return { width: positivePixels(preset.width, preset.unit, dpi), height: positivePixels(preset.height, preset.unit, dpi) };
}

function applyOrientation(size, orientation) {
    if (orientation === "portrait" && size.width > size.height) {
        return { width: size.height, height: size.width };
    }
    if (orientation === "landscape" && size.width < size.height) {
        return { width: size.height, height: size.width };
    }
    return size;
}

function stableStringify(value) {
    if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
    if (value && typeof value === "object") {
        return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
}

function fnv1a(value) {
    let hash = 0x811c9dc5;
    for (let index = 0; index < value.length; index += 1) {
        hash ^= value.charCodeAt(index);
        hash = Math.imul(hash, 0x01000193);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
}

export function clipCropMarksToWhitespace(marks, slots) {
    const safeMarks = [];
    for (const mark of marks) {
        const horizontal = mark.y1 === mark.y2;
        const fixed = horizontal ? mark.y1 : mark.x1;
        let intervals = [[
            Math.min(horizontal ? mark.x1 : mark.y1, horizontal ? mark.x2 : mark.y2),
            Math.max(horizontal ? mark.x1 : mark.y1, horizontal ? mark.x2 : mark.y2),
        ]];
        for (const slot of slots) {
            const crossesSlot = horizontal
                ? fixed >= slot.y && fixed < slot.y + slot.height
                : fixed >= slot.x && fixed < slot.x + slot.width;
            if (!crossesSlot) continue;
            const blockedStart = horizontal ? slot.x : slot.y;
            const blockedEnd = blockedStart + (horizontal ? slot.width : slot.height) - 1;
            const next = [];
            for (const [start, end] of intervals) {
                if (end < blockedStart || start > blockedEnd) {
                    next.push([start, end]);
                    continue;
                }
                if (start < blockedStart) next.push([start, blockedStart - 1]);
                if (end > blockedEnd) next.push([blockedEnd + 1, end]);
            }
            intervals = next;
            if (intervals.length === 0) break;
        }
        for (const [start, end] of intervals) {
            safeMarks.push(horizontal
                ? { ...mark, x1: start, x2: end }
                : { ...mark, y1: start, y2: end });
        }
    }
    return safeMarks;
}

function cropMarksForSlots(slots, canvasWidth, canvasHeight, dpi) {
    const length = Math.max(8, Math.round(0.16 * pixelsPerCm(dpi)));
    const offset = Math.max(2, Math.round(0.025 * pixelsPerCm(dpi)));
    const clampX = (value) => Math.max(0, Math.min(canvasWidth - 1, value));
    const clampY = (value) => Math.max(0, Math.min(canvasHeight - 1, value));
    const marks = [];
    for (const slot of slots) {
        const left = slot.x;
        const right = slot.x + slot.width - 1;
        const top = slot.y;
        const bottom = slot.y + slot.height - 1;
        for (const x of [left, right]) {
            marks.push({ x1: clampX(x), y1: clampY(top - offset - length), x2: clampX(x), y2: clampY(top - offset), width: 1 });
            marks.push({ x1: clampX(x), y1: clampY(bottom + offset), x2: clampX(x), y2: clampY(bottom + offset + length), width: 1 });
        }
        for (const y of [top, bottom]) {
            marks.push({ x1: clampX(left - offset - length), y1: clampY(y), x2: clampX(left - offset), y2: clampY(y), width: 1 });
            marks.push({ x1: clampX(right + offset), y1: clampY(y), x2: clampX(right + offset + length), y2: clampY(y), width: 1 });
        }
    }
    return clipCropMarksToWhitespace(
        marks.filter((mark) => mark.x1 !== mark.x2 || mark.y1 !== mark.y2),
        slots,
    );
}

function buildOneTwoMixedCandidate(settings, orientation, candidateIndex, canvasWidth, canvasHeight) {
    const oneInch = resolveSize(ID_PHOTO_PRESETS, "one-inch", "cm", 2.5, 3.5, settings.dpi);
    const twoInch = resolveSize(ID_PHOTO_PRESETS, "two-inch", "cm", 3.5, 4.9, settings.dpi);
    const oneColumns = 4;
    const oneRows = 2;
    const twoColumns = 2;
    const twoRows = 2;
    const twoLandscape = { width: twoInch.height, height: twoInch.width };
    const gap = distancePixels(0.2, settings.dpi);
    const sectionGap = distancePixels(0.3, settings.dpi);
    const oneGroupWidth = oneColumns * oneInch.width + (oneColumns - 1) * gap;
    const twoGroupWidth = twoColumns * twoLandscape.width + (twoColumns - 1) * gap;
    const oneGroupHeight = oneRows * oneInch.height + (oneRows - 1) * gap;
    const twoGroupHeight = twoRows * twoLandscape.height + (twoRows - 1) * gap;
    const groupWidth = Math.max(oneGroupWidth, twoGroupWidth);
    const groupHeight = oneGroupHeight + sectionGap + twoGroupHeight;
    const valid = groupWidth <= canvasWidth && groupHeight <= canvasHeight;
    const slots = [];
    if (valid) {
        const startY = Math.round((canvasHeight - groupHeight) / 2);
        const oneStartX = Math.round((canvasWidth - oneGroupWidth) / 2);
        for (let index = 0; index < 8; index += 1) {
            const row = Math.floor(index / oneColumns);
            const column = index % oneColumns;
            slots.push({
                x: oneStartX + column * (oneInch.width + gap),
                y: startY + row * (oneInch.height + gap),
                width: oneInch.width,
                height: oneInch.height,
                rotation: 0,
                sizeLabel: "1寸竖版",
            });
        }
        const twoStartX = Math.round((canvasWidth - twoGroupWidth) / 2);
        const twoStartY = startY + oneGroupHeight + sectionGap;
        for (let index = 0; index < 4; index += 1) {
            const row = Math.floor(index / twoColumns);
            const column = index % twoColumns;
            slots.push({
                x: twoStartX + column * (twoLandscape.width + gap),
                y: twoStartY + row * (twoLandscape.height + gap),
                width: twoLandscape.width,
                height: twoLandscape.height,
                rotation: 90,
                sizeLabel: "2寸横放",
            });
        }
    }
    const cropMarks = settings.cropMarksEnabled && slots.length > 0
        ? cropMarksForSlots(slots, canvasWidth, canvasHeight, settings.dpi)
        : [];
    const contractBase = {
        schemaVersion: 1,
        dpi: settings.dpi,
        imageOrientation: settings.photoOrientation,
        canvas: { width: canvasWidth, height: canvasHeight, background: "#ffffff" },
        slots,
        cropMarks,
        settings: {
            photoPresetId: settings.photoPresetId,
            paperPresetId: settings.paperPresetId,
            photoOrientation: settings.photoOrientation,
            orientation,
            layoutMode: "template",
            count: 12,
            columns: 0,
            rows: 0,
            mode: settings.mode,
            cropMarksEnabled: settings.cropMarksEnabled,
            spacingPreset: "custom",
            marginCm: 0,
            gapCm: 0.2,
        },
    };
    const layoutId = `idphoto-v1-${fnv1a(stableStringify(contractBase))}`;
    const contract = { ...contractBase, layoutId, _ui: { settings } };
    return {
        candidateId: `candidate-${candidateIndex + 1}-${orientation}`,
        orientation,
        capacity: valid ? 12 : 0,
        requestedCount: 12,
        columns: 4,
        rows: 4,
        previewColumns: 4,
        previewRows: 4,
        slots,
        cropMarks,
        valid,
        mixed: true,
        photoSummary: "1寸竖版 8张 + 2寸横放 4张",
        message: valid
            ? "同一人物已按上方 8 张1寸竖版、下方 4 张2寸横放排入。"
            : "当前画布无法放入 8 张1寸和 4 张2寸，请选择7寸竖版或更大的画布。",
        json: valid ? JSON.stringify(contract) : "",
        layoutId,
        canvasWidth,
        canvasHeight,
        slotCount: slots.length,
    };
}

function buildCandidate(settings, orientation, candidateIndex) {
    const paper = resolveSize(PAPER_PRESETS, settings.paperPresetId, settings.customPaperUnit, settings.customPaperWidth, settings.customPaperHeight, settings.dpi);
    const shortSide = Math.min(paper.width, paper.height);
    const longSide = Math.max(paper.width, paper.height);
    const canvasWidth = orientation === "portrait" ? shortSide : longSide;
    const canvasHeight = orientation === "portrait" ? longSide : shortSide;
    if (settings.photoPresetId === ONE_TWO_MIXED_PRESET_ID) {
        return buildOneTwoMixedCandidate(settings, orientation, candidateIndex, canvasWidth, canvasHeight);
    }
    const photo = applyOrientation(
        resolveSize(ID_PHOTO_PRESETS, settings.photoPresetId, settings.customPhotoUnit, settings.customPhotoWidth, settings.customPhotoHeight, settings.dpi),
        settings.photoOrientation,
    );
    const margin = distancePixels(settings.marginCm, settings.dpi);
    const gap = distancePixels(settings.gapCm, settings.dpi);
    const usableWidth = Math.max(0, canvasWidth - margin * 2);
    const usableHeight = Math.max(0, canvasHeight - margin * 2);
    const maxColumns = Math.max(0, Math.floor((usableWidth + gap) / (photo.width + gap)));
    const maxRows = Math.max(0, Math.floor((usableHeight + gap) / (photo.height + gap)));
    const automaticGrid = settings.layoutMode !== "fixed_grid";
    const requestedCount = settings.layoutMode === "auto_fill" ? maxColumns * maxRows : settings.count;
    let columns = settings.columns;
    let rows = settings.rows;
    if (settings.layoutMode === "auto_fill") {
        columns = maxColumns;
        rows = maxRows;
    } else if (automaticGrid) {
        const choices = [];
        for (let candidateColumns = 1; candidateColumns <= Math.min(maxColumns, requestedCount); candidateColumns += 1) {
            const candidateRows = Math.ceil(requestedCount / candidateColumns);
            if (candidateRows > maxRows) continue;
            const gridWidth = candidateColumns * photo.width + Math.max(0, candidateColumns - 1) * gap;
            const gridHeight = candidateRows * photo.height + Math.max(0, candidateRows - 1) * gap;
            choices.push({
                columns: candidateColumns,
                rows: candidateRows,
                complete: candidateColumns * candidateRows === requestedCount,
                unused: candidateColumns * candidateRows - requestedCount,
                aspectDifference: Math.abs(Math.log((gridWidth / gridHeight) / (canvasWidth / canvasHeight))),
            });
        }
        choices.sort((left, right) => Number(right.complete) - Number(left.complete)
            || left.unused - right.unused
            || left.aspectDifference - right.aspectDifference
            || right.columns - left.columns);
        columns = choices[0]?.columns || maxColumns;
        rows = choices[0]?.rows || maxRows;
    } else if (columns === 0 && rows === 0) {
        columns = maxColumns;
        rows = maxRows;
    } else if (columns === 0) {
        columns = rows > 0 ? maxColumns : 0;
    } else if (rows === 0) {
        rows = columns > 0 ? maxRows : 0;
    }
    const targetCount = settings.layoutMode === "fixed_grid" ? columns * rows : requestedCount;
    const gridCapacity = columns * rows;
    const physicalCapacity = maxColumns * maxRows;
    const geometryFits = columns > 0 && rows > 0 && columns <= maxColumns && rows <= maxRows;
    const countFits = targetCount <= gridCapacity;
    const valid = geometryFits && countFits;
    const capacity = automaticGrid ? physicalCapacity : gridCapacity;
    const previewColumns = valid ? columns : Math.min(Math.max(columns, 0), maxColumns) || maxColumns;
    const previewRows = valid ? rows : Math.min(Math.max(rows, 0), maxRows) || maxRows;
    const previewCapacity = previewColumns * previewRows;
    const placementCount = Math.min(targetCount, previewCapacity);
    const gridHeight = previewRows > 0 ? previewRows * photo.height + (previewRows - 1) * gap : 0;
    const startY = Math.round((canvasHeight - gridHeight) / 2);
    const slots = [];
    for (let index = 0; index < placementCount; index += 1) {
        const row = Math.floor(index / previewColumns);
        const column = index % previewColumns;
        const itemsInRow = Math.min(previewColumns, placementCount - row * previewColumns);
        const occupiedRowWidth = itemsInRow * photo.width + Math.max(0, itemsInRow - 1) * gap;
        const rowStartX = Math.round((canvasWidth - occupiedRowWidth) / 2);
        slots.push({
            x: rowStartX + column * (photo.width + gap),
            y: startY + row * (photo.height + gap),
            width: photo.width,
            height: photo.height,
        });
    }
    const cropMarks = settings.cropMarksEnabled && slots.length > 0 ? cropMarksForSlots(slots, canvasWidth, canvasHeight, settings.dpi) : [];
    const contractBase = {
        schemaVersion: 1,
        dpi: settings.dpi,
        imageOrientation: settings.photoOrientation,
        canvas: { width: canvasWidth, height: canvasHeight, background: "#ffffff" },
        slots,
        cropMarks,
        settings: {
            photoPresetId: settings.photoPresetId,
            paperPresetId: settings.paperPresetId,
            photoOrientation: settings.photoOrientation,
            orientation,
            layoutMode: settings.layoutMode,
            count: targetCount,
            columns: settings.columns,
            rows: settings.rows,
            mode: settings.mode,
            cropMarksEnabled: settings.cropMarksEnabled,
            spacingPreset: settings.spacingPreset,
            marginCm: settings.marginCm,
            gapCm: settings.gapCm,
        },
    };
    const layoutId = `idphoto-v1-${fnv1a(stableStringify(contractBase))}`;
    const contract = { ...contractBase, layoutId, _ui: { settings } };
    return {
        candidateId: `candidate-${candidateIndex + 1}-${orientation}`,
        orientation,
        capacity,
        requestedCount: targetCount,
        columns,
        rows,
        previewColumns,
        previewRows,
        slots,
        cropMarks,
        valid,
        message: valid
            ? `${targetCount} 张已按 ${columns} 列 × ${rows} 行排入，当前网格可放 ${capacity} 张。`
            : automaticGrid
                ? `当前画布最多放 ${physicalCapacity} 张，请减少总张数或调整尺寸。`
                : !geometryFits
                ? `固定网格 ${columns} 列 × ${rows} 行超过画布上限 ${maxColumns} 列 × ${maxRows} 行。`
                : `固定网格最多放 ${capacity} 张，请减少总张数或增加行列。`,
        json: JSON.stringify(contract),
        layoutId,
        canvasWidth,
        canvasHeight,
        slotCount: slots.length,
    };
}

export function buildLayoutCandidates(value) {
    const settings = normaliseSettings(value);
    const orientations = settings.orientation === "auto" ? ["portrait", "landscape"] : [settings.orientation];
    return orientations
        .map((orientation, index) => buildCandidate(settings, orientation, index))
        .sort((left, right) => Number(right.valid) - Number(left.valid) || right.capacity - left.capacity);
}

export function settingsFromLayout(value) {
    try {
        const layout = typeof value === "string" ? JSON.parse(value) : value;
        const stored = layout?._ui?.settings;
        return stored && typeof stored === "object" ? normaliseSettings(stored) : null;
    } catch {
        return null;
    }
}

export function previewFromLayout(value) {
    try {
        const layout = typeof value === "string" ? JSON.parse(value) : value;
        const width = Number(layout?.canvas?.width);
        const height = Number(layout?.canvas?.height);
        const slots = Array.isArray(layout?.slots) ? layout.slots : [];
        const cropMarks = Array.isArray(layout?.cropMarks) ? layout.cropMarks : [];
        if (!(width > 0 && height > 0 && slots.length > 0)) return null;
        return {
            canvasWidth: width,
            canvasHeight: height,
            slots,
            cropMarks,
            slotCount: slots.length,
            layoutId: String(layout.layoutId || "外部布局"),
        };
    } catch {
        return null;
    }
}
