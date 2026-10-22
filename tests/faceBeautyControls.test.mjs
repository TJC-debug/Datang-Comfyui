import assert from "node:assert/strict";
import test from "node:test";
import {readFile} from "node:fs/promises";
import vm from "node:vm";
import * as controls from "../web/face_beauty_controls_core.js";

import {
    applyBeautyDefaults,
    BEAUTY_NODE_DEFAULTS,
    migrateBlemishValues,
    applyBlemishMigration,
    BLEMISH_WIDGETS,
} from "../web/face_beauty_controls_core.js";

test("快速美颜和痘印精修分别保留稳定默认值", () => {
    assert.deepEqual(Object.keys(BEAUTY_NODE_DEFAULTS), [
        "DatangFastFaceBeauty",
        "DatangBlemishRetouch",
    ]);
    assert.equal(BEAUTY_NODE_DEFAULTS.DatangFastFaceBeauty.磨皮, 45);
    assert.equal(BEAUTY_NODE_DEFAULTS.DatangBlemishRetouch.肤质强度, 0.35);
    assert.equal(BEAUTY_NODE_DEFAULTS.DatangBlemishRetouch.祛痘修补, true);
    assert.equal("五官边缘保护" in BEAUTY_NODE_DEFAULTS.DatangBlemishRetouch, false);
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
    assert.equal(node.widgets[2].value, 99);
    assert.deepEqual(callbacks, [85]);
    assert.deepEqual(node.dirty, [true, true]);
});

test("旧七值迁移保留修复强度，旧检测数值不串入新开关或肤质", () => {
    const original={widgets_values:[85,58,36,85,70,78,6],properties:{keep:"preserved"}},before=JSON.stringify(original);
    assert.deepEqual(migrateBlemishValues(original),{values:[true,0.35,85],legacy:true});
    assert.equal(JSON.stringify(original),before);
    assert.deepEqual(migrateBlemishValues({...original,widgets_values:[0,58,36,85,70,78,6]}).values,[true,0.35,0]);
});

test("新schema重载和复制保持新控件，非法旧数组不会错位使用", () => {
    assert.deepEqual(migrateBlemishValues({widgets_values:[false,0.8,55],properties:{datang_blemish_schema:2}}).values,[false,0.8,55]);
    assert.deepEqual(migrateBlemishValues({widgets_values:[85,58,36]}).values,[true,0.35,85]);
    const node={properties:{keep:"preserved"},widgets:BLEMISH_WIDGETS.map(name=>({name,value:null}))};
    applyBlemishMigration(node,{widgets_values:[85,58,36,85,70,78,6]});
    assert.equal(node.properties.keep,"preserved");assert.equal(node.properties.datang_blemish_schema,2);
    assert.deepEqual(node.widgets.map(w=>w.value),[true,0.35,85]);
});

test("无匹配控件时恢复默认不制造伪修改", () => {
    assert.equal(applyBeautyDefaults({ widgets: [] }, { 磨皮: 45 }), false);
});

test("实际前端扩展完成旧画布载入、保存重载和恢复默认，图像遮罩连线保持", async () => {
    let extension;const messages=[];
    let source=await readFile(new URL('../web/face_beauty_controls.js',import.meta.url),'utf8');
    source=source.replace(/^import .*;\r?\n/gm,'');
    vm.runInNewContext(source,{app:{registerExtension:value=>{extension=value;}},...controls,console:{info:message=>messages.push(message)}});
    class Node {
        constructor(){this.widgets=BLEMISH_WIDGETS.map(name=>({name,value:controls.BEAUTY_NODE_DEFAULTS.DatangBlemishRetouch[name]}));this.inputs=[{name:'图像',type:'IMAGE',link:101},{name:'皮肤遮罩',type:'MASK',link:102}];this.properties={};}
        addWidget(type,name,value,callback,options){const widget={type,name,value,callback,options};this.widgets.push(widget);return widget;}
        setDirtyCanvas(){}
    }
    await extension.beforeRegisterNodeDef(Node,{name:'DatangBlemishRetouch'});
    const node=new Node(),links=JSON.stringify(node.inputs);node.onNodeCreated();node.onConfigure({widgets_values:[85,58,36,85,70,78,6]});
    assert.deepEqual(node.widgets.slice(0,3).map(w=>w.value),[true,0.35,85]);
    node.widgets[0].value=false;node.widgets[1].value=.75;node.widgets[2].value=55;
    const data={inputs:node.inputs};node.onSerialize(data);
    const loaded=new Node();loaded.onNodeCreated();loaded.onConfigure(data);
    assert.deepEqual(loaded.widgets.slice(0,3).map(w=>w.value),[false,.75,55]);assert.equal(JSON.stringify(node.inputs),links);assert.equal(JSON.stringify(loaded.inputs),links);
    loaded.widgets.find(w=>w.name==='恢复默认').callback();
    assert.deepEqual(loaded.widgets.slice(0,3).map(w=>w.value),[true,.35,85]);
    assert.equal(data.widgets_values.length,3);assert.equal(data.properties.datang_blemish_schema,2);
    assert.equal(messages.length,1);
});
