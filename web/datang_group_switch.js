import { app } from "../../../scripts/app.js";
import {
    findInnermostDatangGroupForNode,
    groupHeaderSwitchRect,
    indexDatangGroupControllers,
    isDatangGroupPresenceMarker,
    isDatangGroupPresenceEnabled,
    layoutEmbeddedGroupForNodes,
    layoutParameterGroupForNodes,
    placeControllerBeforeMembers,
    pointInsideRect,
    readDatangGroupState,
    reconcileGroupModes,
    repairRequiredResourceSourceModes,
    rememberDatangGroupMemberOrder,
    removeControllerFromOrder,
    uniqueGroupTitle,
    writeDatangGroupState,
    writeDatangParameterGroupState,
} from "./datang_group_core.js";

const NODE_CLASS = "DatangGroupSwitch";
const WIDGET_NAME = "启用节点组";
const PRESENCE_WIDGET_NAME = "组已启用";
const TITLE_PREFIX = "#";
const GROUP_COLOR = "#b4872f";
const SYNC_INTERVAL_MS = 1500;
const GROUP_SWITCH_CHANGE_EVENT = "datang-group-switch-changed";
const GROUP_SWITCH_REQUEST_EVENT = "datang-group-switch-request";

function notifyGroupSwitchChanged(group, controller, enabled) {
    if (typeof window?.dispatchEvent !== "function" || typeof CustomEvent !== "function") return;
    window.dispatchEvent(new CustomEvent(GROUP_SWITCH_CHANGE_EVENT, {
        detail: {
            controllerId: controller?.id ?? null,
            groupTitle: String(group?.title || "").trim(),
            enabled: enabled === true,
        },
    }));
}

function graphGroups(graph) {
    const groups = graph?._groups || graph?.groups || [];
    return Array.isArray(groups) ? groups : [];
}

function graphNodes(graph) {
    const nodes = graph?._nodes || graph?.nodes || [];
    return Array.isArray(nodes) ? nodes : [];
}

function graphLinks(graph) {
    const links = graph?.links || graph?._links || [];
    return Array.isArray(links) ? links : Object.values(links || {});
}

function isController(node) {
    return node?.comfyClass === NODE_CLASS || node?.type === NODE_CLASS;
}

function isEmbeddedController(node) {
    return isController(node) && node?.properties?.datang_embedded_controller === true;
}

let activeControllerIndex = null;

function refreshControllerIndex(graph = app.graph) {
    if (!graph) return null;
    const groups = graphGroups(graph);
    for (const group of groups) group?.recomputeInsideNodes?.();
    const controllers = graphNodes(graph).filter(isController);
    activeControllerIndex = {
        graph,
        ...indexDatangGroupControllers(groups, controllers),
    };
    return activeControllerIndex;
}

function controllerIndex(graph = app.graph) {
    if (!activeControllerIndex || activeControllerIndex.graph !== graph) {
        return refreshControllerIndex(graph);
    }
    return activeControllerIndex;
}

function resolveBoundGroup(node, index = controllerIndex(node?.graph || app.graph)) {
    return index?.groupByController?.get(node) || null;
}

function groupController(group, graph = group?.graph || app.graph, index = controllerIndex(graph)) {
    return index?.controllerByGroup?.get(group) || null;
}

function groupMembers(group, controller, { recompute = true } = {}) {
    if (recompute) group?.recomputeInsideNodes?.();
    return (group?._nodes || []).filter((node) => (
        node !== controller && !isController(node) && !isDatangGroupPresenceMarker(node)
    ));
}

function hidePresenceWidget(widget) {
    if (!widget || widget.__datangPresenceHidden) return;
    widget.__datangPresenceHidden = true;
    widget.hidden = true;
    widget.type = "converted-widget";
    widget.computeSize = () => [0, -4];
    widget.computeLayoutSize = () => ({ minHeight: 0, maxHeight: 0, minWidth: 0 });
    widget.options ||= {};
    widget.options.getMinHeight = () => 0;
    widget.options.getMaxHeight = () => 0;
    if (widget.inputEl?.style) widget.inputEl.style.display = "none";
}

