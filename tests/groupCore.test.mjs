import assert from "node:assert/strict";
import test from "node:test";

import {
  chooseDatangGroupController,
  DATANG_GROUP_PRESENCE_NODE_CLASS,
  DATANG_GROUP_FLAG,
  DATANG_PARAMETER_GROUP_FLAG,
  groupHeaderSwitchRect,
  findInnermostDatangGroupForNode,
  indexDatangGroupControllers,
  isDatangGroupPresenceMarker,
  isDatangGroupPresenceEnabled,
  layoutEmbeddedGroupForNodes,
  layoutGroupForNodes,
  layoutParameterGroupForNodes,
  NODE_MODE,
  placeControllerBeforeMembers,
  pointInsideRect,
  readDatangGroupState,
  readDatangParameterGroupState,
  reconcileGroupModes,
  repairRequiredResourceSourceModes,
  rememberDatangGroupMemberOrder,
  removeControllerFromOrder,
  uniqueGroupTitle,
  writeDatangGroupState,
  writeDatangParameterGroupState,
} from "../web/datang_group_core.js";

test("selected nodes receive a native group frame with a controller row above them", () => {
  const result = layoutGroupForNodes([
    { pos: [100, 200], size: [180, 80] },
    { pos: [360, 260], size: [220, 120] },
  ], [260, 82]);
  assert.ok(result.controlPos[1] < 200);
  const [x, y, width, height] = result.bounding;
  assert.ok(x < 100 && y < result.controlPos[1]);
  assert.ok(x + width > 580 && y + height > 380);
});

test("group names remain unique without changing the readable base name", () => {
  assert.equal(uniqueGroupTitle([]), "大汤节点组");
  assert.equal(uniqueGroupTitle([{ title: "大汤节点组" }]), "大汤节点组 2");
  assert.equal(uniqueGroupTitle([{ title: "大汤节点组" }, { title: "大汤节点组 2" }]), "大汤节点组 3");
});

test("new groups reserve a safe native title row and keep the controller inside the header", () => {
  const result = layoutEmbeddedGroupForNodes([
    { pos: [100, 200], size: [180, 80] },
    { pos: [360, 260], size: [220, 120] },
  ]);
  const [x, y, width, height] = result.bounding;
  assert.deepEqual(result.controlPos, [x + 8, y + 8]);
  assert.ok(200 - y >= 60, "member nodes must stay below the visible group title and switch");
  assert.ok(y > 110, "the title row must not leave space for a visible controller node");
  assert.ok(x + width > 580 && y + height > 380);
});

test("parameter groups require at least two nodes and reserve only a native title row", () => {
  assert.throws(() => layoutParameterGroupForNodes([{ pos: [100, 200], size: [180, 80] }]), /至少选中两个/);
  const result = layoutParameterGroupForNodes([
    { pos: [100, 200], size: [180, 80] },
    { pos: [360, 260], size: [220, 120] },
  ]);
  const [x, y, width, height] = result.bounding;
  assert.deepEqual(result, { bounding: [72, 158, 536, 250] });
  assert.equal(200 - y, 42);
  assert.ok(x + width > 580 && y + height > 380);
});

test("parameter group metadata stays separate from switch state", () => {
  const group = { flags: {} };
  assert.equal(readDatangParameterGroupState(group), null);
  assert.deepEqual(writeDatangParameterGroupState(group), { version: 1 });
  assert.deepEqual(group.flags[DATANG_PARAMETER_GROUP_FLAG], { version: 1 });
  assert.equal(readDatangGroupState(group), null);
  assert.equal(group.flags[DATANG_GROUP_FLAG], undefined);
});

test("deleting a group controller also removes it from the saved PS AI order", () => {
  assert.deepEqual(removeControllerFromOrder([1, 350, 2, 3], 350), [1, 2, 3]);
  assert.deepEqual(removeControllerFromOrder(["350", 2], 350), [2]);
});

test("native group switch state survives through the serialised flags object", () => {
  const group = { flags: {} };
  assert.equal(readDatangGroupState(group), null);
  const written = writeDatangGroupState(group, { controllerId: 344, enabled: false });
  assert.deepEqual(written, { version: 2, controller_id: 344, enabled: false });
  assert.deepEqual(group.flags[DATANG_GROUP_FLAG], written);
});

