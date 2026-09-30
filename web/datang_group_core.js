export const NODE_MODE = Object.freeze({
    ALWAYS: 0,
    NEVER: 2,
    BYPASS: 4,
});

export const DATANG_GROUP_FLAG = "datang_group_switch";
export const DATANG_PARAMETER_GROUP_FLAG = "datang_parameter_group";
export const DATANG_GROUP_PRESENCE_NODE_CLASS = "DatangGroupPresenceMarker";

export function isDatangGroupPresenceMarker(node) {
    return node?.comfyClass === DATANG_GROUP_PRESENCE_NODE_CLASS
        || node?.type === DATANG_GROUP_PRESENCE_NODE_CLASS;
}

function finite(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
}

export function nodeBounds(node) {
    const x = finite(node?.pos?.[0]);
    const y = finite(node?.pos?.[1]);
    const width = Math.max(1, finite(node?.size?.[0], 180));
    const height = Math.max(1, finite(node?.size?.[1], 80));
    return [x, y, x + width, y + height];
}

export function layoutGroupForNodes(nodes, controlSize = [260, 82], options = {}) {
    if (!Array.isArray(nodes) || nodes.length === 0) {
        throw new Error("请先选中至少一个要打包的节点。");
    }
    const padding = finite(options.padding, 28);
    const titleSpace = finite(options.titleSpace, 42);
    const controlGap = finite(options.controlGap, 22);
    const bounds = nodes.map(nodeBounds);
    const minX = Math.min(...bounds.map((item) => item[0]));
    const minY = Math.min(...bounds.map((item) => item[1]));
    const maxX = Math.max(...bounds.map((item) => item[2]));
    const maxY = Math.max(...bounds.map((item) => item[3]));
    const controlWidth = Math.max(180, finite(controlSize?.[0], 260));
    const controlHeight = Math.max(60, finite(controlSize?.[1], 82));
    const controlPos = [minX, minY - controlHeight - controlGap];
    const left = Math.min(minX, controlPos[0]) - padding;
    const top = controlPos[1] - titleSpace;
    const right = Math.max(maxX, controlPos[0] + controlWidth) + padding;
    const bottom = maxY + padding;
    return {
        controlPos,
        bounding: [left, top, right - left, bottom - top],
    };
}

export function layoutEmbeddedGroupForNodes(nodes, options = {}) {
    if (!Array.isArray(nodes) || nodes.length === 0) {
        throw new Error("请先选中至少一个要打包的节点。");
    }
    const padding = finite(options.padding, 28);
    const titleSpace = finite(options.titleSpace, 64);
    const bounds = nodes.map(nodeBounds);
    const minX = Math.min(...bounds.map((item) => item[0]));
    const minY = Math.min(...bounds.map((item) => item[1]));
    const maxX = Math.max(...bounds.map((item) => item[2]));
    const maxY = Math.max(...bounds.map((item) => item[3]));
    const left = minX - padding;
    const top = minY - titleSpace;
    return {
        controlPos: [left + 8, top + 8],
        bounding: [left, top, maxX - minX + padding * 2, maxY - minY + padding + titleSpace],
    };
}

export function layoutParameterGroupForNodes(nodes, options = {}) {
    if (!Array.isArray(nodes) || nodes.length < 2) {
        throw new Error("请至少选中两个要组合显示的节点。");
    }
    const padding = finite(options.padding, 28);
    const titleSpace = finite(options.titleSpace, 42);
    const bounds = nodes.map(nodeBounds);
    const minX = Math.min(...bounds.map((item) => item[0]));
    const minY = Math.min(...bounds.map((item) => item[1]));
    const maxX = Math.max(...bounds.map((item) => item[2]));
    const maxY = Math.max(...bounds.map((item) => item[3]));
    const left = minX - padding;
    const top = minY - titleSpace;
    return {
        bounding: [left, top, maxX - minX + padding * 2, maxY - minY + padding + titleSpace],
    };
}

export function readDatangParameterGroupState(group) {
    const stored = group?.flags?.[DATANG_PARAMETER_GROUP_FLAG];
    if (!stored) return null;
    if (stored === true) return { version: 1 };
    if (typeof stored !== "object" || Array.isArray(stored)) return null;
    return { version: 1 };
}

