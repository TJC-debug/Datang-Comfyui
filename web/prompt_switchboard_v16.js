import { app } from "../../../scripts/app.js";

const NODE_CLASS = "PromptSwitchboard";
const DATA_WIDGET_NAME = "提示词数据";
const SEPARATOR_WIDGET_NAME = "分隔符";
const DEFAULT_ITEMS = [{ name: "提示词 1", text: "", enabled: true }];
const MIN_NODE_HEIGHT = 380;
const NODE_CHROME_HEIGHT = 190;
const ROW_BLOCK_HEIGHT = 126;
const ADD_BUTTON_BLOCK_HEIGHT = 50;

function parseItems(value) {
    let parsed = value;
    if (typeof parsed === "string") {
        try {
            parsed = JSON.parse(parsed);
        } catch {
            return null;
        }
    }
    if (!Array.isArray(parsed) || parsed.length === 0) return null;
    const selectionMode = parsed[0]?._selection_mode === "单选" ? "单选" : "多选";
    return parsed.map((item, index) => ({
        name: typeof item === "string"
            ? `提示词 ${index + 1}`
            : String(item?.name ?? `提示词 ${index + 1}`),
        text: typeof item === "string" ? item : String(item?.text ?? ""),
        enabled: typeof item === "string" ? true : item?.enabled !== false,
        ...(index === 0 ? { _selection_mode: selectionMode } : {}),
    }));
}

function normaliseItems(value) {
    return parseItems(value) ?? DEFAULT_ITEMS.map((item) => ({ ...item }));
}

function getSelectionMode(items) {
    return items[0]?._selection_mode === "单选" ? "单选" : "多选";
}

function serialiseItems(items, selectionMode) {
    return JSON.stringify(items.map((item, index) => ({
        name: item.name,
        text: item.text,
        enabled: item.enabled,
        ...(index === 0 ? { _selection_mode: selectionMode } : {}),
    })));
}

function normaliseSeparator(value) {
    const text = String(value ?? "");
    const trimmed = text.trim();
    if (!text || parseItems(text)) return ", ";
    if (trimmed.startsWith("[") && trimmed.includes('"text"')) return ", ";
    return text;
}

function nextItemName(items) {
    let highestNumber = items.length;
    for (const item of items) {
        const match = /^提示词\s+(\d+)$/.exec(item.name.trim());
        if (match) highestNumber = Math.max(highestNumber, Number(match[1]));
    }
    return `提示词 ${highestNumber + 1}`;
}

function canConsumeWheel(element, deltaY) {
    if (!element || deltaY === 0 || element.scrollHeight <= element.clientHeight + 1) {
        return false;
    }
    if (deltaY < 0) return element.scrollTop > 1;
    return element.scrollTop + element.clientHeight < element.scrollHeight - 1;
}

function isInteractiveControl(target) {
    if (!(target instanceof Element)) return false;
    return Boolean(target.closest(
        'input, textarea, select, button, label, a, [contenteditable="true"]',
    ));
}

function forwardWheelToCanvas(event) {
    const canvas = app.canvas?.canvas;
    if (!(canvas instanceof HTMLCanvasElement)) return;
    canvas.dispatchEvent(new WheelEvent("wheel", {
        bubbles: true,
        cancelable: true,
        clientX: event.clientX,
        clientY: event.clientY,
        deltaMode: event.deltaMode,
        deltaX: event.deltaX,
        deltaY: event.deltaY,
        ctrlKey: event.ctrlKey,
        shiftKey: event.shiftKey,
        altKey: event.altKey,
        metaKey: event.metaKey,
    }));
}

function setNativeWidgetValue(widget, value) {
    if (typeof widget.options?.setValue === "function") {
        widget.options.setValue(value);
    } else if (widget.inputEl) {
        widget.inputEl.value = value;
    }
}

function hideNativeWidget(widget) {
    widget.hidden = true;
    // LiteGraph's canvas renderer does not treat the literal "hidden" type
    // as invisible for classic widgets. ComfyUI uses "converted-widget" for
    // widgets that must keep serialising without occupying or drawing a row.
    widget.type = "converted-widget";
    const hiddenElement = widget.element ?? widget.inputEl;
    if (hiddenElement) {
        hiddenElement.style.display = "none";
        hiddenElement.setAttribute?.("aria-hidden", "true");
    }
    widget.computeSize = () => [0, -4];
    widget.computeLayoutSize = () => ({
        minHeight: 0,
        maxHeight: 0,
        minWidth: 0,
    });
    widget.options = widget.options ?? {};
    widget.options.getMinHeight = () => 0;
    widget.options.getMaxHeight = () => 0;
}

