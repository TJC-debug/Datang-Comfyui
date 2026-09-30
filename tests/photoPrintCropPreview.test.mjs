import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { VISIBLE_CROP_METHODS } from "../web/photo_print_crop_preview_core.js";

const source = await readFile(new URL("../web/photo_print_crop_preview.js", import.meta.url), "utf8");
const pythonSource = await readFile(new URL("../photo_print_crop.py", import.meta.url), "utf8");

test("生活照裁剪界面只保留居中和补边两种方式", () => {
    assert.deepEqual(VISIBLE_CROP_METHODS, ["居中裁剪", "保留全图并补边"]);
});

test("旧版指定焦点在新界面安全迁移为居中裁剪", () => {
    assert.match(source, /LEGACY_CROP_METHOD = "指定焦点裁剪"/);
    assert.match(source, /methodWidget\.value = "居中裁剪"/);
});

test("焦点位置继续序列化但在画布和 PS_AI 扫描中隐藏", () => {
    assert.match(source, /widgetByName\(node, "焦点位置"\)/);
    assert.match(source, /widget\.type = "converted-widget"/);
    assert.match(source, /widget\.computeSize = \(\) => \[0, -4\]/);
    assert.match(source, /focusWidget\.value = "居中"/);
});

test("裁剪方式下拉从现有服务合同中过滤旧焦点选项", () => {
    assert.match(source, /methodWidget\.options\.values = methodWidget\.options\.values\.filter/);
    assert.match(source, /VISIBLE_CROP_METHODS\.includes\(value\)/);
});

test("加载旧工作流参数后会再次执行迁移和隐藏", () => {
    assert.match(source, /const previousOnConfigure = node\.onConfigure/);
    assert.match(source, /node\.onConfigure = function onConfigure/);
    assert.match(source, /simplifyPhotoCropWidgets\(this\)/);
});

test("构图预览区域和 ComfyUI 临时图片读取均已移除", () => {
    assert.doesNotMatch(source, /addDOMWidget/);
    assert.doesNotMatch(source, /<img/);
    assert.doesNotMatch(source, /scripts\/api\.js/);
    assert.doesNotMatch(source, /datang_preview/);
});

test("界面不再保留轮询定时器或预览样式", () => {
    assert.doesNotMatch(source, /setInterval/);
    assert.doesNotMatch(source, /clearInterval/);
    assert.doesNotMatch(source, /installStyles/);
    assert.doesNotMatch(source, /datang-photo-crop-preview__/);
});

test("旧预览节点高度会恢复为原生控件高度", () => {
    assert.match(source, /LEGACY_PREVIEW_MIN_HEIGHT = 560/);
    assert.match(source, /node\.computeSize\?\.\(\)/);
    assert.match(source, /node\.setSize\?\.\(\[Math\.max\(currentWidth, computedWidth\), computedHeight\]\)/);
});

test("后端在原有两个输出后追加标准补边遮罩", () => {
    assert.match(pythonSource, /RETURN_TYPES = \("IMAGE", "INT", "MASK"\)/);
    assert.match(pythonSource, /RETURN_NAMES = \("处理后图像", "DPI", "补边遮罩"\)/);
    assert.match(pythonSource, /return result\.unsqueeze\(0\), final_dpi, fill_mask\.unsqueeze\(0\)/);
});

test("后端不再保存临时预览且节点仍非强制输出", () => {
    assert.doesNotMatch(pythonSource, /PreviewImage/);
    assert.doesNotMatch(pythonSource, /datang_preview/);
    assert.doesNotMatch(pythonSource, /OUTPUT_NODE\s*=\s*True/);
    assert.doesNotMatch(source, /FormData|fetch\s*\(/);
});
