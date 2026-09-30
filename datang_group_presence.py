class DatangGroupPresenceMarker:
    """Stable group-presence value kept active while ordinary group members are bypassed."""

    CATEGORY = "大汤自制节点/工作流"
    FUNCTION = "evaluate"
    RETURN_TYPES = ("STRING", "BOOLEAN", "BOOLEAN")
    RETURN_NAMES = ("状态标记", "是否为空", "组已启用")
    DESCRIPTION = "放入大汤可开关节点组：组开启时输出非空标记，组忽略时输出 None。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "组已启用": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "由所在的大汤节点组自动同步，请勿手动修改。",
                    },
                ),
            }
        }

    def evaluate(self, 组已启用: bool):
        enabled = bool(组已启用)
        return ("enabled" if enabled else None, not enabled, enabled)


NODE_CLASS_MAPPINGS = {
    "DatangGroupPresenceMarker": DatangGroupPresenceMarker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DatangGroupPresenceMarker": "大汤节点组状态标记",
}
