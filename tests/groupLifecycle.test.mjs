import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import * as core from '../web/datang_group_core.js';

// Execute the shipped extension, replacing only ComfyUI imports and its host.
const script = readFileSync(new URL('../web/datang_group_switch.js', import.meta.url), 'utf8')
  .replace(/^import \{ app \} from [^;]+;/m, 'const app = __app;')
  .replace(/import \{([\s\S]*?)\} from "\.\/datang_group_core\.js";/, 'const {$1} = __core;')
  .replace(/export function /g, 'function ');

function harness() {
  const timers = [], intervals = [], listeners = new Map(), events = [];
  class Canvas {
    getCanvasMenuOptions() { return []; }
    drawGroups() {}
    drawNode() {}
    setDirty() {}
  }
  const app = { graph: null, canvas: new Canvas(), registerExtension(x) { this.extension = x; } };
  const context = vm.createContext({ __app: app, __core: core, LGraphCanvas: Canvas,
    LiteGraph: { createNode() { return { id: -1, type: 'DatangGroupSwitch', title: '大汤节点组',
      mode: 0, size: [260, 82], pos: [0, 0], properties: {},
      widgets: [{ name: '启用节点组', type: 'toggle', value: true }] }; } }, window: {
      addEventListener(name, fn) { listeners.set(name, fn); },
      dispatchEvent(e) { events.push(e); listeners.get(e.type)?.(e); },
    },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    setTimeout(fn) { timers.push(fn); return timers.length; },
    setInterval(fn) { intervals.push(fn); return intervals.length; }, console });
  vm.runInContext(script, context);
  app.extension.setup();
  return { app, events, timers, intervals,
    use(g) { app.graph = g; app.canvas.graph = g; },
    flush() { timers.splice(0).forEach(fn => fn()); },
    tick() { intervals.forEach(fn => fn()); },
    request(id, enabled) { return listeners.get('datang-group-switch-request')({ detail: { controllerId: id, enabled } }); },
    repair(g) { return context.repairDatangGroupSwitch(app.canvas, g); },
  };
}

function fixture() {
  const graph = { _nodes: [], _groups: [], extra: { ps_ai: { node_order: [31, 215] } }, removed: [], changes: 0,
    beforeChange() {}, afterChange() {}, change() { this.changes++; }, setDirtyCanvas() {},
    getNodeById(id) { return this._nodes.find(n => n.id === id); },
    add(n) { if (n.id === -1) n.id = Math.max(...this._nodes.map(x => Number(x.id))) + 1; n.graph = this; this._nodes.push(n); },
    remove(n) { this.removed.push(n.id); this._nodes = this._nodes.filter(x => x.id !== n.id); n.graph = null; },
  };
  const controller = { id: 31, type: 'DatangGroupSwitch', graph, mode: 0, size: [1, 1], pos: [8, 8],
    title: '#加载服装参考图', __datangResolvedGroup: true,
    properties: { datang_embedded_controller: true, datang_delete_with_group: true, datang_group_title: '加载服装参考图' },
    widgets: [{ name: '启用节点组', type: 'toggle', value: true }] };
  const image = { id: 215, type: 'LoadImage', title: '#加载服装图', graph, mode: 0, pos: [40, 80], size: [200, 200] };
  graph._nodes.push(controller, image);
  const group = { graph, title: '加载服装参考图', flags: {}, _bounding: new Float32Array([0, 0, 600, 400]), font_size: 24,
    recomputeInsideNodes() { this._nodes = graph._nodes.filter(n => n.pos[0] >= 0 && n.pos[0] < 600); },
  };
  core.writeDatangGroupState(group, { controllerId: controller.id, enabled: true });
  graph._groups.push(group);
  return { graph, controller, image, group };
}
function click(h, group) {
  const [x, y, w, z] = core.groupHeaderSwitchRect(group);
  return h.app.canvas.onMouse({ type: 'pointerdown', button: 0, canvasX: x + w / 2, canvasY: y + z / 2 });
}

test('real group header toggles image bypass and restores its original mode', () => {
  const h = harness(), f = fixture(); h.use(f.graph); h.tick();
  assert.equal(click(h, f.group), true);
  assert.equal(f.image.mode, core.NODE_MODE.BYPASS);
  assert.equal(f.controller.widgets[0].value, false);
  assert.equal(core.readDatangGroupState(f.group).enabled, false);
  assert.equal(click(h, f.group), true);
  assert.equal(f.image.mode, core.NODE_MODE.ALWAYS);
  assert.equal(f.group.flags.datang_group_switch.controller_id, 31);
  assert.equal(f.graph._groups[0], f.group);
});

test('PS_AI request updates the same real controller and emits the canvas change event', () => {
  const h = harness(), f = fixture(); h.use(f.graph); h.tick();
  assert.equal(h.request(31, false), true);
  assert.equal(f.image.mode, core.NODE_MODE.BYPASS);
  assert.equal(h.events.at(-1).type, 'datang-group-switch-changed');
  assert.equal(h.events.at(-1).detail.controllerId, 31);
});

