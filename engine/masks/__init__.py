"""
masks — Filter mask generation system

Provides mask generators for controlling where filter effects apply:
  - tonal: shadows, mids, highlights
  - spatial: flat areas, edges
  - (future: color, procedural, composite)
"""

from typing import Dict, Any
import numpy as np


def generate_filter_mask(
    image: np.ndarray,
    source: str,
    params: Dict[str, Any] = None,
) -> np.ndarray:
    """
    Generate a float32 (H, W) mask based on the given source type.

    Args:
        image: float32 (H, W, C), range [0, 1]
        source: mask type — "global", "shadows", "mids", "highlights",
                "flat_areas", "edges"
        params: source-specific parameters

    Returns:
        float32 (H, W) mask, range [0, 1]
    """
    if params is None:
        params = {}

    if source == "global":
        return np.ones(image.shape[:2], dtype=np.float32)

    elif source == "shadows":
        from engine.masks.tonal import shadows_mask
        return shadows_mask(image, **params)

    elif source == "mids":
        from engine.masks.tonal import mids_mask
        return mids_mask(image, **params)

    elif source == "highlights":
        from engine.masks.tonal import highlights_mask
        return highlights_mask(image, **params)

    elif source == "flat_areas":
        from engine.masks.spatial import flat_areas_mask
        return flat_areas_mask(image, **params)

    elif source == "edges":
        from engine.masks.spatial import edges_mask
        return edges_mask(image, **params)

    else:
        # Unknown source — fall back to global
        return np.ones(image.shape[:2], dtype=np.float32)


def apply_mask_modifiers(
    mask: np.ndarray,
    modifiers: Dict[str, Any],
) -> np.ndarray:
    """
    Apply post-generation modifiers to a mask.

    Supported modifiers:
        feather: float — Gaussian blur radius for softening edges
        invert: bool — flip the mask
        clamp_min: float — floor value
        clamp_max: float — ceiling value
        noise_breakup: float — add random noise to break up uniform areas
        border_softness: float — soften transitions at mask boundaries
    """
    if not modifiers:
        return mask

    result = mask.copy()

    # Invert
    if modifiers.get("invert", False):
        result = 1.0 - result

    # Clamp
    clamp_min = modifiers.get("clamp_min", 0.0)
    clamp_max = modifiers.get("clamp_max", 1.0)
    if clamp_min > 0.0 or clamp_max < 1.0:
        result = np.clip(result, clamp_min, clamp_max)
        # Re-normalize to 0..1
        if clamp_max > clamp_min:
            result = (result - clamp_min) / (clamp_max - clamp_min)

    # Feather (Gaussian blur)
    feather = modifiers.get("feather", 0.0)
    if feather > 0:
        import cv2
        ksize = int(feather * 4) | 1
        ksize = max(ksize, 3)
        result = cv2.GaussianBlur(result, (ksize, ksize), feather)

    # Border softness (additional edge blur on the mask boundary)
    border_softness = modifiers.get("border_softness", 0.0)
    if border_softness > 0:
        import cv2
        ksize = int(border_softness * 6) | 1
        ksize = max(ksize, 3)
        result = cv2.GaussianBlur(result, (ksize, ksize), border_softness)

    # Noise breakup
    noise_breakup = modifiers.get("noise_breakup", 0.0)
    if noise_breakup > 0:
        noise = np.random.default_rng(42).uniform(
            1.0 - noise_breakup, 1.0,
            size=result.shape,
        ).astype(np.float32)
        result = result * noise

    return np.clip(result, 0.0, 1.0)