export function writeDatangParameterGroupState(group) {
    if (!group) return null;
    group.flags ||= {};
    group.flags[DATANG_PARAMETER_GROUP_FLAG] = { version: 1 };
    return readDatangParameterGroupState(group);
}

export function readDatangGroupState(group) {
    const stored = group?.flags?.[DATANG_GROUP_FLAG];
    if (!stored) return null;
    if (stored === true) return { version: 2, controller_id: null, enabled: true };
    if (typeof stored !== "object" || Array.isArray(stored)) return null;
    return {
        version: 2,
        controller_id: stored.controller_id ?? null,
        enabled: stored.enabled !== false,
    };
}

export function writeDatangGroupState(group, { controllerId = null, enabled = true } = {}) {
    if (!group) return null;
    group.flags ||= {};
    const memberOrder = Array.isArray(group.flags?.[DATANG_GROUP_FLAG]?.member_order)
        ? [...group.flags[DATANG_GROUP_FLAG].member_order]
        : [];
    group.flags[DATANG_GROUP_FLAG] = {
        version: 2,
        controller_id: controllerId,
        enabled: enabled !== false,
        ...(memberOrder.length > 0 ? { member_order: memberOrder } : {}),
    };
    return readDatangGroupState(group);
}

export function rememberDatangGroupMemberOrder(group, members = []) {
    if (!group) return { memberOrder: [], changed: false };
    group.flags ||= {};
    const stored = group.flags[DATANG_GROUP_FLAG];
    if (!stored || typeof stored !== "object" || Array.isArray(stored)) {
        return { memberOrder: [], changed: false };
    }
    const memberOrder = [];
    const seen = new Set();
    for (const value of Array.isArray(stored.member_order) ? stored.member_order : []) {
        const key = String(value ?? "");
        if (!key || seen.has(key)) continue;
        seen.add(key);
        memberOrder.push(value);
    }
    for (const node of members || []) {
        const value = node?.id;
        const key = String(value ?? "");
        if (!key || seen.has(key)) continue;
        seen.add(key);
        memberOrder.push(value);
    }
    const previous = Array.isArray(stored.member_order) ? stored.member_order : [];
    const changed = previous.length !== memberOrder.length
        || previous.some((value, index) => String(value) !== String(memberOrder[index]));
    if (changed) stored.member_order = memberOrder;
    return { memberOrder, changed };
}

function groupArea(group) {
    const bounds = group?._bounding || group?.bounding;
    if (!bounds || typeof bounds.length !== "number" || bounds.length < 4) return Number.POSITIVE_INFINITY;
    return Math.max(0, finite(bounds[2])) * Math.max(0, finite(bounds[3]));
}

export function findDatangGroupsForNode(groups = [], node = null) {
    if (!node) return [];
    return (groups || []).filter((group) => (
        readDatangGroupState(group) && Array.isArray(group?._nodes) && group._nodes.includes(node)
    ));
}

export function findInnermostDatangGroupForNode(groups = [], node = null) {
    return findDatangGroupsForNode(groups, node)
        .sort((left, right) => groupArea(left) - groupArea(right))[0] || null;
}

export function isDatangGroupPresenceEnabled(groups = [], node = null) {
    const containingGroups = findDatangGroupsForNode(groups, node);
    return containingGroups.length > 0
        && containingGroups.every((group) => readDatangGroupState(group)?.enabled === true);
}

export function chooseDatangGroupController(group, controllers = []) {
    const candidates = (controllers || []).filter((node) => node?.id !== null && node?.id !== undefined);
    const savedId = readDatangGroupState(group)?.controller_id;
    if (savedId !== null && savedId !== undefined) {
        const saved = candidates.find((node) => String(node.id) === String(savedId));
        if (saved) return saved;
    }
    return candidates[0] || null;
}

function normalizedGroupTitle(value) {
    return String(value || "").trim().toLocaleLowerCase();
}