test('delayed callbacks of a detached old node cannot remove matching IDs in another workflow', () => {
  const h = harness(), old = fixture(), next = fixture(); h.use(old.graph);
  h.app.extension.nodeCreated(old.controller);
  old.controller.graph = null; next.graph._groups = []; h.use(next.graph);
  h.flush();
  assert.deepEqual(next.graph.removed, []);
  assert.equal(next.graph.getNodeById(31), next.controller);
  assert.equal(next.graph.changes, 0);
});

test('callbacks of an old node cannot mutate a reused graph containing a new node with the same ID', () => {
  const h = harness(), old = fixture(), next = fixture(); h.use(old.graph);
  h.app.extension.nodeCreated(old.controller);
  old.graph._nodes = [next.controller, next.image]; old.graph._groups = [];
  next.controller.graph = old.graph; next.image.graph = old.graph;
  h.flush();
  assert.deepEqual(old.graph.removed, []);
  assert.equal(old.graph.getNodeById(31), next.controller);
});

test('callbacks of an attached but inactive graph cannot delete its nodes', () => {
  const h = harness(), old = fixture(), next = fixture(); h.use(old.graph);
  h.app.extension.nodeCreated(old.controller);
  old.graph._groups = []; h.use(next.graph); h.flush();
  assert.deepEqual(old.graph.removed, []);
  assert.equal(old.graph.getNodeById(31), old.controller);
  assert.deepEqual(next.graph.removed, []);
});

test('loading without restored groups leaves nodes, modes, order and transactions unchanged', () => {
  const h = harness(), f = fixture(); h.use(f.graph); h.app.configuringGraph = true;
  f.graph._groups = []; h.app.extension.nodeCreated(f.controller); h.flush(); h.tick();
  assert.deepEqual(f.graph.removed, []);
  assert.equal(f.image.mode, core.NODE_MODE.ALWAYS);
  assert.deepEqual(f.graph.extra.ps_ai.node_order, [31, 215]);
  assert.equal(f.graph.changes, 0);
});

test('graph completion rebinds the original controller without replacing the group or member', () => {
  const h = harness(), f = fixture(); h.use(f.graph); h.app.configuringGraph = true;
  f.graph._groups = []; h.app.extension.nodeCreated(f.controller); h.flush(); h.tick();
  f.graph._groups = [f.group]; h.app.extension.afterConfigureGraph();
  h.app.configuringGraph = false; h.flush();
  assert.equal(click(h, f.group), true);
  assert.equal(f.image.mode, core.NODE_MODE.BYPASS);
  assert.equal(f.graph.getNodeById(31), f.controller);
  assert.equal(f.graph._groups[0], f.group);
});

test('clicks and PS_AI requests during configuration cannot change saved group state', () => {
  const h = harness(), f = fixture(); h.use(f.graph); h.tick(); h.app.configuringGraph = true;
  assert.notEqual(click(h, f.group), true);
  assert.equal(h.request(31, false), false);
  assert.equal(f.controller.widgets[0].value, true);
  assert.equal(f.image.mode, core.NODE_MODE.ALWAYS);
  assert.equal(f.graph.changes, 0);
});

test('actual deletion of a live group still removes its owned controller and restores members', () => {
  const h = harness(), f = fixture(); h.use(f.graph); h.tick(); click(h, f.group);
  f.graph._groups = []; h.tick();
  assert.deepEqual(f.graph.removed, [31]);
  assert.equal(f.image.mode, core.NODE_MODE.ALWAYS);
  assert.deepEqual(f.graph.extra.ps_ai.node_order, [215]);
});

test('idle synchronization neither repeatedly saves nor changes established member order', () => {
  const h = harness(), f = fixture(); h.use(f.graph); h.tick();
  const snapshot = JSON.stringify({ flags: f.group.flags, properties: f.controller.properties, extra: f.graph.extra });
  for (let n = 0; n < 10; n++) h.tick();
  assert.equal(JSON.stringify({ flags: f.group.flags, properties: f.controller.properties, extra: f.graph.extra }), snapshot);
  assert.equal(f.graph.changes, 0);
});

test('an orphan group is not silently rebuilt and its saved member history is preserved', () => {
  const h = harness(), f = fixture(); f.graph._nodes = [f.image]; h.use(f.graph); h.tick();
  const before = JSON.stringify(f.group.flags);
  assert.notEqual(click(h, f.group), true);
  assert.equal(JSON.stringify(f.group.flags), before);
  assert.equal(f.graph._nodes.length, 1);
  assert.deepEqual(f.graph.removed, []);
});

test('stale presence-marker callbacks do not rewrite values after their node is detached', () => {
  const h = harness(), f = fixture(); h.use(f.graph);
  const marker = { id: 90, type: 'DatangGroupPresenceMarker', graph: f.graph, properties: {}, mode: 0,
    widgets: [{ name: '组已启用', type: 'toggle', value: true }] };
  f.graph._nodes.push(marker); h.app.extension.nodeCreated(marker);
  marker.graph = null; h.use(fixture().graph); h.flush();
  assert.equal(marker.widgets[0].value, true);
  assert.equal(marker.widgets[0].type, 'toggle');
});

