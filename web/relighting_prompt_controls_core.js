export const RELIGHTING_PROMPT_NODE_ID = "DatangRelightingPrompt";

export const RELIGHTING_PROMPT_GROUPS = [
    "主光方向",
    "人像布光法",
    "光线质感",
    "明暗与光比",
    "色温与色彩",
    "阴影形态",
    "补光与控光",
    "高光与材质",
    "场景光源与光效",
    "风格预设",
];

const LEGACY_DEGREE_VALUES = new Set([
    "严格只改光影",
    "自然重新打光",
    "明显重塑光影",
]);

export function migrateRemovedRelightingDegree(node, serializedNode) {
    const savedValues = serializedNode?.widgets_values;
    if (!Array.isArray(savedValues)
        || savedValues.length < RELIGHTING_PROMPT_GROUPS.length + 1
        || !LEGACY_DEGREE_VALUES.has(savedValues[0])) {
        return false;
    }

    for (let index = 0; index < RELIGHTING_PROMPT_GROUPS.length; index += 1) {
        const widget = node.widgets?.find((item) => item?.name === RELIGHTING_PROMPT_GROUPS[index]);
        const savedValue = savedValues[index + 1];
        const choices = widget?.options?.values;
        if (widget && (!Array.isArray(choices) || choices.includes(savedValue))) {
            widget.value = savedValue;
        }
    }
    node.setDirtyCanvas?.(true, true);
    return true;
}
