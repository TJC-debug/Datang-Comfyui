class AnyType(str):
    """ComfyUI 通配类型；只用于在不同数据类型之间原样选路。"""

    def __ne__(self, _other):
        return False


ANY_TYPE = AnyType("*")


class DatangBooleanConstant:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("BOOLEAN",)
    RETURN_NAMES = ("值",)
    FUNCTION = "emit"
    CATEGORY = "大汤自制节点/逻辑"

    def emit(self, value=False):
        return (bool(value),)


class DatangLazyIfElse:
    """只请求被选中的输入，避免关闭的工作流分支仍被 ComfyUI 执行。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "boolean": ("BOOLEAN", {"forceInput": True}),
                "on_true": (ANY_TYPE, {"lazy": True}),
                "on_false": (ANY_TYPE, {"lazy": True}),
            }
        }

    RETURN_TYPES = (ANY_TYPE,)
    RETURN_NAMES = ("输出",)
    FUNCTION = "select"
    CATEGORY = "大汤自制节点/逻辑"

    def check_lazy_status(self, boolean, on_true=None, on_false=None):
        selected_name = "on_true" if bool(boolean) else "on_false"
        selected_value = on_true if bool(boolean) else on_false
        return [selected_name] if selected_value is None else []

    def select(self, boolean, on_true=None, on_false=None):
        return (on_true if bool(boolean) else on_false,)


NODE_CLASS_MAPPINGS = {
    "DatangBooleanConstant": DatangBooleanConstant,
    "DatangLazyIfElse": DatangLazyIfElse,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DatangBooleanConstant": "大汤布尔常量",
    "DatangLazyIfElse": "大汤惰性条件分支",
}
