class DatangBooleanNand:
    """Turn on when either upstream value reports that its source is not empty."""

    CATEGORY = "大汤自制节点/工作流"
    FUNCTION = "evaluate"
    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("布尔值",)
    DESCRIPTION = "两个“是否为空”都为真时关闭；任意一个为假时开启。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "条件A是否为空": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "连接第一个上游节点的“是否为空”输出。",
                    },
                ),
                "条件B是否为空": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "连接第二个上游节点的“是否为空”输出。",
                    },
                ),
            }
        }

    def evaluate(self, 条件A是否为空: bool, 条件B是否为空: bool):
        return (not (bool(条件A是否为空) and bool(条件B是否为空)),)


NODE_CLASS_MAPPINGS = {
    "DatangBooleanNand": DatangBooleanNand,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DatangBooleanNand": "大汤布尔与非",
}
