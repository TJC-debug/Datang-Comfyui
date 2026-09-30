import { app } from "../../../scripts/app.js";

const NODE_CLASS = "DatangModelSelector";
const DATA_WIDGET_NAME = "模型数据";
const MIN_SLOTS = 2;
const MIN_NODE_HEIGHT = 228;
const NODE_CHROME_HEIGHT = 86;
const ROW_BLOCK_HEIGHT = 50;
const ADD_BUTTON_BLOCK_HEIGHT = 42;
const DEFAULT_ITEMS = [
    { name: "模型 1", value: "", enabled: true, _selection_mode: "单选" },
    { name: "模型 2", value: "", enabled: false },
];

function parseItems(value) {
    let parsed = value;
    if (typeof parsed === "string") {
        try {
            parsed = JSON.parse(parsed);
        } catch {
            return null;
        }
    }
    if (!Array.isArray(parsed)) return null;
    const items = parsed.filter((item) => item && typeof item === "object").map((item, index) => ({
        name: String(item.name || `模型 ${index + 1}`).trim() || `模型 ${index + 1}`,
        value: item.value ?? "",
        enabled: item.enabled === true,
    }));
    while (items.length < MIN_SLOTS) {
        items.push({ name: `模型 ${items.length + 1}`, value: "", enabled: false });
    }
    let selected = items.findIndex((item) => item.enabled);
    if (selected < 0) selected = 0;
    for (let index = 0; index < items.length; index += 1) items[index].enabled = index === selected;
    return items;
}

function normaliseItems(value) {
    return parseItems(value) || DEFAULT_ITEMS.map((item) => ({ ...item }));
}

function serialiseItems(items) {
    return JSON.stringify(items.map((item, index) => ({
        name: item.name,
        value: item.value,
        enabled: item.enabled === true,
        ...(index === 0 ? { _selection_mode: "单选" } : {}),
    })));
}

function nextItemName(items) {
    let highest = items.length;
    for (const item of items) {
        const match = /^模型\s+(\d+)$/.exec(String(item.name || "").trim());
        if (match) highest = Math.max(highest, Number(match[1]));
    }
    return `模型 ${highest + 1}`;
}

