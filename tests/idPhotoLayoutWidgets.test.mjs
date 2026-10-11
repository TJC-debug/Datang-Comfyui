import test from "node:test";
import assert from "node:assert/strict";
import { hideDataWidget, afterLayoutConfigured } from "../web/id_photo_layout_widgets.js";
import { buildLayoutCandidates, DEFAULT_SETTINGS } from "../web/id_photo_layout_core.js";

class NativeDomWidget {
    constructor(name, value) {
        this._widget = { name, type: "customtext", options: {} };
        this.element = { style: {} };
        this._value = value;
        this.removeCount = 0;
        Object.defineProperty(this, "value", {
            get: () => this._value,
            set: (next) => { this._value = next; this.callback?.(next); },
        });
    }
    get name() { return this._widget.name; }
    get type() { return this._widget.type; }
    get options() { return this._widget.options; }
    onRemove() { this.removeCount += 1; }
}

async function apiInputs(node) {
    const inputs = {};
    for (const [index, widget] of node.widgets.entries()) {
        if (!widget.name || widget.options?.serialize === false) continue;
        inputs[widget.name] = widget.serializeValue ? await widget.serializeValue(node, index) : widget.value;
    }
    return JSON.parse(JSON.stringify(inputs));
}

test("隐藏原生 DOM 控件保留身份、继承名称、类型、注册引用和不可配置 value", () => {
    const widget = new NativeDomWidget("排版数据", "original");
    const registered = widget;
    const valueDescriptor = Object.getOwnPropertyDescriptor(widget, "value");
    const node = { widgets: [widget] };
    const hidden = hideDataWidget(node, widget);
    assert.equal(hidden, registered);
    assert.equal(node.widgets[0], registered);
    assert.equal(hidden.name, "排版数据");
    assert.equal(hidden.type, "customtext");
    assert.deepEqual(Object.getOwnPropertyDescriptor(hidden, "value"), valueDescriptor);
    assert.equal(widget.element.style.display, "none");
    assert.deepEqual(hidden.computeSize(), [0, -4]);
    hidden.onRemove();
    assert.equal(registered.removeCount, 1);
});

test("选择新排版后普通 JSON 和 API 都保存当前同一份布局", async () => {
    const selected = buildLayoutCandidates({ ...DEFAULT_SETTINGS, dpi: 600, paperPresetId: "five-inch-paper" }).find((candidate) => candidate.valid);
    assert.ok(selected);
    const data = new NativeDomWidget("排版数据", null);
    const dpi = { name: "DPI", type: "number", value: 300, options: { min: 72, max: 1200 } };
    const node = { widgets: [dpi, data] };
    hideDataWidget(node, data).writeFromUi(selected.json);
    hideDataWidget(node, dpi).writeFromUi(600);
    const values = JSON.parse(JSON.stringify(node.widgets.map((widget) => widget.value)));
    assert.deepEqual(values, [600, selected.json]);
    assert.deepEqual(await apiInputs(node), { DPI: 600, "排版数据": selected.json });
    const restored = new NativeDomWidget("排版数据", "");
    const next = { widgets: [restored] };
    hideDataWidget(next, restored);
    restored.value = values[1];
    assert.equal((await apiInputs(next))["排版数据"], selected.json);
});

test("DOM 内部写值只触发一次原回调且不递归渲染，外部写值正常通知", () => {
    const widget = new NativeDomWidget("排版数据", "old");
    let callbacks = 0;
    const external = [];
    widget.callback = function () { assert.equal(this, widget); callbacks += 1; };
    hideDataWidget({ widgets: [widget] }, widget, (value) => external.push(value));
    widget.writeFromUi("chosen");
    assert.equal(callbacks, 1);
    assert.deepEqual(external, []);
    widget.value = "restored";
    assert.equal(callbacks, 2);
    assert.deepEqual(external, ["restored"]);
});

test("普通 DPI 数字控件更新原值和回调且保留数值范围", () => {
    let callbacks = 0;
    const widget = { name: "DPI", type: "number", value: 300, options: { min: 72, max: 1200 }, callback() { callbacks += 1; } };
    hideDataWidget({ widgets: [widget] }, widget).writeFromUi(450);
    assert.equal(widget.value, 450);
    assert.equal(callbacks, 1);
    assert.deepEqual(widget.options, { min: 72, max: 1200 });
});

test("内部写值失败也释放重入保护，随后外部恢复仍通知", () => {
    const widget = new NativeDomWidget("排版数据", "old");
    const external = [];
    widget.callback = (value) => { if (value === "bad") throw new Error("callback failed"); };
    hideDataWidget({ widgets: [widget] }, widget, (value) => external.push(value));
    assert.throws(() => widget.writeFromUi("bad"), /callback failed/);
    widget.value = "recovered";
    assert.deepEqual(external, ["recovered"]);
});

test("外部冻结布局按原字符串提交，不生成默认布局或改变序列化排除规则", async () => {
    const frozen = '{ "schemaVersion": 1, "layoutId": "author-frozen", "slots": [] }';
    const widget = new NativeDomWidget("排版数据", frozen);
    const node = { widgets: [widget] };
    hideDataWidget(node, widget);
    assert.equal((await apiInputs(node))["排版数据"], frozen);
    widget.options.serialize = false;
    assert.deepEqual(await apiInputs(node), {});
    assert.equal(widget.value, frozen);
});

test("旧文件排版数据为空时保留事实，不能静默补入另一套布局", () => {
    const widget = new NativeDomWidget("排版数据", null);
    hideDataWidget({ widgets: [widget] }, widget);
    assert.equal(widget.value, null);
    assert.equal(widget.serializeValue(), null);
});

test("配置完成后才读取恢复的数据并保留原生命周期、参数和返回值", () => {
    const widget = { name: "排版数据", value: "before" };
    const info = { widgets_values: ["after"] };
    const observed = [];
    const node = { onConfigure(value) { assert.equal(this, node); assert.equal(value, info); widget.value = value.widgets_values[0]; return "kept"; } };
    afterLayoutConfigured(node, () => observed.push(widget.value));
    assert.equal(node.onConfigure(info), "kept");
    assert.deepEqual(observed, ["after"]);
});

test("节点中不存在的控件不会被插入或替换", () => {
    const node = { widgets: [] };
    assert.equal(hideDataWidget(node, new NativeDomWidget("排版数据", "")), null);
    assert.deepEqual(node.widgets, []);
});