function replaceWithHiddenProxy(node, originalWidget) {
    const widgetIndex = node.widgets?.indexOf(originalWidget) ?? -1;
    if (widgetIndex < 0) return null;

    let storedValue = originalWidget.value;
    hideNativeWidget(originalWidget);
    originalWidget.onRemove?.();

    const proxyOptions = { ...(originalWidget.options ?? {}) };
    proxyOptions.getValue = () => storedValue;
    proxyOptions.setValue = (value) => { storedValue = value; };
    proxyOptions.getMinHeight = () => 0;
    proxyOptions.getMaxHeight = () => 0;

    const proxyWidget = {
        name: originalWidget.name,
        type: "converted-widget",
        hidden: true,
        serialize: originalWidget.serialize !== false,
        options: proxyOptions,
        callback: originalWidget.callback,
        computeSize: () => [0, -4],
        computeLayoutSize: () => ({ minHeight: 0, maxHeight: 0, minWidth: 0 }),
        draw: () => {},
        serializeValue: () => storedValue,
    };
    Object.defineProperty(proxyWidget, "value", {
        configurable: true,
        enumerable: true,
        get: () => storedValue,
        set: (value) => {
            storedValue = value;
            proxyWidget.callback?.(storedValue);
        },
    });

    node.widgets[widgetIndex] = proxyWidget;
    requestAnimationFrame(() => originalWidget.onRemove?.());
    return proxyWidget;
}

function migrateMisplacedValues(dataWidget, separatorWidget) {
    const dataItems = parseItems(dataWidget.value);
    const misplacedItems = parseItems(separatorWidget.value);
    if (!misplacedItems) return;

    const dataHasText = dataItems?.some((item) => item.text.trim().length > 0) ?? false;
    const recoveredItems = dataHasText ? dataItems : misplacedItems;
    const recoveredSeparator = dataItems ? ", " : normaliseSeparator(dataWidget.value);

    setNativeWidgetValue(
        dataWidget,
        serialiseItems(recoveredItems, getSelectionMode(recoveredItems)),
    );
    setNativeWidgetValue(separatorWidget, recoveredSeparator);
}