test('repair menu restores missing controller 216 inside the original group with all content preserved', () => {
  const h = harness(), f = fixture();
  f.graph._nodes = [f.image];
  f.group.flags.datang_group_switch = { version: 2, controller_id: 216, enabled: true,
    member_order: [2, 210, 213, 214, 215, 217, 218], other_metadata: 'preserve' };
  f.graph.extra.ps_ai.node_order = [215];
  const bounds = [...f.group._bounding];
  f.graph.links = [[1, 215, 0, 214, 0, 'IMAGE']];
  const links = JSON.stringify(f.graph.links);
  h.use(f.graph);
  const menu = h.app.canvas.getCanvasMenuOptions().find(x => x?.content === '大汤：修复缺失的组开关');
  assert.ok(menu);
  const result = menu.submenu.options[0].callback();
  assert.equal(result.repaired, true);
  assert.equal(result.controller.id, 216);
  assert.equal(f.graph.getNodeById(215), f.image);
  assert.equal(f.graph._groups[0], f.group);
  assert.deepEqual([...f.group._bounding], bounds);
  assert.equal(JSON.stringify(f.graph.links), links);
  assert.equal(f.image.mode, core.NODE_MODE.ALWAYS);
  assert.equal(f.group.flags.datang_group_switch.other_metadata, 'preserve');
  assert.deepEqual(f.group.flags.datang_group_switch.member_order, [2, 210, 213, 214, 215, 217, 218]);
  assert.deepEqual([...f.graph.extra.ps_ai.node_order], [216, 215]);
  assert.equal(click(h, f.group), true);
  assert.equal(f.image.mode, core.NODE_MODE.BYPASS);
  assert.equal(click(h, f.group), true);
  assert.equal(f.image.mode, core.NODE_MODE.ALWAYS);
});

test('repair never overwrites an existing unrelated node occupying the saved controller ID', () => {
  const h = harness(), f = fixture();
  const unrelated = { id: 31, type: 'OtherNode', graph: f.graph, mode: 0, pos: [800, 800], size: [100, 100] };
  f.graph._nodes = [f.image, unrelated]; h.use(f.graph);
  const result = h.repair(f.group);
  assert.equal(f.graph.getNodeById(31), unrelated);
  assert.notEqual(result.controller.id, 31);
  assert.equal(f.group.flags.datang_group_switch.controller_id, result.controller.id);
  assert.equal(f.graph._nodes.length, 3);
});

test('repair is idempotent and the missing-controller menu disappears when the group is healthy', () => {
  const h = harness(), f = fixture(); f.graph._nodes = [f.image]; h.use(f.graph);
  const first = h.repair(f.group), second = h.repair(f.group);
  assert.equal(second.repaired, false);
  assert.equal(second.controller, first.controller);
  assert.equal(f.graph._nodes.length, 2);
  assert.equal(f.graph.changes, 1);
  assert.equal(h.app.canvas.getCanvasMenuOptions().some(x => x?.content === '大汤：修复缺失的组开关'), false);
});

test('disabled orphan groups do not invent their lost original member modes', () => {
  const h = harness(), f = fixture(); f.graph._nodes = [f.image];
  f.group.flags.datang_group_switch.enabled = false; f.image.mode = core.NODE_MODE.BYPASS; h.use(f.graph);
  assert.throws(() => h.repair(f.group), /不能安全自动恢复/);
  assert.equal(f.graph._nodes.length, 1);
  assert.equal(f.image.mode, core.NODE_MODE.BYPASS);
  assert.equal(f.graph.changes, 0);
  const menu = h.app.canvas.getCanvasMenuOptions().find(x => x?.content === '大汤：修复缺失的组开关');
  assert.equal(menu.submenu.options[0].disabled, true);
});

test('repair rejects loading, inactive and plain groups before adding or changing any node', () => {
  const h = harness(), f = fixture(); f.graph._nodes = [f.image]; h.use(f.graph);
  h.app.configuringGraph = true;
  assert.throws(() => h.repair(f.group), /等待当前工作流/);
  assert.equal(h.app.canvas.getCanvasMenuOptions().some(x => x?.content === '大汤：修复缺失的组开关'), false);
  h.app.configuringGraph = false;
  assert.throws(() => h.repair({ graph: f.graph, flags: {} }), /等待当前工作流/);
  const plain = { graph: f.graph, flags: {} }; f.graph._groups.push(plain);
  assert.throws(() => h.repair(plain), /不是大汤开关组/);
  h.app.graph = fixture().graph;
  assert.throws(() => h.repair(f.group), /等待当前工作流/);
  assert.equal(f.graph._nodes.length, 1);
  assert.equal(f.graph.changes, 0);
});

test('repair refuses to overwrite deliberately muted member modes', () => {
  const h = harness(), f = fixture(); f.graph._nodes = [f.image]; f.image.mode = core.NODE_MODE.NEVER; h.use(f.graph);
  assert.throws(() => h.repair(f.group), /单独忽略或停用/);
  assert.equal(f.image.mode, core.NODE_MODE.NEVER);
  assert.equal(f.graph._nodes.length, 1);
  assert.equal(f.graph.changes, 0);
});