function syncPresenceMarker(node, groups = graphGroups(node?.graph || app.graph)) {
    if (!isDatangGroupPresenceMarker(node)) return false;
    const widget = node.widgets?.find((item) => item.name === PRESENCE_WIDGET_NAME);
    if (!widget) return false;
    hidePresenceWidget(widget);
    for (const group of groups) group?.recomputeInsideNodes?.();
    const group = findInnermostDatangGroupForNode(groups, node);
    const enabled = isDatangGroupPresenceEnabled(groups, node);
    let changed = false;
    if (widget.value !== enabled) {
        widget.value = enabled;
        changed = true;
    }
    if (node.mode !== 0) {
        node.mode = 0;
        changed = true;
    }
    node.properties ||= {};
    const groupTitle = String(group?.title || "").trim();
    if (node.properties.datang_group_presence_marker !== true) {
        node.properties.datang_group_presence_marker = true;
        changed = true;
    }
    if (node.properties.datang_group_title !== groupTitle) {
        node.properties.datang_group_title = groupTitle;
        changed = true;
    }
    const title = group ? `.大汤节点组状态标记 · ${groupTitle}` : ".大汤节点组状态标记 · 未绑定";
    if (node.title !== title) {
        node.title = title;
        changed = true;
    }
    if (changed) node.setDirtyCanvas?.(true, true);
    return changed;
}

function syncPresenceMarkersForGroup(group) {
    for (const node of group?._nodes || []) {
        if (isDatangGroupPresenceMarker(node)) syncPresenceMarker(node, graphGroups(node?.graph || app.graph));
    }
}

function sameModeMap(left, right) {
    const leftEntries = Object.entries(left || {});
    const rightEntries = Object.entries(right || {});
    return leftEntries.length === rightEntries.length
        && leftEntries.every(([id, mode]) => Number(right?.[id]) === Number(mode));
}

function writeGroupStateIfChanged(group, controllerId, enabled) {
    const previous = readDatangGroupState(group);
    if (String(previous?.controller_id ?? "") === String(controllerId ?? "")
        && previous?.enabled === (enabled === true)) return previous;
    return writeDatangGroupState(group, { controllerId, enabled });
}

function keepControllerInHeader(node, group) {
    const bounds = group?._bounding || group?.bounding;
    if (bounds && typeof bounds.length === "number" && bounds.length >= 2) {
        const nextX = Number(bounds[0]) + 8;
        const nextY = Number(bounds[1]) + 8;
        if (Number(node?.pos?.[0]) !== nextX || Number(node?.pos?.[1]) !== nextY) {
            node.pos = [nextX, nextY];
        }
    }
    if (Number(node?.size?.[0]) !== 1 || Number(node?.size?.[1]) !== 1) node.size = [1, 1];
}

function currentPsAiOrder(graph) {
    const nodes = graphNodes(graph);
    const stored = graph?.extra?.ps_ai || {};
    if (stored.sort_mode === "id") {
        return [...nodes].sort((a, b) => Number(a.id) - Number(b.id)).map((node) => node.id);
    }
    if (stored.sort_mode === "title") {
        return [...nodes]
            .sort((a, b) => String(a.title || a.type || "").localeCompare(String(b.title || b.type || ""), "zh-CN", { numeric: true }))
            .map((node) => node.id);
    }
    const available = new Map(nodes.map((node) => [String(node.id), node.id]));
    const order = [];
    for (const id of Array.isArray(stored.node_order) ? stored.node_order : []) {
        if (!available.has(String(id))) continue;
        order.push(available.get(String(id)));
        available.delete(String(id));
    }
    order.push(...available.values());
    return order;
}

function placeControllerInPsAiOrder(graph, controller, members) {
    graph.extra ||= {};
    graph.extra.ps_ai ||= {};
    graph.extra.ps_ai.sort_mode = "manual";
    graph.extra.ps_ai.node_order = placeControllerBeforeMembers(
        currentPsAiOrder(graph),
        controller.id,
        members.map((node) => node.id),
    );
}

function syncControllerIdentity(node, group, widget) {
    const title = String(group?.title || node?.properties?.datang_group_title || "大汤节点组").trim() || "大汤节点组";
    node.properties ||= {};
    if (node.properties.datang_group_title !== title) node.properties.datang_group_title = title;
    if (node.properties.datang_group_switch !== true) node.properties.datang_group_switch = true;
    if (node.title !== `${TITLE_PREFIX}${title}`) node.title = `${TITLE_PREFIX}${title}`;
    if (widget && widget.label !== `Enable ${title}`) widget.label = `Enable ${title}`;
}

