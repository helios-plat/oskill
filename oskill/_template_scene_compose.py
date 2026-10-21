"""oskill.template_scene_compose — compose scenes from a template spec."""

from __future__ import annotations

from typing import Any


def template_scene_compose(
    *,
    template: dict[str, Any],
    assets: dict[str, Any] | None = None,
    variables: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Compose a list of scenes from a template.

    template: {scenes: [{id, duration, text, asset_key, ...}]}
    Returns list of scene dicts with resolved assets/text.
    """
    assets = assets or {}
    variables = variables or {}
    scenes = template.get("scenes", []) if isinstance(template, dict) else []
    out = []
    for sc in scenes:
        scene = dict(sc)
        # resolve asset
        ak = scene.get("asset_key")
        if ak and ak in assets:
            scene["asset"] = assets[ak]
        # variable substitution in text
        text = scene.get("text", "")
        if isinstance(text, str):
            for k, v in variables.items():
                text = text.replace("{{" + k + "}}", str(v))
            scene["text"] = text
        out.append(scene)
    return out