function installStyles() {
    if (document.getElementById("prompt-switchboard-styles")) return;
    const style = document.createElement("style");
    style.id = "prompt-switchboard-styles";
    style.textContent = `
        .prompt-switchboard {
            box-sizing: border-box;
            display: flex;
            height: 100%;
            min-height: 0;
            flex-direction: column;
            gap: 8px;
            padding: 4px 2px 8px;
            color: var(--input-text, #ddd);
            font: 12px/1.35 system-ui, -apple-system, "Segoe UI", sans-serif;
        }
        .prompt-switchboard__toolbar {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .prompt-switchboard__settings {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 7px;
            min-height: 28px;
        }
        .prompt-switchboard__settings-label {
            flex: 0 0 auto;
            color: var(--descrip-text, #bbb);
        }
        .prompt-switchboard__separator {
            box-sizing: border-box;
            width: 88px;
            height: 27px;
            padding: 3px 8px;
            border: 1px solid var(--border-color, #555);
            border-radius: 6px;
            outline: none;
            background: var(--comfy-input-bg, #202020);
            color: var(--input-text, #eee);
            font: inherit;
        }
        .prompt-switchboard__mode {
            box-sizing: border-box;
            width: 82px;
            height: 27px;
            padding: 3px 6px;
            border: 1px solid var(--border-color, #555);
            border-radius: 6px;
            outline: none;
            background: var(--comfy-input-bg, #202020);
            color: var(--input-text, #eee);
            font: inherit;
        }
        .prompt-switchboard__separator:focus,
        .prompt-switchboard__mode:focus {
            border-color: var(--p-button-primary-border-color, #7aa2f7);
        }
        .prompt-switchboard__settings-hint {
            overflow: hidden;
            color: var(--descrip-text, #888);
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .prompt-switchboard__status {
            flex: 1;
            min-width: 0;
            color: var(--descrip-text, #aaa);
            white-space: nowrap;
        }
        .prompt-switchboard button {
            box-sizing: border-box;
            min-height: 25px;
            padding: 3px 8px;
            border: 1px solid var(--border-color, #555);
            border-radius: 6px;
            background: var(--comfy-input-bg, #282828);
            color: var(--input-text, #ddd);
            cursor: pointer;
            font: inherit;
        }
        .prompt-switchboard button:hover {
            border-color: var(--p-button-primary-border-color, #7aa2f7);
        }
        .prompt-switchboard__add {
            width: 100%;
            min-height: 38px !important;
            border-style: dashed !important;
            font-size: 14px !important;
            font-weight: 600;
        }
        .prompt-switchboard__add-footer {
            display: flex;
            flex: 0 0 auto;
            padding: 4px 40px 2px 42px;
        }
        .prompt-switchboard__list {
            display: flex;
            min-height: 0;
            flex: 1 1 auto;
            flex-direction: column;
            gap: 6px;
            overflow-x: hidden;
            overflow-y: auto;
            padding-right: 2px;
        }
        .prompt-switchboard__row {
            position: relative;
            display: grid;
            grid-template-columns: 36px minmax(0, 1fr) 36px;
            align-items: start;
            gap: 6px;
        }
        .prompt-switchboard__row--dragging {
            opacity: .42;
        }
        .prompt-switchboard__row--drop-before {
            box-shadow: 0 -2px 0 #4f8cff;
        }
        .prompt-switchboard__row--drop-after {
            box-shadow: 0 2px 0 #4f8cff;
        }
        .prompt-switchboard__row-controls {
            display: flex;
            width: 36px;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }
        .prompt-switchboard__reorder {
            width: 34px;
            min-height: 32px !important;
            padding: 0 !important;
            color: var(--descrip-text, #bbb) !important;
            cursor: grab !important;
            font-size: 19px !important;
            line-height: 1 !important;
            user-select: none;
        }
        .prompt-switchboard__reorder:active {
            cursor: grabbing !important;
        }
        .prompt-switchboard__add-footer--drop-target .prompt-switchboard__add {
            border-color: #4f8cff !important;
            background: rgba(79, 140, 255, .18);
        }
        .prompt-switchboard__content {
            display: flex;
            min-width: 0;
            flex-direction: column;
            gap: 5px;
        }
        .prompt-switchboard__name {
            box-sizing: border-box;
            width: 100%;
            height: 27px;
            min-width: 0;
            padding: 3px 9px;
            border: 1px solid var(--border-color, #555);
            border-radius: 7px;
            outline: none;
            background: var(--comfy-input-bg, #202020);
            color: var(--input-text, #eee);
            font: inherit;
            font-weight: 600;
        }
        .prompt-switchboard__input {
            box-sizing: border-box;
            width: 100%;
            height: 88px;
            min-width: 0;
            padding: 7px 9px;
            border: 1px solid var(--border-color, #555);
            border-radius: 7px;
            outline: none;
            background: var(--comfy-input-bg, #202020);
            color: var(--input-text, #eee);
            font: inherit;
            line-height: 1.45;
            overflow-x: hidden;
            overflow-y: auto;
            resize: none;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .prompt-switchboard__name:focus,
        .prompt-switchboard__input:focus {
            border-color: var(--p-button-primary-border-color, #7aa2f7);
        }
        .prompt-switchboard__row--disabled .prompt-switchboard__input {
            opacity: .52;
        }
        .prompt-switchboard__toggle {
            position: relative;
            display: inline-flex;
            width: 34px;
            height: 20px;
            margin-top: 0;
            cursor: pointer;
        }
        .prompt-switchboard__toggle input {
            position: absolute;
            opacity: 0;
            pointer-events: none;
        }
        .prompt-switchboard__track {
            width: 34px;
            height: 20px;
            border-radius: 999px;
            background: #555;
            transition: background .15s ease;
        }
        .prompt-switchboard__track::after {
            content: "";
            position: absolute;
            top: 3px;
            left: 3px;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #e8e8e8;
            transition: transform .15s ease;
        }
        .prompt-switchboard__toggle input:checked + .prompt-switchboard__track {
            background: #4f8cff;
        }
        .prompt-switchboard__toggle input:checked + .prompt-switchboard__track::after {
            transform: translateX(14px);
        }
        .prompt-switchboard__delete {
            width: 36px;
            min-height: 36px !important;
            margin-top: 0;
            padding: 0 !important;
            color: #c9c9c9 !important;
            font-size: 19px !important;
        }
    `;
    document.head.appendChild(style);
}