function applyControllerState(node, widget, { transaction = false, index = null, recomputeMembers = true } = {}) {
    const graph = node?.graph || app.graph;
    const currentIndex = index || controllerIndex(graph);
    const group = resolveBoundGroup(node, currentIndex);
    if (!graph || !group || !widget) return false;
    const canonical = groupController(group, graph, currentIndex);
    if (canonical && canonical !== node) return false;
    syncControllerIdentity(node, group, widget);
    const members = groupMembers(group, node, { recompute: recomputeMembers });
    const memberOrder = rememberDatangGroupMemberOrder(group, members);
    if (transaction) graph.beforeChange?.();
    try {
        const previousState = readDatangGroupState(group);
        const enabled = widget.value === true;
        const repairedModes = repairRequiredResourceSourceModes({
            members,
            previousModes: node.properties?.datang_previous_modes,
            links: graphLinks(graph),
        });
        const result = reconcileGroupModes({
            allNodes: graphNodes(graph),
            members,
            enabled,
            previousModes: repairedModes.previousModes,
        });
        if (!sameModeMap(node.properties?.datang_previous_modes, result.previousModes)) {
            node.properties.datang_previous_modes = result.previousModes;
        }
        writeGroupStateIfChanged(group, node.id, enabled);
        syncPresenceMarkersForGroup(group);
        if (result.changed || memberOrder.changed) {
            node.setDirtyCanvas?.(true, true);
            graph.setDirtyCanvas?.(true, true);
        }
        if (previousState?.enabled !== enabled) notifyGroupSwitchChanged(group, node, enabled);
        return result.changed;
    } finally {
        if (transaction) graph.afterChange?.();
    }
}

function hasConnections(node) {
    return [...(node?.inputs || []), ...(node?.outputs || [])]
        .some((slot) => slot?.link !== null && slot?.link !== undefined || Array.isArray(slot?.links) && slot.links.length > 0);
}

function embedController(node, group, widget) {
    if (!group || hasConnections(node) && !isEmbeddedController(node)) return false;
    node.properties ||= {};
    if (!Array.isArray(node.properties.datang_legacy_size)) {
        node.properties.datang_legacy_size = [...(node.size || [260, 82])];
    }
    if (node.properties.datang_embedded_controller !== true) node.properties.datang_embedded_controller = true;
    if (node.properties.datang_delete_with_group !== true) node.properties.datang_delete_with_group = true;
    node.__datangResolvedGroup = true;
    if (Object.hasOwn(node.properties, "datang_duplicate_controller")) delete node.properties.datang_duplicate_controller;
    syncControllerIdentity(node, group, widget);
    keepControllerInHeader(node, group);
    writeGroupStateIfChanged(group, node.id, widget?.value === true);
    return true;
}

function suppressDuplicateController(node, group) {
    node.properties ||= {};
    if (node.properties.datang_embedded_controller !== true) node.properties.datang_embedded_controller = true;
    if (node.properties.datang_delete_with_group !== true) node.properties.datang_delete_with_group = true;
    node.__datangResolvedGroup = true;
    if (node.properties.datang_duplicate_controller !== true) node.properties.datang_duplicate_controller = true;
    const title = String(group?.title || node.properties.datang_group_title || "").trim();
    if (node.properties.datang_group_title !== title) node.properties.datang_group_title = title;
    keepControllerInHeader(node, group);
    return true;
}

function restoreVisibleController(node) {
    if (!isEmbeddedController(node)) return false;
    const size = node?.properties?.datang_legacy_size;
    node.properties.datang_embedded_controller = false;
    delete node.properties.datang_duplicate_controller;
    node.size = Array.isArray(size) ? [...size] : [260, 82];
    node.setSize?.(node.size);
    return true;
}

function removeGroupOwnedController(node) {
    const graph = node?.graph || app.graph;
    if (!graph || typeof graph.remove !== "function") return false;
    graph.beforeChange?.();
    try {
        const allNodes = graphNodes(graph);
        const rememberedIds = new Set(Object.keys(node.properties?.datang_previous_modes || {}));
        const rememberedMembers = allNodes.filter((member) => rememberedIds.has(String(member?.id)));
        const repairedModes = repairRequiredResourceSourceModes({
            members: rememberedMembers,
            previousModes: node.properties?.datang_previous_modes,
            links: graphLinks(graph),
        });
        const result = reconcileGroupModes({
            allNodes,
            members: [],
            enabled: true,
            previousModes: repairedModes.previousModes,
        });
        node.properties.datang_previous_modes = result.previousModes;
        const psAi = graph?.extra?.ps_ai;
        if (psAi && Array.isArray(psAi.node_order)) {
            psAi.node_order = removeControllerFromOrder(psAi.node_order, node.id);
        }
        graph.remove(node);
        graph.change?.();
        graph.setDirtyCanvas?.(true, true);
        app.canvas?.setDirty?.(true, true);
        app.extensionManager?.workflow?.activeWorkflow?.changeTracker?.checkState?.();
        return true;
    } finally {
        graph.afterChange?.();
    }
}