export function indexDatangGroupControllers(groups = [], controllers = []) {
    const validGroups = Array.isArray(groups) ? groups : [];
    const validControllers = Array.isArray(controllers) ? controllers : [];
    const groupsByTitle = new Map();
    for (const group of validGroups) {
        const title = normalizedGroupTitle(group?.title);
        if (!title) continue;
        const matches = groupsByTitle.get(title) || [];
        matches.push(group);
        groupsByTitle.set(title, matches);
    }

    const groupByController = new Map();
    const candidatesByGroup = new Map();
    for (const controller of validControllers) {
        const savedMatches = validGroups.filter((candidate) => {
            const savedId = readDatangGroupState(candidate)?.controller_id;
            return savedId !== null && savedId !== undefined
                && String(savedId) === String(controller?.id);
        });
        let group = savedMatches.length === 1 ? savedMatches[0] : null;
        if (!group && savedMatches.length === 0) {
            const title = normalizedGroupTitle(controller?.properties?.datang_group_title);
            const exact = title ? groupsByTitle.get(title) || [] : [];
            group = exact.length === 1 ? exact[0] : null;
        }
        if (!group && savedMatches.length === 0) {
            group = validGroups
                .filter((candidate) => Array.isArray(candidate?._nodes) && candidate._nodes.includes(controller))
                .sort((a, b) => {
                    const areaA = Math.max(0, finite(a?._bounding?.[2] ?? a?.bounding?.[2]))
                        * Math.max(0, finite(a?._bounding?.[3] ?? a?.bounding?.[3]));
                    const areaB = Math.max(0, finite(b?._bounding?.[2] ?? b?.bounding?.[2]))
                        * Math.max(0, finite(b?._bounding?.[3] ?? b?.bounding?.[3]));
                    return areaA - areaB;
                })[0] || null;
        }
        if (!group) continue;
        groupByController.set(controller, group);
        const candidates = candidatesByGroup.get(group) || [];
        candidates.push(controller);
        candidatesByGroup.set(group, candidates);
    }

    const controllerByGroup = new Map();
    for (const group of validGroups) {
        const controller = chooseDatangGroupController(group, candidatesByGroup.get(group) || []);
        if (controller) controllerByGroup.set(group, controller);
    }
    return { controllers: validControllers, groupByController, controllerByGroup };
}

export function groupHeaderSwitchRect(group, options = {}) {
    const bounds = group?._bounding || group?.bounding;
    if (!bounds || typeof bounds.length !== "number" || bounds.length < 4) return null;
    const width = finite(options.width, 78);
    const height = finite(options.height, 22);
    const rightReserve = finite(options.rightReserve, 92);
    const fontSize = finite(group?.font_size, 24);
    const titleHeight = fontSize * 1.4;
    const x = finite(bounds[0]) + Math.max(6, finite(bounds[2]) - rightReserve - width);
    const y = finite(bounds[1]) + Math.max(3, (titleHeight - height) / 2);
    return [x, y, width, height];
}

export function pointInsideRect(x, y, rect) {
    if (!rect || typeof rect.length !== "number" || rect.length < 4) return false;
    return x >= rect[0] && x <= rect[0] + rect[2] && y >= rect[1] && y <= rect[1] + rect[3];
}

export function uniqueGroupTitle(groups, baseTitle = "大汤节点组") {
    const used = new Set((groups || []).map((group) => String(group?.title || "").trim().toLocaleLowerCase()));
    if (!used.has(baseTitle.toLocaleLowerCase())) return baseTitle;
    let index = 2;
    while (used.has(`${baseTitle} ${index}`.toLocaleLowerCase())) index += 1;
    return `${baseTitle} ${index}`;
}

export function placeControllerBeforeMembers(order, controllerId, memberIds) {
    const controllerKey = String(controllerId);
    const members = new Set((memberIds || []).map(String));
    const next = (order || []).filter((id) => String(id) !== controllerKey);
    let targetIndex = next.findIndex((id) => members.has(String(id)));
    if (targetIndex < 0) targetIndex = next.length;
    next.splice(targetIndex, 0, controllerId);
    return next;
}

export function removeControllerFromOrder(order, controllerId) {
    const controllerKey = String(controllerId);
    return (order || []).filter((id) => String(id) !== controllerKey);
}