test("moving a native group keeps the historical PS AI member order", () => {
  const group = { flags: {} };
  writeDatangGroupState(group, { controllerId: 345, enabled: true });
  assert.deepEqual(
    rememberDatangGroupMemberOrder(group, [{ id: 30 }, { id: 10 }, { id: 20 }]),
    { memberOrder: [30, 10, 20], changed: true },
  );
  assert.deepEqual(
    rememberDatangGroupMemberOrder(group, [{ id: 20 }, { id: 30 }]),
    { memberOrder: [30, 10, 20], changed: false },
    "a temporary geometry recompute must not discard or reorder missing members",
  );
  assert.deepEqual(
    rememberDatangGroupMemberOrder(group, [{ id: 10 }, { id: 20 }, { id: 30 }, { id: 40 }]),
    { memberOrder: [30, 10, 20, 40], changed: true },
  );
  writeDatangGroupState(group, { controllerId: 345, enabled: false });
  assert.deepEqual(group.flags[DATANG_GROUP_FLAG].member_order, [30, 10, 20, 40]);
});

test("presence markers bind to the smallest containing Datang switch group", () => {
  const marker = { id: 88, type: DATANG_GROUP_PRESENCE_NODE_CLASS };
  const outer = { flags: {}, _nodes: [marker], _bounding: [0, 0, 800, 600] };
  const inner = { flags: {}, _nodes: [marker], _bounding: [100, 100, 300, 200] };
  const plain = { flags: {}, _nodes: [marker], _bounding: [120, 120, 100, 100] };
  writeDatangGroupState(outer, { controllerId: 1, enabled: true });
  writeDatangGroupState(inner, { controllerId: 2, enabled: false });

  assert.equal(isDatangGroupPresenceMarker(marker), true);
  assert.equal(findInnermostDatangGroupForNode([outer, plain, inner], marker), inner);
  assert.equal(isDatangGroupPresenceEnabled([outer, plain, inner], marker), false);
  writeDatangGroupState(inner, { controllerId: 2, enabled: true });
  assert.equal(isDatangGroupPresenceEnabled([outer, plain, inner], marker), true);
  writeDatangGroupState(outer, { controllerId: 1, enabled: false });
  assert.equal(isDatangGroupPresenceEnabled([outer, plain, inner], marker), false);
  assert.equal(findInnermostDatangGroupForNode([plain], marker), null);
  assert.equal(isDatangGroupPresenceEnabled([plain], marker), false);
});

test("a group keeps one canonical controller when duplicate hidden controllers exist", () => {
  const first = { id: 344 };
  const saved = { id: 345 };
  const group = { flags: {} };
  writeDatangGroupState(group, { controllerId: 345, enabled: false });
  assert.equal(chooseDatangGroupController(group, [first, saved]), saved);
  assert.equal(chooseDatangGroupController({ flags: {} }, [first, saved]), first);
});

test("controller indexing resolves every group once and excludes duplicate controllers from canonical work", () => {
  const first = { id: 344, properties: { datang_group_title: "勾选设置扣图" } };
  const saved = { id: 345, properties: { datang_group_title: "勾选设置扣图" } };
  const other = { id: 405, properties: { datang_group_title: "与原图相似度" } };
  const firstGroup = { title: "勾选设置扣图", flags: {}, _nodes: [first, saved], _bounding: [0, 0, 400, 300] };
  const secondGroup = { title: "与原图相似度", flags: {}, _nodes: [other], _bounding: [500, 0, 400, 300] };
  writeDatangGroupState(firstGroup, { controllerId: 345, enabled: false });
  writeDatangGroupState(secondGroup, { controllerId: 405, enabled: true });
  const index = indexDatangGroupControllers([firstGroup, secondGroup], [first, saved, other]);
  assert.equal(index.groupByController.get(first), firstGroup);
  assert.equal(index.groupByController.get(saved), firstGroup);
  assert.equal(index.controllerByGroup.get(firstGroup), saved);
  assert.equal(index.controllerByGroup.get(secondGroup), other);
});

test("renamed groups keep their saved controller binding without title or geometry fallback", () => {
  const controller = { id: 31, properties: { datang_group_title: "大汤节点组" } };
  const group = { title: "大汤组", flags: {}, _nodes: [] };
  writeDatangGroupState(group, { controllerId: 31, enabled: false });

  const index = indexDatangGroupControllers([group], [controller]);

  assert.equal(index.groupByController.get(controller), group);
  assert.equal(index.controllerByGroup.get(group), controller);
});