function synchronizeController(node, index = controllerIndex(node?.graph || app.graph)) {
    if (!isController(node)) return false;
    const widget = node.widgets?.find((item) => item.name === WIDGET_NAME);
    if (!widget) return false;
    const group = resolveBoundGroup(node, index);
    if (!group) {
        if (node.__datangResolvedGroup === true && node?.properties?.datang_delete_with_group === true) {
            return removeGroupOwnedController(node);
        }
        restoreVisibleController(node);
        return false;
    }
    const canonical = groupController(group, node?.graph || app.graph, index);
    if (canonical && canonical !== node) return suppressDuplicateController(node, group);
    embedController(node, group, widget);
    applyControllerState(node, widget, { index, recomputeMembers: false });
    return true;
}

function bindController(node) {
    if (node.__datangGroupBound) return;
    const widget = node.widgets?.find((item) => item.name === WIDGET_NAME);
    if (!widget) return;
    node.__datangGroupBound = true;
    node.properties ||= {};
    const originalCallback = widget.callback;
    widget.callback = function (value) {
        originalCallback?.apply(this, arguments);
        widget.value = value === true;
        applyControllerState(node, widget, { transaction: true });
    };
    const originalForeground = node.onDrawForeground;
    node.onDrawForeground = function () {
        originalForeground?.apply(this, arguments);
        if (!isEmbeddedController(node)) synchronizeController(node);
    };
    if (!isEmbeddedController(node)) {
        node.size[0] = Math.max(Number(node.size?.[0]) || 0, 260);
        node.setSize?.(node.size);
    }
    for (const delay of [0, 120, 600]) {
        setTimeout(() => synchronizeController(node, refreshControllerIndex(node?.graph || app.graph)), delay);
    }
}

