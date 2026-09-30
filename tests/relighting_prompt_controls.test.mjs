import assert from "node:assert/strict";
import test from "node:test";

import {
  migrateRemovedRelightingDegree,
  RELIGHTING_PROMPT_GROUPS,
} from "../web/relighting_prompt_controls_core.js";

function makeNode() {
  return {
    dirty: 0,
    widgets: RELIGHTING_PROMPT_GROUPS.map((name, index) => ({
      name,
      value: "不指定",
      options: { values: ["不指定", `选项${index + 1}`] },
    })),
    setDirtyCanvas() { this.dirty += 1; },
  };
}

test("old eleven-value relighting nodes discard degree and restore the remaining ten by category", () => {
  const node = makeNode();
  const oldValues = ["严格只改光影", ...RELIGHTING_PROMPT_GROUPS.map((_, index) => `选项${index + 1}`)];
  assert.equal(migrateRemovedRelightingDegree(node, { widgets_values: oldValues }), true);
  assert.deepEqual(node.widgets.map((widget) => widget.value), oldValues.slice(1));
  assert.equal(node.dirty, 1);
});

test("new ten-value nodes are not migrated", () => {
  const node = makeNode();
  const values = RELIGHTING_PROMPT_GROUPS.map((_, index) => `选项${index + 1}`);
  assert.equal(migrateRemovedRelightingDegree(node, { widgets_values: values }), false);
  assert.deepEqual(node.widgets.map((widget) => widget.value), Array(10).fill("不指定"));
  assert.equal(node.dirty, 0);
});

test("legacy invalid choices cannot overwrite current valid defaults", () => {
  const node = makeNode();
  const oldValues = ["自然重新打光", "已删除选项", ...RELIGHTING_PROMPT_GROUPS.slice(1).map((_, index) => `选项${index + 2}`)];
  assert.equal(migrateRemovedRelightingDegree(node, { widgets_values: oldValues }), true);
  assert.equal(node.widgets[0].value, "不指定");
  assert.deepEqual(node.widgets.slice(1).map((widget) => widget.value), oldValues.slice(2));
});