function replaceWithHiddenProxy(node, originalWidget) {
    const widgetIndex = node.widgets?.indexOf(originalWidget) ?? -1;
    if (widgetIndex < 0) return null;
    let storedValue = originalWidget.value;
    const proxyWidget = {
        ...originalWidget,
        type: "converted-widget",
        hidden: true,
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
    originalWidget.hidden = true;
    originalWidget.type = "converted-widget";
    return proxyWidget;
}

function hideNativeWidget(widget) {
    if (!widget) return;
    widget.hidden = true;
    widget.type = "converted-widget";
    if (widget.inputEl?.style) widget.inputEl.style.display = "none";
}

function graphLink(graph, linkId) {
    const links = graph?.links || graph?._links;
    return links?.get?.(linkId) || links?.[linkId] || null;
}

function comboValues(widget, input) {
    const candidates = [
        widget?.options?.values,
        input?.widget?.config?.[0],
        input?.widget?.[0],
    ];
    for (const candidate of candidates) {
        try {
            const resolved = typeof candidate === "function" ? candidate(widget) : candidate;
            if (!Array.isArray(resolved)) continue;
            return [...new Set(resolved
                .filter((value) => ["string", "number"].includes(typeof value))
                .map((value) => String(value)))];
        } catch (error) {
            console.warn("[大汤模型选择器] 无法读取目标下拉选项。", error);
        }
    }
    return [];
}

function targetModelOptions(node) {
    const graph = node?.graph || app.graph;
    const linkIds = node?.outputs?.[0]?.links || [];
    if (!graph || !Array.isArray(linkIds) || linkIds.length === 0) {
        return {
            values: [],
            message: "请先连接目标模型参数（目标下拉需先转换为输入）",
            connected: false,
        };
    }
    const targets = [];
    for (const linkId of linkIds) {
        const link = graphLink(graph, linkId);
        const target = graph.getNodeById?.(link?.target_id);
        const input = target?.inputs?.[Number(link?.target_slot)];
        const widgetName = String(input?.widget?.name || input?.name || "").trim();
        const widget = target?.widgets?.find((item) => String(item?.name || "") === widgetName)
            || target?.widgets?.find((item) => String(item?.name || "") === String(input?.name || ""));
        const values = comboValues(widget, input);
        targets.push({ target, input, widget, values });
    }
    const valid = targets.filter((item) => item.values.length > 0);
    if (valid.length === 0) {
        return { values: [], message: "已连接，但目标不是可读取的模型下拉参数", connected: true };
    }
    let values = [...valid[0].values];
    for (const item of valid.slice(1)) {
        const allowed = new Set(item.values);
        values = values.filter((value) => allowed.has(value));
    }
    if (values.length === 0) {
        return { values: [], message: "多个目标的模型选项不一致，请一个选择器只连接一个参数", connected: true };
    }
    const target = valid[0];
    const targetName = String(target.target?.title || target.target?.type || "目标节点");
    const inputName = String(target.input?.label || target.input?.name || target.widget?.name || "模型");
    return {
        values,
        message: `已连接：${targetName} / ${inputName}（${values.length} 项）`,
        connected: true,
    };
}

function installStyles() {
    if (document.getElementById("datang-model-selector-styles")) return;
    const style = document.createElement("style");
    style.id = "datang-model-selector-styles";
    style.textContent = `
        .datang-model-selector { box-sizing: border-box; display: flex; flex-direction: column; gap: 7px; width: 100%; height: 100%; padding: 7px; color: #e7e2d7; font: 12px/1.35 system-ui, -apple-system, "Segoe UI", sans-serif; }
        .datang-model-selector__status { min-height: 18px; color: #bcb7ab; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .datang-model-selector__status.is-ready { color: #74d59a; }
        .datang-model-selector__list { display: flex; flex: 1 1 auto; flex-direction: column; gap: 6px; min-height: 0; }
        .datang-model-selector__row { display: grid; grid-template-columns: 42px 104px minmax(0, 1fr) 32px; gap: 6px; align-items: center; min-height: 42px; }
        .datang-model-selector__switch { position: relative; display: block; width: 38px; height: 22px; }
        .datang-model-selector__switch input { position: absolute; width: 1px; height: 1px; opacity: 0; }
        .datang-model-selector__track { position: absolute; inset: 0; box-sizing: border-box; border: 1px solid #706445; border-radius: 12px; background: #282821; }
        .datang-model-selector__track::after { position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%; background: #898982; content: ""; transition: transform .12s ease, background .12s ease; }
        .datang-model-selector__switch input:checked + .datang-model-selector__track { border-color: #d4a62a; background: #39321d; }
        .datang-model-selector__switch input:checked + .datang-model-selector__track::after { background: #ffc83d; transform: translateX(16px); }
        .datang-model-selector__name, .datang-model-selector__select, .datang-model-selector__delete, .datang-model-selector__add { box-sizing: border-box; min-height: 32px; border: 1px solid #575446; border-radius: 4px; color: #eee9dc; background: #1d1e1a; font: inherit; }
        .datang-model-selector__name, .datang-model-selector__select { width: 100%; min-width: 0; padding: 0 7px; }
        .datang-model-selector__delete { width: 32px; padding: 0; color: #ef8a83; }
        .datang-model-selector__delete:disabled { color: #66655f; border-color: #41413a; }
        .datang-model-selector__add { width: 100%; color: #f2cf65; border-color: #796224; }
        .datang-model-selector__add:hover, .datang-model-selector__delete:not(:disabled):hover { border-color: #e5b62e; background: #302918; }
    `;
    document.head.appendChild(style);
}

function createSelectorUi(node, dataWidget) {
    const root = document.createElement("div");
    root.className = "datang-model-selector";
    const status = document.createElement("div");
    status.className = "datang-model-selector__status";
    const list = document.createElement("div");
    list.className = "datang-model-selector__list";
    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.className = "datang-model-selector__add";
    addButton.textContent = "+ 增加模型槽位";
    root.append(status, list, addButton);

    let items = normaliseItems(dataWidget.value);
    let optionsState = targetModelOptions(node);
    let resizeScheduled = false;

    const desiredNodeHeight = () => Math.max(
        MIN_NODE_HEIGHT,
        NODE_CHROME_HEIGHT + items.length * ROW_BLOCK_HEIGHT + ADD_BUTTON_BLOCK_HEIGHT,
    );

    const syncNodeHeight = () => {
        if (resizeScheduled) return;
        resizeScheduled = true;
        requestAnimationFrame(() => {
            resizeScheduled = false;
            node.setSize?.([Math.max(Number(node.size?.[0]) || 0, 430), desiredNodeHeight()]);
            node.setDirtyCanvas?.(true, true);
            app.graph?.setDirtyCanvas?.(true, true);
        });
    };

    const save = () => {
        const graph = node?.graph || app.graph;
        const value = serialiseItems(items);
        graph?.beforeChange?.();
        try {
            dataWidget.value = value;
            graph?.change?.();
            graph?.setDirtyCanvas?.(true, true);
            app.canvas?.setDirty?.(true, true);
            app.extensionManager?.workflow?.activeWorkflow?.changeTracker?.checkState?.();
        } finally {
            graph?.afterChange?.();
        }
    };

    const fillEmptyValues = () => {
        if (optionsState.values.length === 0) return false;
        let changed = false;
        for (let index = 0; index < items.length; index += 1) {
            if (String(items[index].value ?? "").length > 0) continue;
            items[index].value = optionsState.values[Math.min(index, optionsState.values.length - 1)];
            changed = true;
        }
        return changed;
    };

    const render = () => {
        status.textContent = optionsState.message;
        status.classList.toggle("is-ready", optionsState.connected && optionsState.values.length > 0);
        list.replaceChildren();
        items.forEach((item, index) => {
            const row = document.createElement("div");
            row.className = "datang-model-selector__row";

            const switchLabel = document.createElement("label");
            switchLabel.className = "datang-model-selector__switch";
            switchLabel.title = item.enabled ? "当前启用模型" : "切换到此模型";
            const toggle = document.createElement("input");
            toggle.type = "checkbox";
            toggle.checked = item.enabled;
            toggle.setAttribute("aria-label", `启用${item.name}`);
            const track = document.createElement("span");
            track.className = "datang-model-selector__track";
            switchLabel.append(toggle, track);
            toggle.addEventListener("change", () => {
                if (!toggle.checked) {
                    toggle.checked = true;
                    return;
                }
                for (const candidate of items) candidate.enabled = candidate === item;
                save();
                render();
            });

            const nameInput = document.createElement("input");
            nameInput.className = "datang-model-selector__name";
            nameInput.type = "text";
            nameInput.value = item.name;
            nameInput.placeholder = `模型 ${index + 1}`;
            nameInput.title = "发布到 PS_AI/Photoshop 的默认槽位名称";
            nameInput.addEventListener("change", () => {
                item.name = nameInput.value.trim() || `模型 ${index + 1}`;
                nameInput.value = item.name;
                save();
            });

            const select = document.createElement("select");
            select.className = "datang-model-selector__select";
            select.title = "目标参数的真实模型值";
            const current = String(item.value ?? "");
            const values = [...optionsState.values];
            if (current && !values.includes(current)) values.unshift(current);
            if (values.length === 0) {
                const option = document.createElement("option");
                option.value = current;
                option.textContent = current || "请先连接目标模型参数";
                select.appendChild(option);
                select.disabled = true;
            } else {
                for (const value of values) {
                    const option = document.createElement("option");
                    option.value = value;
                    option.textContent = value === current && !optionsState.values.includes(value)
                        ? `${value}（目标中已不可用）`
                        : value;
                    select.appendChild(option);
                }
                select.value = current || values[0];
                if (!current) item.value = select.value;
            }
            select.addEventListener("change", () => {
                item.value = select.value;
                save();
            });

            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "datang-model-selector__delete";
            remove.textContent = "×";
            remove.title = items.length <= MIN_SLOTS ? "至少保留两个槽位" : "删除槽位";
            remove.disabled = items.length <= MIN_SLOTS;
            remove.addEventListener("click", () => {
                if (items.length <= MIN_SLOTS) return;
                const removedWasEnabled = item.enabled;
                items.splice(index, 1);
                if (removedWasEnabled) items[0].enabled = true;
                save();
                render();
                syncNodeHeight();
            });

            row.append(switchLabel, nameInput, select, remove);
            list.appendChild(row);
        });
        syncNodeHeight();
    };

    addButton.addEventListener("click", () => {
        const used = new Set(items.map((item) => String(item.value ?? "")));
        const value = optionsState.values.find((candidate) => !used.has(candidate))
            || optionsState.values[0]
            || "";
        items.push({ name: nextItemName(items), value, enabled: false });
        save();
        render();
        syncNodeHeight();
    });

    const domWidget = node.addDOMWidget("模型槽位", "datang-model-selector", root, {
        getValue: () => "",
        setValue: () => {},
        getMinHeight: () => Math.max(120, 50 + items.length * ROW_BLOCK_HEIGHT + ADD_BUTTON_BLOCK_HEIGHT),
        getMaxHeight: () => Number.MAX_SAFE_INTEGER,
        hideOnZoom: false,
    });
    domWidget.serialize = false;
    domWidget.serializeValue = () => undefined;
    domWidget.inputEl = root;
    domWidget.options.minNodeSize = [410, 220];

    const refreshOptions = () => {
        optionsState = targetModelOptions(node);
        const changed = fillEmptyValues();
        if (changed) save();
        render();
    };
    refreshOptions();
    return {
        refreshOptions,
        setValue(value) {
            items = normaliseItems(value);
            refreshOptions();
        },
    };
}

app.registerExtension({
    name: "Datang.ModelSelector",
    async nodeCreated(node) {
        if (node.comfyClass !== NODE_CLASS) return;
        installStyles();
        const originalDataWidget = node.widgets?.find((widget) => widget.name === DATA_WIDGET_NAME);
        if (!originalDataWidget) return;
        const dataWidget = replaceWithHiddenProxy(node, originalDataWidget);
        if (!dataWidget) return;
        const originalIsWidgetVisible = node.isWidgetVisible?.bind(node);
        node.isWidgetVisible = (widget) => (
            widget === dataWidget ? false : originalIsWidgetVisible ? originalIsWidgetVisible(widget) : !widget.hidden
        );
        hideNativeWidget(dataWidget);
        const selector = createSelectorUi(node, dataWidget);
        let syncScheduled = false;
        const scheduleSync = () => {
            if (syncScheduled) return;
            syncScheduled = true;
            requestAnimationFrame(() => {
                syncScheduled = false;
                hideNativeWidget(dataWidget);
                selector.setValue(dataWidget.value);
                node.setDirtyCanvas?.(true, true);
            });
        };
        const originalCallback = dataWidget.callback;
        dataWidget.callback = function () {
            originalCallback?.apply(this, arguments);
            scheduleSync();
        };
        const originalConnectionsChange = node.onConnectionsChange;
        node.onConnectionsChange = function () {
            originalConnectionsChange?.apply(this, arguments);
            setTimeout(() => selector.refreshOptions(), 0);
        };
        scheduleSync();
        for (const delay of [0, 120, 600]) setTimeout(() => selector.refreshOptions(), delay);
    },
});
