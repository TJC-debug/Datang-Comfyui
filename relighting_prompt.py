"""Fixed, compact relighting prompt presets for ComfyUI workflows.

The canvas exposes only human-readable Chinese labels.  The full prompt text
is resolved in this backend node and emitted as one standard STRING.
"""

from collections.abc import Mapping


PRESET_GROUPS = {
    "主光方向": {
        "不指定": "",
        "正面光": "frontal key light from the camera direction, evenly lighting the subject",
        "画面左侧光": "key light from camera-left, natural directional shading toward camera-right",
        "画面右侧光": "key light from camera-right, natural directional shading toward camera-left",
        "左前45度光": "45-degree front key light from camera-left, dimensional facial modeling",
        "右前45度光": "45-degree front key light from camera-right, dimensional facial modeling",
        "顶光": "overhead top light, shadows falling naturally downward",
        "底光": "uplight from below, upward-cast shadows and dramatic modeling",
        "逆光": "backlight behind the subject, luminous edge separation",
        "双侧轮廓光": "balanced rim lights from both rear sides, clean subject separation",
    },
    "人像布光法": {
        "不指定": "",
        "单灯布光": "single-light setup with one clearly motivated key light",
        "主辅双灯": "two-light setup with a dominant key and restrained fill light",
        "经典三点布光": "classic three-point lighting with key, fill and back light",
        "蝴蝶光": "butterfly lighting, centered high key light with a small symmetrical shadow under the nose",
        "环形光": "ring light, even frontal illumination with a clean circular catchlight",
        "伦勃朗光": "Rembrandt lighting with a small triangle of light on the shadow-side cheek",
        "环路光": "loop lighting with a short nose shadow angled gently to one side",
        "分割光": "split lighting, one half of the face lit and the other half in shadow",
        "宽光": "broad lighting, the camera-facing side of the face illuminated",
        "窄光": "short lighting, the camera-facing side of the face in shadow for slimmer modeling",
        "蛤壳光": "clamshell beauty lighting with soft upper key and lower fill",
    },
    "光线质感": {
        "不指定": "",
        "柔光": "soft diffused light, gentle transitions and soft shadow edges",
        "硬光": "hard directional light, crisp shadow edges and strong definition",
        "漫射光": "broad ambient diffused illumination with smooth tonal transitions",
        "聚光灯": "focused spotlight with controlled falloff around the subject",
        "大面积包裹光": "large wrapping light source, smooth dimensional gradients around the subject",
        "清透日光": "clean transparent daylight with natural skin and material rendering",
        "方向性窗光": "directional window light with soft but readable falloff",
    },
    "明暗与光比": {
        "不指定": "",
        "均衡曝光": "balanced exposure with retained highlight and shadow detail",
        "低对比平光": "low-contrast flat lighting with very gentle tonal separation",
        "中等对比": "medium lighting ratio with natural highlight-to-shadow separation",
        "高对比": "high-contrast lighting with deep shadows and bright highlights",
        "高调明亮": "high-key bright lighting, airy tones and minimal deep shadows",
        "低调暗黑": "low-key lighting, predominantly dark tones with controlled highlights",
        "剪影": "silhouette lighting, bright background and a deliberately dark subject shape",
    },
    "色温与色彩": {
        "不指定": "",
        "中性白光": "neutral white light around 5000K with accurate natural colors",
        "暖色光": "warm amber illumination around 3000K with a welcoming atmosphere",
        "冷色光": "cool blue illumination around 7000K with a crisp atmosphere",
        "日落金": "golden sunset light with warm amber highlights",
        "蓝调时刻": "blue-hour lighting with deep blue ambient tones and subtle warm accents",
        "冷暖双色": "cinematic warm key light and cool fill light with controlled color separation",
        "霓虹双色": "two-tone neon lighting with saturated complementary colors",
        "单色光": "cohesive monochromatic colored lighting while retaining tonal detail",
    },
    "阴影形态": {
        "不指定": "",
        "柔和阴影": "soft natural shadows with feathered edges",
        "清晰硬影": "crisp directional cast shadows with clean edges",
        "长投影": "long directional cast shadows suggesting a low-angle light source",
        "短投影": "short compact cast shadows suggesting a high-angle light source",
        "百叶窗光影": "venetian-blind light and shadow stripes cast across the scene",
        "窗框投影": "realistic window-frame shadows cast across the subject and surroundings",
        "树影斑驳": "dappled foliage shadows with irregular natural light patches",
        "几乎无影": "nearly shadowless illumination with very soft uniform fill",
    },
    "补光与控光": {
        "不指定": "",
        "无补光": "no fill light, preserve a strong natural shadow side",
        "反光板柔补": "subtle reflector fill that gently lifts shadows without flattening the key light",
        "柔光箱补光": "softbox fill light with smooth controlled shadow recovery",
        "环境反弹光": "natural bounced ambient fill matching the surrounding environment",
        "负补光加深": "negative fill that deepens the shadow side and increases dimensionality",
        "眼神光": "clean natural catchlights in the eyes without changing eye shape or color",
        "发丝轮廓补光": "restrained hair light defining fine strands and the head contour",
        "背景分离光": "subtle background separation light behind the subject",
    },
    "高光与材质": {
        "不指定": "",
        "自然高光": "natural controlled highlights that preserve material texture",
        "柔和高光": "broad soft highlights with smooth roll-off and no clipping",
        "镜面高光": "clean specular highlights that describe glossy surfaces without overexposure",
        "压制反光": "reduced glare and restrained specular reflections while retaining material realism",
        "金属质感高光": "precise directional highlights that reveal metallic surface shape",
        "皮肤通透高光": "subtle luminous skin highlights with preserved pores and natural texture",
    },
    "场景光源与光效": {
        "不指定": "",
        "自然窗光": "natural daylight entering through a window with believable room falloff",
        "黄金时刻": "golden-hour sunlight with a low warm direction and long soft shadows",
        "阴天漫射": "overcast daylight, broad soft illumination and restrained contrast",
        "月光夜景": "cool moonlit night ambience with selective readable highlights",
        "室内实景灯": "motivated practical interior lights integrated naturally into the scene",
        "体积光雾": "subtle volumetric light in light atmospheric haze with preserved subject clarity",
        "丁达尔光束": "visible Tyndall light rays passing through fine atmospheric particles",
        "光晕": "controlled optical glow around bright light sources without obscuring details",
        "镜头耀斑": "restrained cinematic lens flare motivated by a visible or off-frame light source",
        "散景光斑": "soft out-of-focus practical-light bokeh in the background",
        "焦散光纹": "realistic caustic light patterns projected onto surfaces",
        "舞台光束": "defined theatrical light beams with atmospheric depth and subject separation",
    },
    "风格预设": {
        "不指定": "",
        "电影感": "cinematic lighting, motivated sources, controlled contrast and nuanced color separation",
        "日系清新": "bright airy Japanese editorial lighting, soft daylight and clean gentle colors",
        "商业棚拍": "polished commercial studio lighting, clean separation and accurate material detail",
        "时尚杂志": "high-end fashion editorial lighting with sculpted highlights and confident contrast",
        "黑色电影": "film-noir lighting, dramatic chiaroscuro, deep shadows and selective highlights",
        "古典油画": "classical painterly chiaroscuro with warm highlights and rich gradual shadows",
        "自然纪实": "natural documentary lighting with believable ambient light and restrained grading",
        "赛博霓虹": "cyberpunk neon lighting with vivid color separation and reflective accents",
        "舞台戏剧": "theatrical stage lighting with focused beams, deep falloff and dramatic separation",
        "产品广告": "premium product-advertising lighting with precise edges, material highlights and clean gradients",
    },
}