function drawHeaderSwitch(ctx, group, enabled) {
    const rect = groupHeaderSwitchRect(group);
    if (!rect) return;
    const [x, y, width, height] = rect;
    ctx.save();
    ctx.globalAlpha = 1;
    ctx.lineWidth = 1.25;
    ctx.fillStyle = enabled ? "#171712" : "#2c2922";
    ctx.strokeStyle = enabled ? "#f2bd35" : "#8b7440";
    ctx.beginPath();
    ctx.roundRect(x, y, width, height, height / 2);
    ctx.fill();
    ctx.stroke();

    const knobRadius = 7;
    const knobX = enabled ? x + width - 12 : x + 12;
    ctx.fillStyle = enabled ? "#ffc83d" : "#8a8a82";
    ctx.beginPath();
    ctx.arc(knobX, y + height / 2, knobRadius, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = enabled ? "#ffe6a3" : "#d0c7b3";
    ctx.font = "600 12px system-ui, sans-serif";
    ctx.textAlign = enabled ? "left" : "right";
    ctx.textBaseline = "middle";
    ctx.fillText(enabled ? "开启" : "忽略", enabled ? x + 10 : x + width - 10, y + height / 2 + 0.5);
    ctx.restore();
}

function installCanvasDrawing() {
    if (LGraphCanvas.prototype.__datangEmbeddedDrawingInstalled) return;
    LGraphCanvas.prototype.__datangEmbeddedDrawingInstalled = true;
    const originalDrawGroups = LGraphCanvas.prototype.drawGroups;
    LGraphCanvas.prototype.drawGroups = function () {
        originalDrawGroups.apply(this, arguments);
        const ctx = arguments[1];
        if (!ctx) return;
        const index = controllerIndex(this.graph);
        for (const group of graphGroups(this.graph)) {
            const state = readDatangGroupState(group);
            if (!state) continue;
            const controller = groupController(group, this.graph, index);
            const widget = controller?.widgets?.find((item) => item.name === WIDGET_NAME);
            drawHeaderSwitch(ctx, group, widget ? widget.value === true : state.enabled);
        }
    };

    const originalDrawNode = LGraphCanvas.prototype.drawNode;
    LGraphCanvas.prototype.drawNode = function (node) {
        if (isEmbeddedController(node)) return;
        return originalDrawNode.apply(this, arguments);
    };
}

function toggleGroup(group, graph) {
    const index = refreshControllerIndex(graph);
    const controller = groupController(group, graph, index);
    const widget = controller?.widgets?.find((item) => item.name === WIDGET_NAME);
    if (!controller || !widget) return false;
    const next = widget.value !== true;
    if (typeof widget.callback === "function") widget.callback(next);
    else {
        widget.value = next;
        applyControllerState(controller, widget, { transaction: true });
    }
    writeGroupStateIfChanged(group, controller.id, next);
    graph.change?.();
    graph.setDirtyCanvas?.(true, true);
    app.canvas?.setDirty?.(true, true);
    app.extensionManager?.workflow?.activeWorkflow?.changeTracker?.checkState?.();
    return true;
}

function installCanvasMouseHook(canvas) {
    if (!canvas || canvas.onMouse?.__datangEmbeddedGroupHook) return;
    const originalOnMouse = canvas.onMouse;
    const hooked = function (event) {
        if (event?.type === "pointerdown" && event.button === 0) {
            const group = [...graphGroups(this.graph)].reverse().find((candidate) => (
                readDatangGroupState(candidate)
                && pointInsideRect(event.canvasX, event.canvasY, groupHeaderSwitchRect(candidate))
            ));
            if (group && toggleGroup(group, this.graph)) return true;
        }
        return originalOnMouse?.apply(this, arguments);
    };
    hooked.__datangEmbeddedGroupHook = true;
    canvas.onMouse = hooked;
}

function syncAllControllers() {
    const graph = app.graph;
    if (!graph) return;
    installCanvasMouseHook(app.canvas);
    const index = refreshControllerIndex(graph);
    for (const node of index?.controllers || []) {
        bindController(node);
        synchronizeController(node, index);
    }
    for (const node of graphNodes(graph)) {
        if (isDatangGroupPresenceMarker(node)) syncPresenceMarker(node, graphGroups(graph));
    }
}

function applyRequestedGroupState(event) {
    const graph = app.graph;
    const controllerId = event?.detail?.controllerId;
    if (!graph || controllerId === null || controllerId === undefined) return false;
    const index = refreshControllerIndex(graph);
    const controller = index?.controllers?.find((node) => String(node.id) === String(controllerId));
    const widget = controller?.widgets?.find((item) => item.name === WIDGET_NAME);
    const group = controller ? resolveBoundGroup(controller, index) : null;
    if (!controller || !widget || !group || groupController(group, graph, index) !== controller) return false;
    widget.value = event.detail.enabled === true;
    applyControllerState(controller, widget, { index });
    graph.change?.();
    graph.setDirtyCanvas?.(true, true);
    app.canvas?.setDirty?.(true, true);
    app.extensionManager?.workflow?.activeWorkflow?.changeTracker?.checkState?.();
    return true;
}

function installGroupRequestListener() {
    if (globalThis.__datangGroupRequestListenerInstalled) return;
    globalThis.__datangGroupRequestListenerInstalled = true;
    window.addEventListener(GROUP_SWITCH_REQUEST_EVENT, applyRequestedGroupState);
}

export function createDatangGroup(canvas, selectedNodes) {
    const graph = canvas?.graph || app.graph;
    const nodes = (selectedNodes || []).filter((node) => !isController(node));
    if (!graph || nodes.length === 0) throw new Error("请先选中至少一个要打包的节点。");
    const controller = LiteGraph.createNode(NODE_CLASS);
    if (!controller) throw new Error("大汤节点组开关尚未注册，请先重启 ComfyUI。");
    const title = uniqueGroupTitle(graphGroups(graph));
    const layout = layoutEmbeddedGroupForNodes(nodes);
    controller.properties ||= {};
    controller.properties.datang_group_title = title;
    controller.properties.datang_group_switch = true;
    controller.properties.datang_embedded_controller = true;
    controller.properties.datang_delete_with_group = true;
    controller.properties.datang_legacy_size = [260, 82];
    controller.__datangResolvedGroup = true;
    controller.pos = [...layout.controlPos];
    controller.size = [1, 1];
    const group = new LiteGraph.LGraphGroup();
    group.configure({
        title,
        bounding: layout.bounding,
        color: GROUP_COLOR,
        font_size: 24,
        locked: false,
        flags: {},
    });
    graph.beforeChange?.();
    try {
        graph.add(group);
        graph.add(controller);
        group.recomputeInsideNodes?.();
        const groupBounds = group?._bounding || group?.bounding;
        if (groupBounds && typeof groupBounds.length === "number" && groupBounds.length >= 4) {
            for (let index = 0; index < 4; index += 1) groupBounds[index] = layout.bounding[index];
        }
        controller.pos = [...layout.controlPos];
        writeDatangGroupState(group, { controllerId: controller.id, enabled: true });
        refreshControllerIndex(graph);
        placeControllerInPsAiOrder(graph, controller, nodes);
        bindController(controller);
        const widget = controller.widgets?.find((item) => item.name === WIDGET_NAME);
        if (widget) widget.value = true;
        syncControllerIdentity(controller, group, widget);
        applyControllerState(controller, widget);
        if (typeof canvas.selectItems === "function") canvas.selectItems([group]);
        else {
            canvas.selected_group = group;
            group.selected = true;
        }
        graph.setDirtyCanvas?.(true, true);
        return { controller, group };
    } finally {
        graph.afterChange?.();
    }
}

export function createDatangParameterGroup(canvas, selectedNodes) {
    const graph = canvas?.graph || app.graph;
    const nodes = (selectedNodes || []).filter((node) => !isController(node));
    if (!graph || nodes.length < 2) throw new Error("请至少选中两个要组合显示的节点。");
    const title = uniqueGroupTitle(graphGroups(graph), "大汤参数组");
    const layout = layoutParameterGroupForNodes(nodes);
    const group = new LiteGraph.LGraphGroup();
    group.configure({
        title,
        bounding: layout.bounding,
        color: GROUP_COLOR,
        font_size: 24,
        locked: false,
        flags: {},
    });
    graph.beforeChange?.();
    try {
        graph.add(group);
        group.recomputeInsideNodes?.();
        const groupBounds = group?._bounding || group?.bounding;
        if (groupBounds && typeof groupBounds.length === "number" && groupBounds.length >= 4) {
            for (let index = 0; index < 4; index += 1) groupBounds[index] = layout.bounding[index];
        }
        writeDatangParameterGroupState(group);
        if (typeof canvas.selectItems === "function") canvas.selectItems([group]);
        else {
            canvas.selected_group = group;
            group.selected = true;
        }
        graph.change?.();
        graph.setDirtyCanvas?.(true, true);
        app.canvas?.setDirty?.(true, true);
        app.extensionManager?.workflow?.activeWorkflow?.changeTracker?.checkState?.();
        return { group };
    } finally {
        graph.afterChange?.();
    }
}

function installCanvasMenu() {
    if (LGraphCanvas.prototype.__datangGroupMenuInstalled) return;
    LGraphCanvas.prototype.__datangGroupMenuInstalled = true;
    const original = LGraphCanvas.prototype.getCanvasMenuOptions;
    LGraphCanvas.prototype.getCanvasMenuOptions = function () {
        const options = original.apply(this, arguments);
        const selectedNodes = Object.values(this.selected_nodes || {}).filter((node) => !isController(node));
        options.push(null, {
            content: selectedNodes.length
                ? `大汤：将选中的 ${selectedNodes.length} 个节点设为可开关组`
                : "大汤：将选中节点设为可开关组",
            disabled: selectedNodes.length === 0,
            callback: () => createDatangGroup(this, selectedNodes),
        }, {
            content: selectedNodes.length
                ? `大汤：将选中的 ${selectedNodes.length} 个节点设为无开关参数组`
                : "大汤：将选中节点设为无开关参数组",
            disabled: selectedNodes.length < 2,
            callback: () => createDatangParameterGroup(this, selectedNodes),
        });
        return options;
    };
}

app.registerExtension({
    name: "Datang.GroupSwitch",
    setup() {
        installCanvasMenu();
        installCanvasDrawing();
        installCanvasMouseHook(app.canvas);
        installGroupRequestListener();
        if (!globalThis.__datangGroupSyncTimer) {
            globalThis.__datangGroupSyncTimer = setInterval(syncAllControllers, SYNC_INTERVAL_MS);
        }
    },
    nodeCreated(node) {
        if (isController(node)) {
            bindController(node);
            return;
        }
        if (isDatangGroupPresenceMarker(node)) {
            node.properties ||= {};
            node.properties.datang_group_presence_marker = true;
            for (const delay of [0, 120, 600]) {
                setTimeout(() => syncPresenceMarker(node), delay);
            }
        }
    },
});
