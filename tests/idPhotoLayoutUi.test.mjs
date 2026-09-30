import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../web/id_photo_layout.js", import.meta.url), "utf8");

test("张数与行列使用枚举下拉而不是自由数字输入", () => {
    assert.match(source, /<details data-layout-advanced>/);
    assert.match(source, /<select data-field="count">/);
    assert.match(source, /<select data-field="columns">/);
    assert.match(source, /<select data-field="rows">/);
    assert.doesNotMatch(source, /<input data-field="(?:count|columns|rows)"/);
});

test("非自定义尺寸隐藏单位宽高并让尺寸选择独占一行", () => {
    assert.match(source, /data-custom-control="photo"/);
    assert.match(source, /data-custom-control="paper"/);
    assert.match(source, /control\.hidden = !display\.custom/);
    assert.match(source, /row\?\.classList\.toggle\("is-custom", display\.custom\)/);
});

test("默认自动铺满且数量行列只按排版方式按需显示", () => {
    assert.match(source, /<select data-field="layoutMode">/);
    assert.match(source, /value="auto_fill">自动铺满/);
    assert.match(source, /value="specified_count">指定张数/);
    assert.match(source, /value="fixed_grid">固定行列/);
    assert.match(source, /settings\.layoutMode === "specified_count"/);
    assert.match(source, /settings\.layoutMode === "fixed_grid"/);
});

test("固定混排自动锁定七寸竖版并隐藏无意义方向设置", () => {
    assert.match(source, /paperPresetId: "seven-inch-paper", orientation: "portrait", photoOrientation: "original"/);
    assert.match(source, /photoOrientation\.closest\("label"\)\.hidden = mixedPreset/);
    assert.match(source, /canvasOrientation\.closest\("label"\)\.hidden = mixedPreset/);
});

test("节点界面移除重复宣传并在高级设置提供 DPI", () => {
    assert.doesNotMatch(source, /可视化证件照排版/);
    assert.doesNotMatch(source, /参数变化后立即/);
    assert.match(source, /data-layout-control="dpi"/);
    assert.match(source, /data-field="dpi"/);
    assert.match(source, /排版 DPI（未连接时）/);
    assert.match(source, /DPI_WIDGET_NAME = "DPI"/);
    assert.match(source, /dpiWidget\?\.writeFromUi\(settings\.dpi\)/);
    assert.doesNotMatch(source, /不写 DPI/);
    assert.doesNotMatch(source, /回到 Photoshop 后仍按默认 72/);
});

test("固定方向隐藏重复方案按钮且有效布局隐藏重复状态", () => {
    assert.match(source, /elements\.schemes\.hidden = settings\.orientation !== "auto"/);
    assert.match(source, /elements\.status\.hidden = true/);
});

test("照片方向提供保持规格、竖版和横版枚举", () => {
    assert.match(source, /<select data-field="photoOrientation">/);
    assert.match(source, /value="original">保持规格/);
    assert.match(source, /value="portrait">竖版/);
    assert.match(source, /value="landscape">横版/);
});

test("含义重复的排版模式改为明确裁切线开关", () => {
    assert.doesNotMatch(source, /紧凑排版/);
    assert.doesNotMatch(source, /易裁切（带裁切线）/);
    assert.match(source, /<select data-field="cropMarksEnabled">/);
    assert.match(source, /datang-id-photo__crop-mark/);
    assert.match(source, /显示（避开照片）/);
});

test("间距方案提供影楼紧密、留缝裁切和自定义", () => {
    assert.match(source, /<select data-field="spacingPreset">/);
    assert.match(source, /value="studio_tight">影楼紧密/);
    assert.match(source, /value="cutting_gap">留缝裁切/);
    assert.match(source, /value="custom">自定义/);
});

test("无法完整排下时仍绘制合法预览并显示未排入数量", () => {
    assert.match(source, /paintPreview\(selected\)/);
    assert.match(source, /还有 \$\{Math\.max\(0, selected\.requestedCount - selected\.slotCount\)\} 张未排入/);
});

