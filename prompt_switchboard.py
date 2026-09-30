import json
from typing import Any


DEFAULT_ITEMS = json.dumps(
    [{"name": "提示词 1", "text": "", "enabled": True}],
    ensure_ascii=False,
    separators=(",", ":"),
)


class PromptSwitchboard:
    """Combine enabled prompt rows into one STRING output."""

    CATEGORY = "大汤自制节点/提示词"
    FUNCTION = "combine"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("提示词",)
    DESCRIPTION = "可无限新增提示词槽位，并通过每行开关决定是否合并输出。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "提示词数据": (
                    "STRING",
                    {
                        "default": DEFAULT_ITEMS,
                        "multiline": True,
                        "tooltip": "由节点界面自动保存，请通过上方提示词槽位编辑。",
                    },
                ),
                "分隔符": (
                    "STRING",
                    {
                        "default": ", ",
                        "multiline": False,
                        "tooltip": "启用的提示词之间使用的分隔符。",
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

        items: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, str):
                items.append({"text": item, "enabled": True})
                continue
            if not isinstance(item, dict):
                continue
            text = item.get("text", "")
            if text is None:
                text = ""
            items.append(
                {
                    "text": str(text),
                    "enabled": bool(item.get("enabled", True)),
                }
            )
        return items

    @staticmethod
    def _selection_mode(value: Any) -> str:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return "多选"
        if not isinstance(value, list) or not value or not isinstance(value[0], dict):
            return "多选"
        return "单选" if value[0].get("_selection_mode") == "单选" else "多选"

    def combine(self, 提示词数据: str, 分隔符: str):
        selection_mode = self._selection_mode(提示词数据)
        items = self._normalise_items(提示词数据)
        enabled_prompts = [
            item["text"].strip()
            for item in items
            if item["enabled"] and item["text"].strip()
        ]
        if selection_mode == "单选":
            enabled_prompts = enabled_prompts[:1]
        return (str(分隔符).join(enabled_prompts),)


NODE_CLASS_MAPPINGS = {
    "PromptSwitchboard": PromptSwitchboard,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptSwitchboard": "提示词开关板（无限槽位）",
}