test("title switch hit target stays in the group header and leaves room for rgthree icons", () => {
  const group = { _bounding: new Float32Array([100, 200, 500, 320]), font_size: 24 };
  const rect = groupHeaderSwitchRect(group);
  assert.deepEqual(rect, [430, 205.8, 78, 22]);
  assert.equal(pointInsideRect(450, 216, rect), true);
  assert.equal(pointInsideRect(590, 216, rect), false);
});

test("a new controller is inserted before selected members without disturbing other order", () => {
  assert.deepEqual(
    placeControllerBeforeMembers([1, 2, 3, 4, 9], 9, [2, 3]),
    [1, 9, 2, 3, 4],
  );
});

test("disabled groups remember member modes and restore nodes that leave or re-enable", () => {
  const first = { id: 1, mode: NODE_MODE.ALWAYS };
  const second = { id: 2, mode: NODE_MODE.NEVER };
  const disabled = reconcileGroupModes({ allNodes: [first, second], members: [first, second], enabled: false });
  assert.deepEqual(disabled.previousModes, { 1: NODE_MODE.ALWAYS, 2: NODE_MODE.NEVER });
  assert.equal(first.mode, NODE_MODE.BYPASS);
  assert.equal(second.mode, NODE_MODE.BYPASS);

  const resized = reconcileGroupModes({
    allNodes: [first, second],
    members: [first],
    enabled: false,
    previousModes: disabled.previousModes,
  });
  assert.equal(second.mode, NODE_MODE.NEVER, "a node removed from a disabled frame must recover its old mode");
  assert.deepEqual(resized.previousModes, { 1: NODE_MODE.ALWAYS });

  const enabled = reconcileGroupModes({
    allNodes: [first, second],
    members: [first],
    enabled: true,
    previousModes: resized.previousModes,
  });
  assert.equal(first.mode, NODE_MODE.ALWAYS);
  assert.deepEqual(enabled.previousModes, {});
});

test("stale group restore metadata re-enables required model clip and vae sources", () => {
  const clipLoader = { id: 727, mode: NODE_MODE.BYPASS, inputs: [] };
  const textEncode = {
    id: 575,
    mode: NODE_MODE.BYPASS,
    inputs: [{ name: "clip", type: "CLIP", link: 6194 }],
    constructor: { nodeData: { input: { required: { clip: ["CLIP", {}] } } } },
  };
  const optionalVaeTarget = {
    id: 900,
    mode: NODE_MODE.BYPASS,
    inputs: [{ name: "optional_vae", type: "VAE", link: 6195 }],
    constructor: { nodeData: { input: { required: {}, optional: { optional_vae: ["VAE", {}] } } } },
  };
  const vaeLoader = { id: 901, mode: NODE_MODE.BYPASS, inputs: [] };
  const previousModes = {
    575: NODE_MODE.ALWAYS,
    727: NODE_MODE.BYPASS,
    900: NODE_MODE.ALWAYS,
    901: NODE_MODE.BYPASS,
  };

  const repaired = repairRequiredResourceSourceModes({
    members: [clipLoader, textEncode, optionalVaeTarget, vaeLoader],
    previousModes,
    links: [
      [6194, 727, 0, 575, 0, "CLIP"],
      [6195, 901, 0, 900, 0, "VAE"],
    ],
  });

  assert.equal(repaired.changed, true);
  assert.equal(repaired.previousModes[727], NODE_MODE.ALWAYS);
  assert.equal(repaired.previousModes[901], NODE_MODE.BYPASS, "optional resource inputs keep an intentional bypass");

  reconcileGroupModes({
    allNodes: [clipLoader, textEncode, optionalVaeTarget, vaeLoader],
    members: [clipLoader, textEncode, optionalVaeTarget, vaeLoader],
    enabled: true,
    previousModes: repaired.previousModes,
  });
  assert.equal(clipLoader.mode, NODE_MODE.ALWAYS);
  assert.equal(textEncode.mode, NODE_MODE.ALWAYS);
  assert.equal(vaeLoader.mode, NODE_MODE.BYPASS);
});
