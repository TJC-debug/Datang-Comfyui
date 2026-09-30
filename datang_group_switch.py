class DatangGroupSwitch:
    """Canvas group controller; frontend code owns membership and node modes."""

    CATEGORY = "大汤自制节点/工作流"
    FUNCTION = "return_state"
    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("启用状态",)
    DESCRIPTION = "配合画布右键命令创建原生节点组，并统一启用或忽略组内节点。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "启用节点组": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "label_on": "启用",
                        "label_off": "忽略",
                        "tooltip": "开启时恢复组内节点，关闭时将组内节点设为 Bypass。",
                    },
                ),
            }
        }

    def return_state(self, 启用节点组: bool):
        return (bool(启用节点组),)


NODE_CLASS_MAPPINGS = {
    "DatangGroupSwitch": DatangGroupSwitch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DatangGroupSwitch": "大汤节点组开关",
}
