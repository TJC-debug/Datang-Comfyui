import json
import math
from typing import Any


DEFAULT_LAYOUT = json.dumps(
    {
        "schemaVersion": 1,
        "dpi": 300,
        "layoutId": "preview-default",
        "canvas": {"width": 1051, "height": 1500, "background": "#ffffff"},
        "slots": [{"x": 378, "y": 544, "width": 295, "height": 413}],
        "cropMarks": [],
    },
    ensure_ascii=False,
    separators=(",", ":"),
)


class IdPhotoLayoutError(ValueError):
    pass


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise IdPhotoLayoutError(f"{field} 必须是有限数字。")
    rounded = int(value)
    if rounded != value or rounded < minimum or rounded > maximum:
        raise IdPhotoLayoutError(f"{field} 必须是 {minimum} 到 {maximum} 的整数。")
    return rounded


def _record(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IdPhotoLayoutError(f"{field} 格式不正确。")
    return value


def _parse_background(value: Any) -> tuple[float, float, float]:
    text = str(value or "#ffffff").strip()
    if len(text) != 7 or not text.startswith("#"):
        raise IdPhotoLayoutError("canvas.background 必须是 #RRGGBB。")
    try:
        channels = tuple(int(text[index:index + 2], 16) / 255 for index in (1, 3, 5))
    except ValueError as exc:
        raise IdPhotoLayoutError("canvas.background 必须是 #RRGGBB。") from exc
    return channels


def _clip_crop_marks_to_whitespace(
    marks: list[dict[str, int]],
    slots: list[dict[str, int]],
) -> list[dict[str, int]]:
    safe_marks: list[dict[str, int]] = []
    for mark in marks:
        horizontal = mark["y1"] == mark["y2"]
        fixed = mark["y1"] if horizontal else mark["x1"]
        start = min(mark["x1"], mark["x2"]) if horizontal else min(mark["y1"], mark["y2"])
        end = max(mark["x1"], mark["x2"]) if horizontal else max(mark["y1"], mark["y2"])
        intervals = [(start, end)]
        for slot in slots:
            crosses_slot = (
                slot["y"] <= fixed < slot["y"] + slot["height"]
                if horizontal
                else slot["x"] <= fixed < slot["x"] + slot["width"]
            )
            if not crosses_slot:
                continue
            blocked_start = slot["x"] if horizontal else slot["y"]
            blocked_end = blocked_start + (slot["width"] if horizontal else slot["height"]) - 1
            next_intervals: list[tuple[int, int]] = []
            for interval_start, interval_end in intervals:
                if interval_end < blocked_start or interval_start > blocked_end:
                    next_intervals.append((interval_start, interval_end))
                    continue
                if interval_start < blocked_start:
                    next_intervals.append((interval_start, blocked_start - 1))
                if interval_end > blocked_end:
                    next_intervals.append((blocked_end + 1, interval_end))
            intervals = next_intervals
            if not intervals:
                break
        for interval_start, interval_end in intervals:
            safe_mark = dict(mark)
            if horizontal:
                safe_mark.update({"x1": interval_start, "x2": interval_end})
            else:
                safe_mark.update({"y1": interval_start, "y2": interval_end})
            safe_marks.append(safe_mark)
            if len(safe_marks) > 1600:
                raise IdPhotoLayoutError("裁剪线安全裁切后数量过多。")
    return safe_marks


def parse_layout(value: Any) -> dict[str, Any]:
    try:
        raw = json.loads(value) if isinstance(value, str) else value
    except (json.JSONDecodeError, TypeError) as exc:
        raise IdPhotoLayoutError("排版数据不是有效 JSON。") from exc
    layout = _record(raw, "排版数据")
    if layout.get("schemaVersion") != 1:
        raise IdPhotoLayoutError("仅支持证件照排版合同 v1。")
    layout_id = str(layout.get("layoutId") or "").strip()
    if not layout_id or len(layout_id) > 96:
        raise IdPhotoLayoutError("layoutId 缺失或过长。")
    ui_settings = layout.get("_ui", {}).get("settings", {}) if isinstance(layout.get("_ui"), dict) else {}
    if not isinstance(ui_settings, dict):
        ui_settings = {}
    image_orientation = layout.get("imageOrientation", ui_settings.get("photoOrientation", "original"))
    if image_orientation not in {"original", "portrait", "landscape"}:
        raise IdPhotoLayoutError("imageOrientation 只支持 original、portrait 或 landscape。")
    dpi = _integer(layout.get("dpi", ui_settings.get("dpi", 300)), "dpi", 72, 1200)

    canvas = _record(layout.get("canvas"), "canvas")
    canvas_width = _integer(canvas.get("width"), "canvas.width", 1, 12000)
    canvas_height = _integer(canvas.get("height"), "canvas.height", 1, 12000)
    if canvas_width * canvas_height > 80_000_000:
        raise IdPhotoLayoutError("排版画布像素过大。")
    background = _parse_background(canvas.get("background"))

    raw_slots = layout.get("slots")
    if not isinstance(raw_slots, list) or not 1 <= len(raw_slots) <= 200:
        raise IdPhotoLayoutError("slots 必须包含 1 到 200 个照片位置。")
    slots: list[dict[str, int]] = []
    for index, raw_slot in enumerate(raw_slots):
        slot = _record(raw_slot, f"slots[{index}]")
        parsed = {
            "x": _integer(slot.get("x"), f"slots[{index}].x", 0, canvas_width - 1),
            "y": _integer(slot.get("y"), f"slots[{index}].y", 0, canvas_height - 1),
            "width": _integer(slot.get("width"), f"slots[{index}].width", 1, canvas_width),
            "height": _integer(slot.get("height"), f"slots[{index}].height", 1, canvas_height),
            "rotation": _integer(slot.get("rotation", 0), f"slots[{index}].rotation", 0, 270),
        }
        if parsed["rotation"] not in {0, 90, 180, 270}:
            raise IdPhotoLayoutError(f"slots[{index}].rotation 只支持 0、90、180 或 270。")
        if parsed["x"] + parsed["width"] > canvas_width or parsed["y"] + parsed["height"] > canvas_height:
            raise IdPhotoLayoutError(f"slots[{index}] 超出画布。")
        for previous_index, previous in enumerate(slots):
            separated = (
                parsed["x"] + parsed["width"] <= previous["x"]
                or previous["x"] + previous["width"] <= parsed["x"]
                or parsed["y"] + parsed["height"] <= previous["y"]
                or previous["y"] + previous["height"] <= parsed["y"]
            )
            if not separated:
                raise IdPhotoLayoutError(f"slots[{index}] 与 slots[{previous_index}] 重叠。")
        slots.append(parsed)

    raw_marks = layout.get("cropMarks", [])
    if not isinstance(raw_marks, list) or len(raw_marks) > 1600:
        raise IdPhotoLayoutError("cropMarks 数量不正确。")
    crop_marks: list[dict[str, int]] = []
    for index, raw_mark in enumerate(raw_marks):
        mark = _record(raw_mark, f"cropMarks[{index}]")
        parsed = {
            "x1": _integer(mark.get("x1"), f"cropMarks[{index}].x1", 0, canvas_width - 1),
            "y1": _integer(mark.get("y1"), f"cropMarks[{index}].y1", 0, canvas_height - 1),
            "x2": _integer(mark.get("x2"), f"cropMarks[{index}].x2", 0, canvas_width - 1),
            "y2": _integer(mark.get("y2"), f"cropMarks[{index}].y2", 0, canvas_height - 1),
            "width": _integer(mark.get("width", 1), f"cropMarks[{index}].width", 1, 8),
        }
        if parsed["x1"] != parsed["x2"] and parsed["y1"] != parsed["y2"]:
            raise IdPhotoLayoutError(f"cropMarks[{index}] 只允许水平或垂直线。")
        crop_marks.append(parsed)

    crop_marks = _clip_crop_marks_to_whitespace(crop_marks, slots)

    return {
        "schemaVersion": 1,
        "layoutId": layout_id,
        "dpi": dpi,
        "imageOrientation": image_orientation,
        "canvas": {
            "width": canvas_width,
            "height": canvas_height,
            "background": background,
        },
        "slots": slots,
        "cropMarks": crop_marks,
    }


def _round_scaled(value: int, ratio: float) -> int:
    return int(math.floor(value * ratio + 0.5))


def scale_layout_to_dpi(layout: dict[str, Any], dpi: int) -> dict[str, Any]:
    source_dpi = layout["dpi"]
    if dpi == source_dpi:
        return layout
    ratio = dpi / source_dpi
    scaled_slots = []
    for slot in layout["slots"]:
        left = _round_scaled(slot["x"], ratio)
        top = _round_scaled(slot["y"], ratio)
        right = _round_scaled(slot["x"] + slot["width"], ratio)
        bottom = _round_scaled(slot["y"] + slot["height"], ratio)
        scaled_slots.append({
            **slot,
            "x": left,
            "y": top,
            "width": max(1, right - left),
            "height": max(1, bottom - top),
        })
    return {
        **layout,
        "dpi": dpi,
        "canvas": {
            **layout["canvas"],
            "width": max(1, _round_scaled(layout["canvas"]["width"], ratio)),
            "height": max(1, _round_scaled(layout["canvas"]["height"], ratio)),
        },
        "slots": scaled_slots,
        "cropMarks": [{
            "x1": _round_scaled(mark["x1"], ratio),
            "y1": _round_scaled(mark["y1"], ratio),
            "x2": _round_scaled(mark["x2"], ratio),
            "y2": _round_scaled(mark["y2"], ratio),
            "width": max(1, _round_scaled(mark["width"], ratio)),
        } for mark in layout["cropMarks"]],
    }


def _median_integer(values: list[int], fallback: int = 0) -> int:
    if not values:
        return fallback
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return int(math.floor((ordered[middle - 1] + ordered[middle]) / 2 + 0.5))


def _crop_marks_for_slots(
    slots: list[dict[str, int]], canvas_width: int, canvas_height: int, dpi: int
) -> list[dict[str, int]]:
    pixels_per_cm = dpi / 2.54
    length = max(8, round(0.16 * pixels_per_cm))
    offset = max(2, round(0.025 * pixels_per_cm))

    def clamp_x(value: int) -> int:
        return max(0, min(canvas_width - 1, value))

    def clamp_y(value: int) -> int:
        return max(0, min(canvas_height - 1, value))

    marks: list[dict[str, int]] = []
    for slot in slots:
        left = slot["x"]
        right = left + slot["width"] - 1
        top = slot["y"]
        bottom = top + slot["height"] - 1
        for x in (left, right):
            marks.append({"x1": clamp_x(x), "y1": clamp_y(top - offset - length), "x2": clamp_x(x), "y2": clamp_y(top - offset), "width": 1})
            marks.append({"x1": clamp_x(x), "y1": clamp_y(bottom + offset), "x2": clamp_x(x), "y2": clamp_y(bottom + offset + length), "width": 1})
        for y in (top, bottom):
            marks.append({"x1": clamp_x(left - offset - length), "y1": clamp_y(y), "x2": clamp_x(left - offset), "y2": clamp_y(y), "width": 1})
            marks.append({"x1": clamp_x(right + offset), "y1": clamp_y(y), "x2": clamp_x(right + offset + length), "y2": clamp_y(y), "width": 1})
    return _clip_crop_marks_to_whitespace(
        [mark for mark in marks if mark["x1"] != mark["x2"] or mark["y1"] != mark["y2"]],
        slots,
    )


def reflow_layout_to_photo_size(
    layout: dict[str, Any], width: int, height: int
) -> dict[str, Any]:
    width = _integer(width, "输入照片宽度", 1, 12000)
    height = _integer(height, "输入照片高度", 1, 12000)
    orientation = layout["imageOrientation"]
    if orientation == "portrait" and width > height:
        width, height = height, width
    elif orientation == "landscape" and height > width:
        width, height = height, width

    slots = layout["slots"]
    base_sizes = {
        (slot["height"], slot["width"])
        if slot.get("rotation", 0) in {90, 270}
        else (slot["width"], slot["height"])
        for slot in slots
    }
    if len(base_sizes) != 1:
        raise IdPhotoLayoutError("单一外部照片尺寸不能用于一寸与二寸混合排版。")

    rows_by_y: dict[int, list[dict[str, int]]] = {}
    for slot in sorted(slots, key=lambda item: (item["y"], item["x"])):
        rows_by_y.setdefault(slot["y"], []).append(slot)
    rows = [rows_by_y[y] for y in sorted(rows_by_y)]

    gap_candidates: list[int] = []
    for row in rows:
        ordered = sorted(row, key=lambda item: item["x"])
        gap_candidates.extend(
            max(0, current["x"] - (previous["x"] + previous["width"]))
            for previous, current in zip(ordered, ordered[1:])
        )
    for previous, current in zip(rows, rows[1:]):
        previous_bottom = max(slot["y"] + slot["height"] for slot in previous)
        current_top = min(slot["y"] for slot in current)
        gap_candidates.append(max(0, current_top - previous_bottom))
    gap = _median_integer(gap_candidates, 0)

    planned_rows: list[list[dict[str, int]]] = []
    row_widths: list[int] = []
    row_heights: list[int] = []
    for row in rows:
        planned_row = []
        for slot in sorted(row, key=lambda item: item["x"]):
            rotated = slot.get("rotation", 0) in {90, 270}
            planned_row.append({
                **slot,
                "width": height if rotated else width,
                "height": width if rotated else height,
            })
        planned_rows.append(planned_row)
        row_widths.append(
            sum(slot["width"] for slot in planned_row) + gap * max(0, len(planned_row) - 1)
        )
        row_heights.append(max(slot["height"] for slot in planned_row))

    canvas_width = layout["canvas"]["width"]
    canvas_height = layout["canvas"]["height"]
    grid_height = sum(row_heights) + gap * max(0, len(planned_rows) - 1)
    if max(row_widths, default=0) > canvas_width or grid_height > canvas_height:
        raise IdPhotoLayoutError(
            f"外部证件照尺寸 {width}×{height} 像素无法按当前行列完整排入 "
            f"{canvas_width}×{canvas_height} 像素画布。"
        )

    next_slots: list[dict[str, int]] = []
    y = round((canvas_height - grid_height) / 2)
    for row, row_width, row_height in zip(planned_rows, row_widths, row_heights):
        x = round((canvas_width - row_width) / 2)
        for slot in row:
            next_slots.append({
                **slot,
                "x": x,
                "y": y + (row_height - slot["height"]) // 2,
            })
            x += slot["width"] + gap
        y += row_height + gap

    return {
        **layout,
        "slots": next_slots,
        "cropMarks": _crop_marks_for_slots(
            next_slots, canvas_width, canvas_height, layout["dpi"]
        ) if layout["cropMarks"] else [],
        "externalPhotoSize": {"width": width, "height": height},
    }


class DatangIdPhotoLayout:
    """Compose a finished ID photo into exact caller-owned pixel slots."""

    CATEGORY = "大汤自制节点/图像"
    FUNCTION = "compose"
    RETURN_TYPES = ("IMAGE", "STRING", "INT")
    RETURN_NAMES = ("排版图", "排版回执", "DPI")
    DESCRIPTION = "按冻结坐标排版，并输出用于真实 DPI 保存的分辨率。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图片": ("IMAGE",),
                "DPI": (
                    "INT",
                    {
                        "default": 300,
                        "min": 72,
                        "max": 1200,
                        "step": 1,
                        "tooltip": "厘米规格按此 DPI 换算像素；连接到大汤证件照 DPI 保存节点可写入文件元数据。",
                    },
                ),
                "排版数据": (
                    "STRING",
                    {
                        "default": DEFAULT_LAYOUT,
                        "multiline": True,
                        "tooltip": "由纳贝AI冻结并提交的证件照排版合同 v1。",
                    },
                ),
            },
            "optional": {
                "输入DPI": (
                    "INT",
                    {
                        "forceInput": True,
                        "tooltip": "可连接其他节点输出的 DPI；连接后优先于高级设置，并按比例缩放整套冻结像素布局。",
                    },
                ),
                "输入照片宽度": (
                    "INT",
                    {
                        "forceInput": True,
                        "tooltip": "连接预设裁剪尺寸节点的宽度输出；必须与输入照片高度同时连接。",
                    },
                ),
                "输入照片高度": (
                    "INT",
                    {
                        "forceInput": True,
                        "tooltip": "连接预设裁剪尺寸节点的高度输出；必须与输入照片宽度同时连接。",
                    },
                ),
            },
        }

    def compose(
        self,
        图片,
        DPI: int,
        排版数据: str,
        输入DPI=None,
        输入照片宽度=None,
        输入照片高度=None,
    ):
        import numpy as np
        import torch
        from PIL import Image

        layout = parse_layout(排版数据)
        dpi = (
            _integer(输入DPI, "输入DPI", 72, 1200)
            if 输入DPI is not None
            else _integer(DPI, "DPI", 72, 1200)
        )
        source_layout_dpi = layout["dpi"]
        if 输入DPI is not None:
            layout = scale_layout_to_dpi(layout, dpi)
        has_external_width = 输入照片宽度 is not None
        has_external_height = 输入照片高度 is not None
        if has_external_width != has_external_height:
            raise IdPhotoLayoutError("输入照片宽度和输入照片高度必须同时连接。")
        if has_external_width:
            layout = reflow_layout_to_photo_size(layout, 输入照片宽度, 输入照片高度)
        if not isinstance(图片, torch.Tensor) or 图片.ndim != 4 or 图片.shape[-1] < 3:
            raise IdPhotoLayoutError("图片必须是 ComfyUI IMAGE 张量。")
        source = 图片[..., :3]
        batch, source_height, source_width, _ = source.shape
        if source_height < 1 or source_width < 1:
            raise IdPhotoLayoutError("输入图片尺寸为空。")

        canvas_width = layout["canvas"]["width"]
        canvas_height = layout["canvas"]["height"]
        background = source.new_tensor(layout["canvas"]["background"]).view(1, 1, 1, 3)
        output = background.expand(batch, canvas_height, canvas_width, 3).clone()
        source_nchw = source.permute(0, 3, 1, 2)
        image_orientation = layout["imageOrientation"]
        should_rotate = (
            image_orientation == "landscape" and source_height > source_width
        ) or (
            image_orientation == "portrait" and source_width > source_height
        )
        if should_rotate:
            source_nchw = torch.rot90(source_nchw, k=-1, dims=(-2, -1))
            source_height, source_width = source_width, source_height

        resize_cache = {}
        for slot in layout["slots"]:
            rotation = slot["rotation"]
            slot_source = source_nchw if rotation == 0 else torch.rot90(
                source_nchw,
                k=-(rotation // 90),
                dims=(-2, -1),
            )
            slot_source_height = int(slot_source.shape[-2])
            slot_source_width = int(slot_source.shape[-1])
            scale = min(slot["width"] / slot_source_width, slot["height"] / slot_source_height)
            target_width = max(1, min(slot["width"], round(slot_source_width * scale)))
            target_height = max(1, min(slot["height"], round(slot_source_height * scale)))
            cache_key = (rotation, target_height, target_width)
            resized = resize_cache.get(cache_key)
            if resized is None:
                if target_height == slot_source_height and target_width == slot_source_width:
                    resized = slot_source.permute(0, 2, 3, 1)
                else:
                    resampling = getattr(Image, "Resampling", Image).LANCZOS
                    resized_batches = []
                    for batch_image in slot_source:
                        rgb = (
                            batch_image.permute(1, 2, 0)
                            .detach()
                            .to(device="cpu", dtype=torch.float32)
                            .clamp(0, 1)
                            .mul(255)
                            .round()
                            .to(torch.uint8)
                            .numpy()
                        )
                        resized_rgb = np.asarray(
                            Image.fromarray(rgb, mode="RGB").resize(
                                (target_width, target_height),
                                resample=resampling,
                            ),
                            dtype=np.float32,
                        ).copy()
                        resized_batches.append(torch.from_numpy(resized_rgb).div_(255))
                    resized = torch.stack(resized_batches).to(
                        device=source.device,
                        dtype=source.dtype,
                    )
                resize_cache[cache_key] = resized
            x = slot["x"] + (slot["width"] - target_width) // 2
            y = slot["y"] + (slot["height"] - target_height) // 2
            output[:, y:y + target_height, x:x + target_width, :] = resized

        for mark in layout["cropMarks"]:
            half = mark["width"] // 2
            if mark["x1"] == mark["x2"]:
                x0 = max(0, mark["x1"] - half)
                x1 = min(canvas_width, x0 + mark["width"])
                y0, y1 = sorted((mark["y1"], mark["y2"]))
                output[:, y0:y1 + 1, x0:x1, :] = 0
            else:
                y0 = max(0, mark["y1"] - half)
                y1 = min(canvas_height, y0 + mark["width"])
                x0, x1 = sorted((mark["x1"], mark["x2"]))
                output[:, y0:y1, x0:x1 + 1, :] = 0

        receipt = json.dumps(
            {
                "schemaVersion": 1,
                "layoutId": layout["layoutId"],
                "canvas": {"width": canvas_width, "height": canvas_height},
                "slotCount": len(layout["slots"]),
                "imageOrientation": image_orientation,
                "resizeFilter": "lanczos",
                "dpi": dpi,
                "layoutDpi": source_layout_dpi,
                "dpiSource": "input" if 输入DPI is not None else "advanced_setting",
                "dpiMetadata": "由专用 DPI 保存节点写入",
                "photoSizeSource": "input" if has_external_width else "frozen_layout",
                "photoSize": layout.get("externalPhotoSize") or {
                    "width": layout["slots"][0]["width"],
                    "height": layout["slots"][0]["height"],
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return (output, receipt, dpi)


NODE_CLASS_MAPPINGS = {"DatangIdPhotoLayout": DatangIdPhotoLayout}
NODE_DISPLAY_NAME_MAPPINGS = {"DatangIdPhotoLayout": "大汤证件照智能排版"}