test("面板滚轮在高级文本区无需滚动时转交给 ComfyUI 画布缩放", () => {
    assert.match(source, /function canConsumeWheel\(element, deltaY\)/);
    assert.match(source, /function forwardWheelToCanvas\(event\)/);
    assert.match(source, /canvas\.dispatchEvent\(new WheelEvent\("wheel"/);
    assert.match(source, /root\.addEventListener\("wheel"/);
    assert.match(source, /canConsumeWheel\(textArea, event\.deltaY\)/);
    assert.match(source, /forwardWheelToCanvas\(event\)/);
    assert.match(source, /\{ passive: false \}/);
});

test("占位预览按真实画布比例绘制并显示物理尺寸", () => {
    assert.match(source, /const scale = Math\.min\(maxWidth \/ preview\.canvasWidth, maxHeight \/ preview\.canvasHeight\)/);
    assert.match(source, /slot\.x \/ preview\.canvasWidth \* 100/);
    assert.match(source, /slot\.height \/ preview\.canvasHeight \* 100/);
    assert.match(source, /data-width-label/);
    assert.match(source, /data-height-label/);
    assert.match(source, /datang-id-photo__person/);
    assert.match(source, /画布 \$\{dimensionText/);
    assert.match(source, /照片 \$\{dimensionText/);
});

test("预览区域放大相纸并压缩无效留白", () => {
    assert.match(source, /grid-template-columns: minmax\(300px, 1\.5fr\) minmax\(140px, \.5fr\)/);
    assert.match(source, /min-height: 260px/);
    assert.match(source, /min-height: 238px/);
    assert.match(source, /justify-content: flex-start/);
    assert.match(source, /const maxWidth = 320/);
    assert.match(source, /const maxHeight = 255/);
});

test("预览摘要把画布、照片和行列张数分成独立三行", () => {
    assert.match(source, /function setSummaryLines\(lines\)/);
    assert.match(source, /datang-id-photo__summary-line/);
    assert.match(source, /`画布 \$\{dimensionText/);
    assert.match(source, /`照片 \$\{dimensionText/);
    assert.match(source, /`\$\{selected\.columns\} 列 × \$\{selected\.rows\} 行 · \$\{selected\.slotCount\} 张`/);
    assert.doesNotMatch(source, /elements\.detail\.textContent/);
});

test("顶部快捷区提供常用影楼与打印组合", () => {
    assert.match(source, />快捷排版</);
    assert.match(source, /6寸 · 12张1寸/);
    assert.match(source, /6寸 · 6张2寸/);
    assert.match(source, /7寸 · 1寸\+2寸/);
    assert.match(source, /上8张竖版 · 下4张横放/);
    assert.match(source, /5寸 · 9张1寸/);
    assert.match(source, /5寸 · 4张2寸/);
    assert.match(source, /常用冲印 · 2列 × 2行/);
    assert.match(source, /\[data-built-in-presets\] > :last-child:nth-child\(odd\)/);
    assert.doesNotMatch(source, /A4 · 50张1寸/);
    assert.match(source, /function applyPreset\(preset\)/);
    assert.ok(source.indexOf('id: "studio-five-one-inch-9"') < source.indexOf('id: "studio-six-one-inch-12"'));
    assert.ok(source.indexOf('id: "studio-six-one-inch-12"') < source.indexOf('id: "studio-seven-one-two-mixed"'));
});

test("用户可以在浏览器本机保存、同名更新和删除个人预设", () => {
    assert.match(source, /datang\.id_photo_layout\.user_presets\.v1/);
    assert.match(source, /localStorage\.getItem\(USER_PRESET_STORAGE_KEY\)/);
    assert.match(source, /localStorage\.setItem\(USER_PRESET_STORAGE_KEY/);
    assert.match(source, /existing\.settings = normaliseSettings\(settings\)/);
    assert.match(source, /userPresets = userPresets\.filter/);
    assert.match(source, /MAX_USER_PRESETS = 20/);
});

test("快捷预设是一次性参数指令且不保持选中状态", () => {
    assert.match(source, /button\.addEventListener\("click", \(\) => applyPreset\(preset\)\)/);
    assert.doesNotMatch(source, /selectedPresetId/);
    assert.doesNotMatch(source, /presetMatches/);
});

test("恢复默认回到节点初始设置而不是数值归零", () => {
    assert.match(source, /data-preset-action="reset">恢复默认/);
    assert.match(source, /settings = applyExternalValues\(DEFAULT_SETTINGS\)/);
    assert.match(source, /selectedOrientation = ""/);
    assert.match(source, /renderManual\(\)/);
});

test("外部裁剪规格实时接管尺寸和 DPI 并锁定冲突控件", () => {
    assert.match(source, /function resolveExternalInputs\(node\)/);
    assert.match(source, /String\(source\.comfyClass \|\| source\.type \|\| ""\) !== "LoneSeaPresetSize"/);
    assert.match(source, /photoPresetId: "custom"/);
    assert.match(source, /customPhotoUnit: "px"/);
    assert.match(source, /外部规格已接管/);
    assert.match(source, /elements\.quickLayout\.hidden = photoLocked/);
    assert.match(source, /photoPresetInput\.disabled = photoLocked/);
    assert.match(source, /dpiInput\.disabled = dpiLocked/);
    assert.match(source, /buildLayoutCandidates\(settings\)\.some/);
    assert.match(source, /layoutMode: "auto_fill", columns: 0, rows: 0/);
    assert.match(source, /globalThis\.setInterval/);
    assert.match(source, /domWidget\.onRemove = \(\) => globalThis\.clearInterval/);
});

test("隐藏 DPI 不再伪装成可连接控件并迁移旧版错位连线", () => {
    assert.match(source, /datangHidden: true/);
    assert.match(source, /originalWidget\.datangHidden = true/);
    assert.match(source, /function repairLegacyConvertedDpiInput\(node\)/);
    assert.match(source, /if \(!node\.graph\) return false/);
    assert.match(source, /if \(!link\) return false/);
    assert.match(source, /inferred\?\.type === "IMAGE" \? "图片" : "输入DPI"/);
    assert.match(source, /node\.disconnectInput\?\.\(legacyIndex\)/);
    assert.match(source, /node\.removeInput\?\.\(legacyIndex\)/);
    assert.match(source, /inferred\.source\.connect\?\.\(inferred\.originSlot, node, targetIndex\)/);
    assert.doesNotMatch(source, /type: "converted-widget"/);
    assert.doesNotMatch(source, /type: HIDDEN_WIDGET_TYPE/);
    assert.doesNotMatch(source, /originalWidget\.type = HIDDEN_WIDGET_TYPE/);
});

test("先挂载可视面板再执行初次渲染且失败时不留下空白节点", () => {
    const mountIndex = source.indexOf('node.addDOMWidget("证件照排版面板"');
    const renderIndex = source.indexOf("if (externalLayout) renderExternal(dataWidget.value)");
    assert.ok(mountIndex >= 0);
    assert.ok(renderIndex > mountIndex);
    assert.match(source, /证件照排版界面初始化失败/);
    assert.match(source, /uiFailed = true/);
    assert.match(source, /if \(!uiFailed && node\.graph\) synchronizeExternalInputs\(\)/);
    assert.match(source, /console\.error\("\[Datang\.IdPhotoLayout\] initial render failed", error\)/);
});

test("预览人物轮廓跟随横向照片整体旋转", () => {
    assert.match(source, /person\.classList\.toggle\("is-landscape", slot\.width > slot\.height\)/);
    assert.match(source, /datang-id-photo__person\.is-landscape \{ transform: rotate\(90deg\); \}/);
});

test("节点面板按住中键可以继续拖动 ComfyUI 画布", () => {
    assert.match(source, /if \(event\.button !== 1\) return/);
    assert.match(source, /app\.canvas\?\.processMouseDown\?\.\(event\)/);
    assert.match(source, /app\.canvas\?\.processMouseMove\?\.\(event\)/);
    assert.match(source, /app\.canvas\?\.processMouseUp\?\.\(event\)/);
    assert.match(source, /root\.setPointerCapture\?\.\(event\.pointerId\)/);
    assert.match(source, /root\.addEventListener\("pointercancel", finishCanvasPan\)/);
});