function createSwitchboard(node, dataWidget, separatorWidget) {
    let items = normaliseItems(dataWidget.value);
    let selectionMode = getSelectionMode(items);
    const root = document.createElement("div");
    root.className = "prompt-switchboard";

    const settings = document.createElement("div");
    settings.className = "prompt-switchboard__settings";

    const separatorLabel = document.createElement("label");
    separatorLabel.className = "prompt-switchboard__settings-label";
    separatorLabel.textContent = "分隔符";

    const separatorInput = document.createElement("input");
    separatorInput.type = "text";
    separatorInput.className = "prompt-switchboard__separator";
    separatorInput.value = normaliseSeparator(separatorWidget.value);
    separatorInput.placeholder = ", ";
    separatorInput.title = "启用的提示词之间使用的分隔符";
    separatorInput.spellcheck = false;
    separatorLabel.htmlFor = `prompt-switchboard-separator-${node.id ?? "new"}`;
    separatorInput.id = separatorLabel.htmlFor;

    const modeLabel = document.createElement("label");
    modeLabel.className = "prompt-switchboard__settings-label";
    modeLabel.textContent = "选择模式";

    const modeSelect = document.createElement("select");
    modeSelect.className = "prompt-switchboard__mode";
    modeSelect.id = `prompt-switchboard-mode-${node.id ?? "new"}`;
    modeLabel.htmlFor = modeSelect.id;
    for (const mode of ["多选", "单选"]) {
        const option = document.createElement("option");
        option.value = mode;
        option.textContent = mode;
        modeSelect.appendChild(option);
    }
    modeSelect.value = selectionMode;
    modeSelect.title = "单选模式下开启一项会自动关闭其他项";

    const separatorHint = document.createElement("span");
    separatorHint.className = "prompt-switchboard__settings-hint";
    separatorHint.textContent = "分隔已开启的提示词";
    settings.append(separatorLabel, separatorInput, modeLabel, modeSelect, separatorHint);

    const toolbar = document.createElement("div");
    toolbar.className = "prompt-switchboard__toolbar";

    const status = document.createElement("span");
    status.className = "prompt-switchboard__status";

    const allOnButton = document.createElement("button");
    allOnButton.type = "button";
    allOnButton.textContent = "全开";
    allOnButton.title = "开启全部提示词";

    const allOffButton = document.createElement("button");
    allOffButton.type = "button";
    allOffButton.textContent = "全关";
    allOffButton.title = "关闭全部提示词";

    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.className = "prompt-switchboard__add";
    addButton.textContent = "+ 添加槽位";
    addButton.title = "新增一个提示词槽位（数量不限）";

    const addFooter = document.createElement("div");
    addFooter.className = "prompt-switchboard__add-footer";
    addFooter.appendChild(addButton);

    toolbar.append(status, allOnButton, allOffButton);

    const list = document.createElement("div");
    list.className = "prompt-switchboard__list";
    root.append(settings, toolbar, list);

    let domWidget;
    let resizeScheduled = false;
    let pendingForceResize = false;

    const desiredNodeHeight = () => Math.max(
        MIN_NODE_HEIGHT,
        NODE_CHROME_HEIGHT + items.length * ROW_BLOCK_HEIGHT + ADD_BUTTON_BLOCK_HEIGHT,
    );

    const syncNodeHeight = ({ force = false } = {}) => {
        pendingForceResize ||= force;
        if (resizeScheduled) return;
        resizeScheduled = true;
        requestAnimationFrame(() => {
            resizeScheduled = false;
            const shouldForceResize = pendingForceResize;
            pendingForceResize = false;
            const desiredHeight = desiredNodeHeight();
            const currentHeight = Number(node.size?.[1] ?? 0);
            const currentWidth = Math.max(Number(node.size?.[0] ?? 0), 420);
            const needsExpansion = currentHeight < desiredHeight - 1;

            if (shouldForceResize || needsExpansion) {
                node.setSize?.([currentWidth, desiredHeight]);
                node.setDirtyCanvas?.(true, true);
                app.graph?.setDirtyCanvas?.(true, true);
            }
        });
    };

    const enforceSingleSelection = () => {
        if (selectionMode !== "单选") return false;
        let foundEnabled = false;
        let changed = false;
        for (const item of items) {
            if (!item.enabled) continue;
            if (!foundEnabled) {
                foundEnabled = true;
            } else {
                item.enabled = false;
                changed = true;
            }
        }
        return changed;
    };

    const notifyChanged = () => {
        const serialised = serialiseItems(items, selectionMode);
        setNativeWidgetValue(dataWidget, serialised);
        node.setDirtyCanvas?.(true, true);
        app.graph?.setDirtyCanvas?.(true, true);
    };

    const notifySeparatorChanged = () => {
        setNativeWidgetValue(separatorWidget, separatorInput.value);
        node.setDirtyCanvas?.(true, true);
        app.graph?.setDirtyCanvas?.(true, true);
    };

    let draggedRowIndex = null;
    let draggedRowPointerId = null;
    let draggedRowDropTarget = null;

    const clearRowDropIndicators = ({ keepDragging = false } = {}) => {
        list.querySelectorAll(".prompt-switchboard__row").forEach((row) => {
            row.classList.remove(
                "prompt-switchboard__row--drop-before",
                "prompt-switchboard__row--drop-after",
            );
            if (!keepDragging) row.classList.remove("prompt-switchboard__row--dragging");
        });
        addFooter.classList.remove("prompt-switchboard__add-footer--drop-target");
    };

    const updateDraggedRowDropTarget = (clientY) => {
        const listBounds = list.getBoundingClientRect();
        const autoScrollEdge = 28;
        if (clientY < listBounds.top + autoScrollEdge) {
            list.scrollTop -= 12;
        } else if (clientY > listBounds.bottom - autoScrollEdge) {
            list.scrollTop += 12;
        }

        const rows = Array.from(list.querySelectorAll(".prompt-switchboard__row"));
        if (rows.length === 0) return;

        let target = {
            targetIndex: Number(rows.at(-1).dataset.index),
            insertAfter: true,
        };
        for (const candidate of rows) {
            const bounds = candidate.getBoundingClientRect();
            if (clientY < bounds.top + bounds.height / 2) {
                target = {
                    targetIndex: Number(candidate.dataset.index),
                    insertAfter: false,
                };
                break;
            }
        }

        draggedRowDropTarget = target;
        clearRowDropIndicators({ keepDragging: true });
        if (target.targetIndex === items.length - 1 && target.insertAfter) {
            addFooter.classList.add("prompt-switchboard__add-footer--drop-target");
            return;
        }
        const targetRow = rows.find(
            (candidate) => Number(candidate.dataset.index) === target.targetIndex,
        );
        targetRow?.classList.add(target.insertAfter
            ? "prompt-switchboard__row--drop-after"
            : "prompt-switchboard__row--drop-before");
    };

    const moveDraggedRow = (targetIndex, insertAfter) => {
        const fromIndex = draggedRowIndex;
        if (!Number.isInteger(fromIndex)) return;

        let insertionIndex = targetIndex + (insertAfter ? 1 : 0);
        const [movedItem] = items.splice(fromIndex, 1);
        if (fromIndex < insertionIndex) insertionIndex -= 1;
        insertionIndex = Math.max(0, Math.min(insertionIndex, items.length));
        items.splice(insertionIndex, 0, movedItem);
        draggedRowIndex = null;
        draggedRowPointerId = null;
        draggedRowDropTarget = null;
        clearRowDropIndicators();
        render();
        notifyChanged();
    };

    const render = () => {
        list.replaceChildren();
        const enabledCount = items.filter((item) => item.enabled).length;
        status.textContent = `${enabledCount}/${items.length} 已开启`;
        allOnButton.disabled = selectionMode === "单选";
        allOnButton.title = selectionMode === "单选"
            ? "单选模式不能全部开启"
            : "开启全部提示词";

        items.forEach((item, index) => {
            const row = document.createElement("div");
            row.className = `prompt-switchboard__row${item.enabled ? "" : " prompt-switchboard__row--disabled"}`;
            row.dataset.index = String(index);

            const rowControls = document.createElement("div");
            rowControls.className = "prompt-switchboard__row-controls";

            const reorderHandle = document.createElement("button");
            reorderHandle.type = "button";
            reorderHandle.className = "prompt-switchboard__reorder";
            reorderHandle.textContent = "⠿";
            reorderHandle.title = "按住上下拖动，调整整个槽位的顺序";
            reorderHandle.setAttribute("aria-label", `调整提示词 ${index + 1} 顺序`);

            const toggleLabel = document.createElement("label");
            toggleLabel.className = "prompt-switchboard__toggle";
            toggleLabel.title = item.enabled ? "点击关闭此提示词" : "点击开启此提示词";
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.checked = item.enabled;
            checkbox.setAttribute("aria-label", `提示词 ${index + 1} 开关`);
            const track = document.createElement("span");
            track.className = "prompt-switchboard__track";
            toggleLabel.append(checkbox, track);

            const content = document.createElement("div");
            content.className = "prompt-switchboard__content";

            const nameInput = document.createElement("input");
            nameInput.type = "text";
            nameInput.className = "prompt-switchboard__name";
            nameInput.value = item.name;
            nameInput.placeholder = `提示词 ${index + 1} 名称`;
            nameInput.title = "此名称仅用于辨认槽位，不会加入提示词输出";
            nameInput.spellcheck = false;
            nameInput.setAttribute("aria-label", `提示词 ${index + 1} 名称`);

            const input = document.createElement("textarea");
            input.className = "prompt-switchboard__input";
            input.value = item.text;
            input.placeholder = `提示词 ${index + 1}`;
            input.title = item.text;
            input.rows = 4;
            input.spellcheck = false;
            input.setAttribute("aria-label", `提示词 ${index + 1} 内容`);

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "prompt-switchboard__delete";
            deleteButton.textContent = "×";
            deleteButton.title = "删除此槽位";
            deleteButton.setAttribute("aria-label", `删除提示词 ${index + 1}`);

            reorderHandle.addEventListener("pointerdown", (event) => {
                if (event.button !== 0) return;
                event.preventDefault();
                event.stopPropagation();
                draggedRowIndex = index;
                draggedRowPointerId = event.pointerId;
                draggedRowDropTarget = null;
                row.classList.add("prompt-switchboard__row--dragging");
                reorderHandle.setPointerCapture?.(event.pointerId);
            });
            reorderHandle.addEventListener("pointermove", (event) => {
                if (event.pointerId !== draggedRowPointerId || (event.buttons & 1) !== 1) return;
                event.preventDefault();
                event.stopPropagation();
                updateDraggedRowDropTarget(event.clientY);
            });
            const finishRowPointerDrag = (event) => {
                if (event.pointerId !== draggedRowPointerId) return;
                event.preventDefault();
                event.stopPropagation();
                if (reorderHandle.hasPointerCapture?.(event.pointerId)) {
                    reorderHandle.releasePointerCapture(event.pointerId);
                }
                const target = draggedRowDropTarget;
                if (target && event.type !== "pointercancel") {
                    moveDraggedRow(target.targetIndex, target.insertAfter);
                    return;
                }
                draggedRowIndex = null;
                draggedRowPointerId = null;
                draggedRowDropTarget = null;
                clearRowDropIndicators();
            };
            reorderHandle.addEventListener("pointerup", finishRowPointerDrag);
            reorderHandle.addEventListener("pointercancel", finishRowPointerDrag);

            checkbox.addEventListener("change", () => {
                item.enabled = checkbox.checked;
                if (selectionMode === "单选" && item.enabled) {
                    items.forEach((entry, entryIndex) => {
                        if (entryIndex !== index) entry.enabled = false;
                    });
                    render();
                } else {
                    row.classList.toggle("prompt-switchboard__row--disabled", !item.enabled);
                    toggleLabel.title = item.enabled ? "点击关闭此提示词" : "点击开启此提示词";
                    status.textContent = `${items.filter((entry) => entry.enabled).length}/${items.length} 已开启`;
                }
                notifyChanged();
            });

            nameInput.addEventListener("input", () => {
                item.name = nameInput.value;
                notifyChanged();
            });
            nameInput.addEventListener("keydown", (event) => event.stopPropagation());

            input.addEventListener("input", () => {
                item.text = input.value;
                input.title = input.value;
                notifyChanged();
            });
            input.addEventListener("keydown", (event) => event.stopPropagation());

            deleteButton.addEventListener("click", () => {
                items.splice(index, 1);
                if (items.length === 0) {
                    items.push({ name: "提示词 1", text: "", enabled: true });
                }
                render();
                syncNodeHeight({ force: true });
                notifyChanged();
            });

            rowControls.append(reorderHandle, toggleLabel);
            content.append(nameInput, input);
            row.append(rowControls, content, deleteButton);
            list.appendChild(row);
        });
        list.appendChild(addFooter);
    };

    allOnButton.addEventListener("click", () => {
        items.forEach((item) => { item.enabled = true; });
        render();
        notifyChanged();
    });

    allOffButton.addEventListener("click", () => {
        items.forEach((item) => { item.enabled = false; });
        render();
        notifyChanged();
    });

    addButton.addEventListener("click", () => {
        items.push({
            name: nextItemName(items),
            text: "",
            enabled: selectionMode !== "单选",
        });
        render();
        syncNodeHeight({ force: true });
        notifyChanged();
        requestAnimationFrame(() => {
            const rows = list.querySelectorAll(".prompt-switchboard__row");
            rows.item(rows.length - 1)?.querySelector("textarea")?.focus();
            list.scrollTop = list.scrollHeight;
        });
    });

    separatorInput.addEventListener("input", notifySeparatorChanged);
    separatorInput.addEventListener("keydown", (event) => event.stopPropagation());

    modeSelect.addEventListener("change", () => {
        selectionMode = modeSelect.value === "单选" ? "单选" : "多选";
        enforceSingleSelection();
        render();
        notifyChanged();
    });
    modeSelect.addEventListener("keydown", (event) => event.stopPropagation());

    let activeCanvasPointerId = null;
    let activePointerAction = null;
    let lastPointerClientX = 0;
    let lastPointerClientY = 0;

    root.addEventListener("pointerdown", (event) => {
        event.stopPropagation();
        const shouldPanCanvas = event.button === 1;
        const shouldDragNode = event.button === 0 && !isInteractiveControl(event.target);
        if (!shouldPanCanvas && !shouldDragNode) return;

        event.preventDefault();
        activeCanvasPointerId = event.pointerId;
        activePointerAction = shouldPanCanvas ? "canvas-pan" : "node-drag";
        lastPointerClientX = event.clientX;
        lastPointerClientY = event.clientY;
        root.setPointerCapture?.(event.pointerId);
        if (activePointerAction === "canvas-pan") {
            app.canvas?.processMouseDown?.(event);
        } else {
            app.graph?.beforeChange?.();
            app.canvas?.selectNode?.(node, false);
        }
    });
    root.addEventListener("pointermove", (event) => {
        if (event.pointerId !== activeCanvasPointerId) return;
        const activeButtonMask = activePointerAction === "canvas-pan" ? 4 : 1;
        if ((event.buttons & activeButtonMask) !== activeButtonMask) return;
        event.preventDefault();
        event.stopPropagation();
        if (activePointerAction === "canvas-pan") {
            app.canvas?.processMouseMove?.(event);
            return;
        }

        const canvasScale = Math.max(Number(app.canvas?.ds?.scale ?? 1), 0.0001);
        node.pos[0] += (event.clientX - lastPointerClientX) / canvasScale;
        node.pos[1] += (event.clientY - lastPointerClientY) / canvasScale;
        lastPointerClientX = event.clientX;
        lastPointerClientY = event.clientY;
        node.setDirtyCanvas?.(true, true);
        app.graph?.setDirtyCanvas?.(true, true);
    });
    const finishCanvasPointerAction = (event) => {
        if (event.pointerId !== activeCanvasPointerId) return;
        const expectedButton = activePointerAction === "canvas-pan" ? 1 : 0;
        if (event.type !== "pointercancel" && event.button !== expectedButton) return;
        event.preventDefault();
        event.stopPropagation();
        if (activePointerAction === "canvas-pan") {
            app.canvas?.processMouseUp?.(event);
        } else {
            app.graph?.afterChange?.();
            node.setDirtyCanvas?.(true, true);
            app.graph?.setDirtyCanvas?.(true, true);
        }
        if (root.hasPointerCapture?.(event.pointerId)) {
            root.releasePointerCapture(event.pointerId);
        }
        activeCanvasPointerId = null;
        activePointerAction = null;
    };
    root.addEventListener("pointerup", finishCanvasPointerAction);
    root.addEventListener("pointercancel", finishCanvasPointerAction);
    root.addEventListener("auxclick", (event) => {
        if (event.button !== 1) return;
        event.preventDefault();
        event.stopPropagation();
    });
    root.addEventListener("wheel", (event) => {
        const target = event.target instanceof Element ? event.target : null;
        const promptEditor = target?.closest(".prompt-switchboard__input");
        const shouldScrollPrompt = canConsumeWheel(promptEditor, event.deltaY);
        const shouldScrollList = canConsumeWheel(list, event.deltaY);
        if (shouldScrollPrompt || shouldScrollList) {
            event.stopPropagation();
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        forwardWheelToCanvas(event);
    }, { passive: false });

    domWidget = node.addDOMWidget("提示词槽位", "prompt-switchboard", root, {
        getValue: () => "",
        setValue: () => {},
        getMinHeight: () => Math.max(
            120,
            75 + items.length * ROW_BLOCK_HEIGHT + ADD_BUTTON_BLOCK_HEIGHT,
        ),
        getMaxHeight: () => Number.MAX_SAFE_INTEGER,
        hideOnZoom: false,
    });
    domWidget.serialize = false;
    domWidget.serializeValue = () => undefined;
    domWidget.inputEl = root;
    domWidget.options.minNodeSize = [400, 260];
    render();
    syncNodeHeight({ force: true });
    return {
        widget: domWidget,
        setValue(value) {
            items = normaliseItems(value);
            selectionMode = getSelectionMode(items);
            modeSelect.value = selectionMode;
            enforceSingleSelection();
            render();
            syncNodeHeight({ force: true });
        },
        setSeparator(value) {
            const separator = normaliseSeparator(value);
            separatorInput.value = separator;
            if (separator !== value) setNativeWidgetValue(separatorWidget, separator);
        },
    };
}

app.registerExtension({
    name: "Datang.PromptSwitchboard",
    async nodeCreated(node) {
        if (node.comfyClass !== NODE_CLASS) return;
        installStyles();

        const originalDataWidget = node.widgets?.find((widget) => widget.name === DATA_WIDGET_NAME);
        const originalSeparatorWidget = node.widgets?.find((widget) => widget.name === SEPARATOR_WIDGET_NAME);
        if (!originalDataWidget || !originalSeparatorWidget) return;

        const dataWidget = replaceWithHiddenProxy(node, originalDataWidget);
        const separatorWidget = replaceWithHiddenProxy(node, originalSeparatorWidget);
        if (!dataWidget || !separatorWidget) return;

        const internalWidgets = new Set([dataWidget, separatorWidget]);
        const originalIsWidgetVisible = node.isWidgetVisible?.bind(node);
        node.isWidgetVisible = (widget) => {
            if (internalWidgets.has(widget)) return false;
            return originalIsWidgetVisible ? originalIsWidgetVisible(widget) : !widget.hidden;
        };

        hideNativeWidget(dataWidget);
        hideNativeWidget(separatorWidget);

        const switchboard = createSwitchboard(node, dataWidget, separatorWidget);
        let syncScheduled = false;
        const scheduleSync = () => {
            if (syncScheduled) return;
            syncScheduled = true;
            requestAnimationFrame(() => {
                syncScheduled = false;
                hideNativeWidget(dataWidget);
                hideNativeWidget(separatorWidget);
                migrateMisplacedValues(dataWidget, separatorWidget);
                switchboard.setValue(dataWidget.value);
                switchboard.setSeparator(separatorWidget.value);
                node.setDirtyCanvas?.(true, true);
            });
        };

        for (const widget of [dataWidget, separatorWidget]) {
            const originalCallback = widget.callback;
            widget.callback = function () {
                originalCallback?.apply(this, arguments);
                scheduleSync();
            };
        }
        scheduleSync();

        node.size[0] = Math.max(node.size[0], 420);
        node.size[1] = Math.max(node.size[1], MIN_NODE_HEIGHT);
        node.setSize?.(node.size);
    },
});
