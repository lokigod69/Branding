"""
batch_processor.py — Async Batch Processing with Progress Reporting

Processes multiple images through the signing pipeline.
Reports progress via callback for WebSocket integration.
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime

import numpy as np

from engine.io_handler import load_image, save_image, create_proxy
from engine.mask_generator import generate_mask
from engine.compositor import composite
from engine.effects.base import EffectRegistry
from engine.presets import PresetSchema


async def process_batch(
    image_paths: List[str],
    preset: PresetSchema,
    output_dir: str,
    progress_callback: Optional[Callable] = None,
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Process a batch of images with the given preset.

    Args:
        image_paths: list of input image file paths
        preset: the preset configuration to apply
        output_dir: directory to write signed images to
        progress_callback: async callback(current, total, image_name, status)
        overrides: optional per-image parameter overrides keyed by filename

    Returns:
        List of result dicts with status and output paths
    """
    results = []
    total = len(image_paths)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for idx, img_path in enumerate(image_paths):
        img_name = Path(img_path).name
        try:
            if progress_callback:
                await progress_callback(idx, total, img_name, "processing")

            result = await asyncio.to_thread(
                _process_single, img_path, preset, str(out_dir), overrides
            )
            results.append(result)

            if progress_callback:
                await progress_callback(idx + 1, total, img_name, "done")

        except Exception as e:
            results.append({
                "input": img_path,
                "output": None,
                "status": "error",
                "error": str(e),
            })
            if progress_callback:
                await progress_callback(idx + 1, total, img_name, f"error: {e}")

    return results


def _process_single(
    image_path: str,
    preset: PresetSchema,
    output_dir: str,
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Process a single image (runs in thread pool)."""
    # Load
    image, meta = load_image(image_path)
    h, w = image.shape[:2]

    # Apply per-image overrides
    layout = preset.layout.model_copy()
    effect_config = preset.effect.model_copy()
    img_name = Path(image_path).stem

    if overrides and img_name in overrides:
        ov = overrides[img_name]
        if "x_pct" in ov:
            layout.position.x_pct = ov["x_pct"]
        if "y_pct" in ov:
            layout.position.y_pct = ov["y_pct"]
        if "strength" in ov:
            effect_config.strength = ov["strength"]
        if "rotation_deg" in ov:
            layout.rotation_deg = ov["rotation_deg"]

    # Generate mask
    font_path = preset.font.path
    mask = generate_mask(
        text=preset.text,
        image_width=w,
        image_height=h,
        font_path=font_path,
        size_rel_width=layout.size_rel_width,
        x_pct=layout.position.x_pct,
        y_pct=layout.position.y_pct,
        anchor=layout.position.anchor,
        rotation_deg=layout.rotation_deg,
        tracking=layout.tracking,
        feather_px=layout.feather_px,
    )

    # Apply effect
    effect = EffectRegistry.get(effect_config.type)
    if effect is None:
        raise ValueError(f"Unknown effect type: {effect_config.type}")

    effected = effect.apply(image, mask, effect_config.params)

    # Composite
    output = composite(
        image, effected, mask,
        strength=effect_config.strength,
        blend_mode=effect_config.blend_mode,
    )

    # Build output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = preset.export.suffix or "__signed"
    ext = Path(image_path).suffix
    if preset.export.include_timestamp:
        out_name = f"{img_name}{suffix}__{timestamp}{ext}"
    else:
        out_name = f"{img_name}{suffix}{ext}"

    out_path = str(Path(output_dir) / out_name)

    # Save
    save_image(output, out_path, meta)

    # Save sidecar preset JSON
    import json
    sidecar_path = out_path + ".preset.json"
    with open(sidecar_path, "w") as f:
        json.dump(preset.model_dump(), f, indent=2)

    return {
        "input": image_path,
        "output": out_path,
        "status": "success",
    }