function modeMap(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    const result = {};
    for (const [id, mode] of Object.entries(value)) {
        const number = Number(mode);
        if (Number.isFinite(number)) result[String(id)] = number;
    }
    return result;
}

const REQUIRED_RESOURCE_INPUT_TYPES = new Set(["MODEL", "CLIP", "VAE"]);

function normalizedGraphLink(link) {
    if (Array.isArray(link)) {
        return {
            originId: String(link[1] ?? ""),
            targetId: String(link[3] ?? ""),
            targetSlot: Number(link[4]),
            type: String(link[5] || "").trim().toUpperCase(),
        };
    }
    if (!link || typeof link !== "object") return null;
    return {
        originId: String(link.origin_id ?? link.originId ?? ""),
        targetId: String(link.target_id ?? link.targetId ?? ""),
        targetSlot: Number(link.target_slot ?? link.targetSlot),
        type: String(link.type || "").trim().toUpperCase(),
    };
}

function isRequiredResourceInput(node, slot, type) {
    if (!REQUIRED_RESOURCE_INPUT_TYPES.has(type)) return false;
    const input = Array.isArray(node?.inputs) ? node.inputs[slot] : null;
    const inputName = String(input?.name || "").trim();
    if (!inputName) return false;
    const required = node?.constructor?.nodeData?.input?.required
        || node?.nodeData?.input?.required;
    if (required && typeof required === "object" && !Array.isArray(required)) {
        return Object.hasOwn(required, inputName);
    }
    return inputName.toLowerCase() === type.toLowerCase();
}

export function repairRequiredResourceSourceModes({ members = [], previousModes, links = [] }) {
    const remembered = modeMap(previousModes);
    const memberById = new Map((members || []).map((node) => [String(node?.id), node]));
    let changed = false;

    for (const rawLink of links || []) {
        const link = normalizedGraphLink(rawLink);
        if (!link || !Number.isInteger(link.targetSlot) || link.targetSlot < 0) continue;
        const source = memberById.get(link.originId);
        const target = memberById.get(link.targetId);
        if (!source || !target) continue;
        if (remembered[link.originId] !== NODE_MODE.BYPASS) continue;
        if (remembered[link.targetId] === NODE_MODE.BYPASS) continue;
        if (!isRequiredResourceInput(target, link.targetSlot, link.type)) continue;
        remembered[link.originId] = NODE_MODE.ALWAYS;
        changed = true;
    }

    return { previousModes: remembered, changed };
}

export function reconcileGroupModes({ allNodes = [], members = [], enabled, previousModes }) {
    const nodesById = new Map((allNodes || []).map((node) => [String(node?.id), node]));
    const memberIds = new Set((members || []).map((node) => String(node?.id)));
    const remembered = modeMap(previousModes);
    let changed = false;

    if (enabled) {
        for (const node of members || []) {
            const id = String(node?.id);
            const nextMode = Object.hasOwn(remembered, id) ? remembered[id] : NODE_MODE.ALWAYS;
            if (node.mode !== nextMode) {
                node.mode = nextMode;
                changed = true;
            }
        }
        for (const [id, previousMode] of Object.entries(remembered)) {
            const node = nodesById.get(id);
            if (node && !memberIds.has(id) && node.mode === NODE_MODE.BYPASS) {
                node.mode = previousMode;
                changed = true;
            }
        }
        return { previousModes: {}, changed };
    }

    for (const [id, previousMode] of Object.entries(remembered)) {
        if (memberIds.has(id)) continue;
        const node = nodesById.get(id);
        if (node && node.mode === NODE_MODE.BYPASS) {
            node.mode = previousMode;
            changed = true;
        }
        delete remembered[id];
    }
    for (const node of members || []) {
        const id = String(node?.id);
        if (!Object.hasOwn(remembered, id)) remembered[id] = finite(node?.mode, NODE_MODE.ALWAYS);
        if (node.mode !== NODE_MODE.BYPASS) {
            node.mode = NODE_MODE.BYPASS;
            changed = true;
        }
    }
    return { previousModes: remembered, changed };
}