DEFAULT_SELECTIONS = {
    group_name: next(iter(options))
    for group_name, options in PRESET_GROUPS.items()
}


def compose_relighting_prompt(selections: Mapping[str, str]) -> str:
    """Resolve labels in a stable group order and return the hidden prompt text."""

    if not isinstance(selections, Mapping):
        raise ValueError("重新打光选项必须按大类提供。")

    prompts = []
    for group_name, options in PRESET_GROUPS.items():
        selected = selections.get(group_name)
        if not isinstance(selected, str) or selected not in options:
            raise ValueError(f"“{group_name}”的选项无效，请重新选择。")
        prompt = options[selected]
        if prompt:
            prompts.append(prompt)
    return ", ".join(prompts)


class DatangRelightingPrompt:
    CATEGORY = "大汤自制节点/提示词"
    FUNCTION = "build_prompt"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("重新打光提示词",)
    DESCRIPTION = "按多个中文下拉选项组合专业重新打光提示词；画布不展示后台完整提示词。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                group_name: (
                    list(options),
                    {
                        "default": DEFAULT_SELECTIONS[group_name],
                        "tooltip": f"选择{group_name}；完整提示词由节点后台输出。",
                    },
                )
                for group_name, options in PRESET_GROUPS.items()
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        try:
            compose_relighting_prompt(kwargs)
        except ValueError as error:
            return str(error)
        return True

    def build_prompt(self, **kwargs):
        return (compose_relighting_prompt(kwargs),)


NODE_CLASS_MAPPINGS = {"DatangRelightingPrompt": DatangRelightingPrompt}
NODE_DISPLAY_NAME_MAPPINGS = {"DatangRelightingPrompt": "大汤重新打光提示词"}
