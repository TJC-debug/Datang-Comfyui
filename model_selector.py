import json
from typing import Any


class AnyType(str):
    """ComfyUI wildcard output used by Primitive-style selector nodes."""

    def __ne__(self, _value):
        return False


ANY_TYPE = AnyType("*")
DEFAULT_ITEMS = json.dumps(
    [
        {"name": "模型 1", "value": "", "enabled": True, "_selection_mode": "单选"},
        {"name": "模型 2", "value": "", "enabled": False},
    ],
    ensure_ascii=False,
    separators=(",", ":"),
)


class DatangModelSelector:
    """Return exactly one author-configured value to a connected model combo input."""

    CATEGORY = "大汤自制节点/模型"
    FUNCTION = "select_model"
    RETURN_TYPES = (ANY_TYPE,)
    RETURN_NAMES = ("当前模型",)
    DESCRIPTION = "连接到模型下拉参数后，可配置两个或更多互斥模型槽位。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型数据": (
                    "STRING",
                    {
                        "default": DEFAULT_ITEMS,
                        "multiline": True,
                        "tooltip": "由节点界面自动保存，请通过模型槽位编辑。",
                    },
                ),
            }
        }

    @staticmethod
    def _normalise_items(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        if not isinstance(value, list):
            return []
        result = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    "name": str(item.get("name") or f"模型 {index + 1}"),
                    "value": item.get("value", ""),
                    "enabled": item.get("enabled") is True,
                }
            )
        return result

    def select_model(self, 模型数据: str):
        items = self._normalise_items(模型数据)
        selected = next((item for item in items if item["enabled"]), None)
        if selected is None:
            selected = next((item for item in items if str(item["value"]).strip()), None)
        return ((selected or {}).get("value", ""),)


NODE_CLASS_MAPPINGS = {
    "DatangModelSelector": DatangModelSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DatangModelSelector": "模型选择器（单选多槽位）",
}
