from pathlib import Path
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1] / "web" / "prompt_switchboard_v16.js"
).read_text(encoding="utf-8")


class FrontendContractTests(unittest.TestCase):
    def test_internal_json_widget_is_hidden_but_kept_for_serialisation(self):
        self.assertIn("function replaceWithHiddenProxy", SCRIPT)
        self.assertIn("node.widgets[widgetIndex] = proxyWidget", SCRIPT)
        self.assertIn("serializeValue: () => storedValue", SCRIPT)
        self.assertIn("widget.hidden = true", SCRIPT)
        self.assertIn('widget.type = "converted-widget"', SCRIPT)
        self.assertIn('type: "converted-widget"', SCRIPT)
        self.assertIn("draw: () => {}", SCRIPT)
        self.assertIn('hiddenElement.style.display = "none"', SCRIPT)
        self.assertNotIn("node.widgets.splice(originalIndex, 1)", SCRIPT)

    def test_native_separator_widget_is_hidden_and_replaced_with_a_labelled_control(self):
        self.assertIn('const SEPARATOR_WIDGET_NAME = "分隔符"', SCRIPT)
        self.assertIn("const internalWidgets = new Set([dataWidget, separatorWidget])", SCRIPT)
        self.assertIn("if (internalWidgets.has(widget)) return false", SCRIPT)
        self.assertIn("hideNativeWidget(separatorWidget)", SCRIPT)
        self.assertIn('separatorLabel.textContent = "分隔符"', SCRIPT)

    def test_misplaced_json_is_migrated_back_to_prompt_data(self):
        self.assertIn("function migrateMisplacedValues", SCRIPT)
        self.assertIn("const misplacedItems = parseItems(separatorWidget.value)", SCRIPT)
        self.assertIn("serialiseItems(recoveredItems, getSelectionMode(recoveredItems))", SCRIPT)
        self.assertIn("setNativeWidgetValue(separatorWidget, recoveredSeparator)", SCRIPT)
        self.assertIn("function normaliseSeparator(value)", SCRIPT)
        self.assertIn('if (!text || parseItems(text)) return ", "', SCRIPT)

    def test_single_select_mode_disables_other_enabled_items(self):
        self.assertIn('return items[0]?._selection_mode === "单选"', SCRIPT)
        self.assertIn("function serialiseItems(items, selectionMode)", SCRIPT)
        self.assertIn('modeSelect.value === "单选"', SCRIPT)
        self.assertIn("if (entryIndex !== index) entry.enabled = false", SCRIPT)
        self.assertIn('allOnButton.disabled = selectionMode === "单选"', SCRIPT)

    def test_prompt_editor_is_a_four_line_textarea(self):
        self.assertIn('document.createElement("textarea")', SCRIPT)
        self.assertIn("input.rows = 4", SCRIPT)
        self.assertIn("height: 88px", SCRIPT)

    def test_each_prompt_row_has_an_editable_persisted_name(self):
        self.assertIn('name: item.name', SCRIPT)
        self.assertIn('nameInput.className = "prompt-switchboard__name"', SCRIPT)
        self.assertIn('nameInput.value = item.name', SCRIPT)
        self.assertIn('item.name = nameInput.value', SCRIPT)
        self.assertIn('content.append(nameInput, input)', SCRIPT)
        self.assertIn('name: nextItemName(items)', SCRIPT)
        self.assertIn('let highestNumber = items.length', SCRIPT)
        self.assertIn('return `提示词 ${highestNumber + 1}`', SCRIPT)

    def test_long_text_scrolls_inside_the_editor(self):
        self.assertIn("overflow-y: auto", SCRIPT)
        self.assertIn("resize: none", SCRIPT)

    def test_node_and_internal_list_resize_with_prompt_count(self):
        self.assertIn("const ROW_BLOCK_HEIGHT = 126", SCRIPT)
        self.assertIn("const desiredNodeHeight = () => Math.max", SCRIPT)
        self.assertIn("NODE_CHROME_HEIGHT + items.length * ROW_BLOCK_HEIGHT", SCRIPT)
        self.assertIn("syncNodeHeight({ force: true })", SCRIPT)
        self.assertIn("pendingForceResize ||= force", SCRIPT)
        self.assertIn("if (shouldForceResize || needsExpansion)", SCRIPT)
        self.assertIn("height: 100%", SCRIPT)
        self.assertIn("flex: 1 1 auto", SCRIPT)
        self.assertIn("getMaxHeight: () => Number.MAX_SAFE_INTEGER", SCRIPT)
        self.assertNotIn("max-height: 520px", SCRIPT)

    def test_wheel_only_stays_inside_when_content_can_scroll(self):
        self.assertIn("function canConsumeWheel(element, deltaY)", SCRIPT)
        self.assertIn("function forwardWheelToCanvas(event)", SCRIPT)
        self.assertIn('canvas.dispatchEvent(new WheelEvent("wheel"', SCRIPT)
        self.assertIn("const shouldScrollPrompt = canConsumeWheel", SCRIPT)
        self.assertIn("const shouldScrollList = canConsumeWheel", SCRIPT)
        self.assertIn("forwardWheelToCanvas(event)", SCRIPT)
        self.assertIn("{ passive: false }", SCRIPT)
        self.assertNotIn(
            'root.addEventListener("wheel", (event) => event.stopPropagation()',
            SCRIPT,
        )

    def test_middle_button_drag_is_forwarded_to_the_canvas(self):
        self.assertIn("let activeCanvasPointerId = null", SCRIPT)
        self.assertIn("let activePointerAction = null", SCRIPT)
        self.assertIn('root.addEventListener("pointerdown"', SCRIPT)
        self.assertIn("const shouldPanCanvas = event.button === 1", SCRIPT)
        self.assertIn("root.setPointerCapture?.(event.pointerId)", SCRIPT)
        self.assertIn("app.canvas?.processMouseDown?.(event)", SCRIPT)
        self.assertIn('root.addEventListener("pointermove"', SCRIPT)
        self.assertIn('activePointerAction === "canvas-pan" ? 4 : 1', SCRIPT)
        self.assertIn("app.canvas?.processMouseMove?.(event)", SCRIPT)
        self.assertIn('root.addEventListener("pointerup", finishCanvasPointerAction)', SCRIPT)
        self.assertIn("app.canvas?.processMouseUp?.(event)", SCRIPT)
        self.assertIn('root.addEventListener("pointercancel", finishCanvasPointerAction)', SCRIPT)
        self.assertIn('root.addEventListener("auxclick"', SCRIPT)

    def test_left_drag_moves_node_from_non_interactive_areas_only(self):
        self.assertIn("function isInteractiveControl(target)", SCRIPT)
        self.assertIn(
            "const shouldDragNode = event.button === 0 && !isInteractiveControl(event.target)",
            SCRIPT,
        )
        self.assertIn("if (!shouldPanCanvas && !shouldDragNode) return", SCRIPT)
        self.assertIn('input, textarea, select, button, label, a, [contenteditable="true"]', SCRIPT)
        self.assertIn('activePointerAction = shouldPanCanvas ? "canvas-pan" : "node-drag"', SCRIPT)
        self.assertIn("app.graph?.beforeChange?.()", SCRIPT)
        self.assertIn("app.canvas?.selectNode?.(node, false)", SCRIPT)
        self.assertIn("const canvasScale = Math.max", SCRIPT)
        self.assertIn("node.pos[0] += (event.clientX - lastPointerClientX) / canvasScale", SCRIPT)
        self.assertIn("node.pos[1] += (event.clientY - lastPointerClientY) / canvasScale", SCRIPT)
        self.assertIn("app.graph?.afterChange?.()", SCRIPT)

    def test_large_add_button_is_below_the_last_prompt_row(self):
        self.assertIn("const ADD_BUTTON_BLOCK_HEIGHT = 50", SCRIPT)
        self.assertIn('addButton.textContent = "+ 添加槽位"', SCRIPT)
        self.assertIn('addFooter.className = "prompt-switchboard__add-footer"', SCRIPT)
        self.assertIn("addFooter.appendChild(addButton)", SCRIPT)
        self.assertIn("toolbar.append(status, allOnButton, allOffButton)", SCRIPT)
        self.assertIn("list.appendChild(addFooter)", SCRIPT)
        self.assertIn("min-height: 38px !important", SCRIPT)
        self.assertNotIn(
            "toolbar.append(status, allOnButton, allOffButton, addButton)",
            SCRIPT,
        )

    def test_delete_button_has_a_larger_click_target(self):
        self.assertIn("grid-template-columns: 36px minmax(0, 1fr) 36px", SCRIPT)
        self.assertIn("width: 36px", SCRIPT)
        self.assertIn("min-height: 36px !important", SCRIPT)

    def test_prompt_rows_can_be_dragged_as_a_group_to_reorder(self):
        self.assertIn('reorderHandle.className = "prompt-switchboard__reorder"', SCRIPT)
        self.assertIn('reorderHandle.textContent = "⠿"', SCRIPT)
        self.assertIn('reorderHandle.addEventListener("pointerdown"', SCRIPT)
        self.assertIn('reorderHandle.addEventListener("pointermove"', SCRIPT)
        self.assertIn('reorderHandle.addEventListener("pointerup", finishRowPointerDrag)', SCRIPT)
        self.assertIn('reorderHandle.addEventListener("pointercancel", finishRowPointerDrag)', SCRIPT)
        self.assertIn("reorderHandle.setPointerCapture?.(event.pointerId)", SCRIPT)
        self.assertIn("const updateDraggedRowDropTarget = (clientY)", SCRIPT)
        self.assertIn("list.scrollTop -= 12", SCRIPT)
        self.assertIn("list.scrollTop += 12", SCRIPT)
        self.assertIn("const moveDraggedRow = (targetIndex, insertAfter)", SCRIPT)
        self.assertIn("const [movedItem] = items.splice(fromIndex, 1)", SCRIPT)
        self.assertIn("items.splice(insertionIndex, 0, movedItem)", SCRIPT)
        self.assertIn("render()", SCRIPT)
        self.assertIn("notifyChanged()", SCRIPT)
        self.assertIn("rowControls.append(reorderHandle, toggleLabel)", SCRIPT)
        self.assertNotIn('reorderHandle.addEventListener("dragstart"', SCRIPT)

    def test_visual_widget_does_not_duplicate_workflow_data(self):
        self.assertIn("domWidget.serialize = false", SCRIPT)


if __name__ == "__main__":
    unittest.main()
