"""
pipeline.py — Stage Stack Executor

Executes the unified image finishing pipeline:
  Input → [Filter stages] → [Signing stage] → [Final finish stages] → Output

Stages are processed in array order — the stages[] list IS the canonical ordering.
Only one signing stage is supported; signing config lives at preset top level.
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from engine.io_handler import ImageMeta
from engine.compositor import composite, _apply_blend_mode
from engine.filters.base import FilterRegistry
from engine.masks import generate_filter_mask, apply_mask_modifiers


def execute_pipeline(
    image: np.ndarray,
    meta: ImageMeta,
    stages: List[Dict[str, Any]],
    signing_config: Optional[Dict[str, Any]] = None,
    global_intensity: float = 1.0,
    target_resolution: Optional[Tuple[int, int]] = None,
) -> np.ndarray:
    """
    Execute the full stage stack on an image.

    Args:
        image: float32 (H, W, C), range [0, 1]
        meta: ImageMeta for the source image
        stages: ordered list of stage dicts (filter or signing)
        signing_config: top-level signing configuration (text, font, layout, effect)
        global_intensity: 0.0–1.0, overall pipeline blend
        target_resolution: (w, h) of final output for resolution-aware filters

    Returns:
        Processed float32 array (H, W, C)
    """
    if not stages:
        return image

    original = image.copy()
    result = image.copy()

    for stage in stages:
        if not stage.get("enabled", True):
            continue

        stage_type = stage.get("type", "filter")

        if stage_type == "filter":
            result = _execute_filter_stage(result, stage, target_resolution)
        elif stage_type == "signing":
            if signing_config:
                if isinstance(signing_config, list):
                    configs = signing_config
                else:
                    configs = [signing_config]
                for s_config in configs:
                    if not s_config.get("hidden", False):
                        result = _execute_signing_stage(result, meta, s_config)

    # Apply global intensity: blend pipeline result with original
    if global_intensity < 1.0:
        result = original * (1.0 - global_intensity) + result * global_intensity

    return np.clip(result, 0.0, 1.0)


def _execute_filter_stage(
    image: np.ndarray,
    stage: Dict[str, Any],
    target_resolution: Optional[Tuple[int, int]] = None,
) -> np.ndarray:
    """
    Execute a single filter stage.

    Handles: filter lookup, apply, mask generation, mask modifiers,
    intensity blending, and stage-level blend mode.
    """
    filter_key = stage.get("filter_key", "")
    filt = FilterRegistry.get(filter_key)
    if filt is None:
        # Unknown filter — skip silently
        return image

    params = stage.get("params", {})
    intensity = stage.get("intensity", 1.0)
    blend_mode = stage.get("blend_mode", "normal")
    mask_source = stage.get("mask_source", "global")
    mask_params = stage.get("mask_params", {})
    mask_modifiers_cfg = stage.get("mask_modifiers", {})

    # Apply the filter
    filtered = filt.apply(image, params, target_resolution=target_resolution)

    # Apply stage-level blend mode
    if blend_mode != "normal":
        filtered = _apply_blend_mode(image, filtered, blend_mode)

    # Generate and apply mask
    if mask_source != "global":
        mask = generate_filter_mask(image, mask_source, mask_params)
        # Apply mask modifiers (feather, invert, clamp, noise, border)
        if mask_modifiers_cfg:
            mask = apply_mask_modifiers(mask, mask_modifiers_cfg)
        # Blend: original where mask=0, filtered where mask=1, scaled by intensity
        alpha = mask[:, :, np.newaxis] * intensity
        result = image * (1.0 - alpha) + filtered * alpha
    else:
        # Global — simple intensity blend
        if intensity < 1.0:
            result = image * (1.0 - intensity) + filtered * intensity
        else:
            result = filtered

    return np.clip(result, 0.0, 1.0)


def _execute_signing_stage(
    image: np.ndarray,
    meta: ImageMeta,
    signing_config: Dict[str, Any],
) -> np.ndarray:
    """
    Execute the signing stage — generates text mask, applies effect, composites.
    This is the existing signing pipeline extracted into the stage stack.
    """
    from engine.mask_generator import generate_mask
    from engine.effects.base import EffectRegistry

    h, w = image.shape[:2]

    # Extract signing settings
    text = signing_config.get("text", "LAZART")
    font_cfg = signing_config.get("font", {})
    layout_cfg = signing_config.get("layout", {})
    effect_cfg = signing_config.get("effect", {})

    font_path = font_cfg.get("path")

    # Generate text mask OR per-letter masks
    per_letter_effects = signing_config.get("per_letter_effects")

    if per_letter_effects and len(per_letter_effects) > 0:
        from engine.mask_generator import generate_per_letter_masks
        letter_masks = generate_per_letter_masks(
            text=text,
            image_width=w,
            image_height=h,
            font_path=font_path,
            size_rel_width=layout_cfg.get("size_rel_width", 0.22),
            x_pct=layout_cfg.get("position", {}).get("x_pct", 0.5),
            y_pct=layout_cfg.get("position", {}).get("y_pct", 0.5),
            anchor=layout_cfg.get("position", {}).get("anchor", "center"),
            rotation_deg=layout_cfg.get("rotation_deg", -8.0),
            tracking=layout_cfg.get("tracking", 0.02),
            feather_px=layout_cfg.get("feather_px", 2.0),
            skew_x=layout_cfg.get("skew_x", 0.0),
            skew_y=layout_cfg.get("skew_y", 0.0),
            perspective_x=layout_cfg.get("perspective_x", 0.0),
            perspective_y=layout_cfg.get("perspective_y", 0.0),
            vertical=layout_cfg.get("vertical", False),
            mirror_x=layout_cfg.get("mirror_x", False),
            mirror_y=layout_cfg.get("mirror_y", False),
        )

        output = image.copy()
        for i, (char, mask) in enumerate(letter_masks):
            if i < len(per_letter_effects):
                ple = per_letter_effects[i]
            else:
                ple = {}

            etype = ple.get("effect_type", effect_cfg.get("type", "difference"))
            effect = EffectRegistry.get(etype)
            if effect is None:
                effect = EffectRegistry.get("difference")

            eparams = ple.get("effect_params", effect_cfg.get("params", {}))
            base_color_rgb = signing_config.get("base_color_rgb", [255, 255, 255])
            if "color_rgb" not in eparams:
                eparams["color_rgb"] = base_color_rgb

            estrength = ple.get("strength", effect_cfg.get("strength", 0.85))
            eblend = ple.get("blend_mode", effect_cfg.get("blend_mode", "normal"))

            effected = effect.apply(image, mask, eparams)
            output = composite(output, effected, mask, strength=estrength, blend_mode=eblend)

        return output

    # --- Uniform mode (original path) ---
    mask = generate_mask(
        text=text,
        image_width=w,
        image_height=h,
        font_path=font_path,
        size_rel_width=layout_cfg.get("size_rel_width", 0.22),
        x_pct=layout_cfg.get("position", {}).get("x_pct", 0.5),
        y_pct=layout_cfg.get("position", {}).get("y_pct", 0.5),
        anchor=layout_cfg.get("position", {}).get("anchor", "center"),
        rotation_deg=layout_cfg.get("rotation_deg", -8.0),
        tracking=layout_cfg.get("tracking", 0.02),
        feather_px=layout_cfg.get("feather_px", 2.0),
        skew_x=layout_cfg.get("skew_x", 0.0),
        skew_y=layout_cfg.get("skew_y", 0.0),
        perspective_x=layout_cfg.get("perspective_x", 0.0),
        perspective_y=layout_cfg.get("perspective_y", 0.0),
        vertical=layout_cfg.get("vertical", False),
        mirror_x=layout_cfg.get("mirror_x", False),
        mirror_y=layout_cfg.get("mirror_y", False),
    )

    # Apply effect
    effect_type = effect_cfg.get("type", "difference")
    effect = EffectRegistry.get(effect_type)
    if effect is None:
        return image

    effect_params = effect_cfg.get("params", {})
    
    # Inject base color if not explicitly overridden in effect_params
    base_color_rgb = signing_config.get("base_color_rgb", [255, 255, 255])
    if "color_rgb" not in effect_params:
        effect_params["color_rgb"] = base_color_rgb

    effected = effect.apply(image, mask, effect_params)

    # Composite
    strength = effect_cfg.get("strength", 0.85)
    blend_mode = effect_cfg.get("blend_mode", "normal")

    output = composite(
        image, effected, mask,
        strength=strength,
        blend_mode=blend_mode,
    )

    return output
