"""
compositor.py — Core Pixel Blending

Implements the fundamental compositing equation:
  output = original × (1 - mask × strength) + effect(original) × (mask × strength)

Also provides secondary blend mode modifiers (overlay, soft light, color burn).
"""

import numpy as np


def composite(
    original: np.ndarray,
    effected: np.ndarray,
    mask: np.ndarray,
    strength: float = 1.0,
    blend_mode: str = "normal",
) -> np.ndarray:
    """
    Blend original and effected images using the mask.

    Args:
        original: float32 (H, W, C), range [0, 1]
        effected: float32 (H, W, C), range [0, 1] — result of an effect
        mask: float32 (H, W), range [0, 1] — the text alpha mask
        strength: 0.0–1.0, overall mix strength
        blend_mode: "normal", "overlay", "soft_light", "color_burn", "multiply", "screen"

    Returns:
        Composited float32 array (H, W, C)
    """
    # Expand mask to match image channels
    if mask.ndim == 2:
        alpha = mask[:, :, np.newaxis]
    else:
        alpha = mask

    alpha = alpha * strength

    # Apply blend mode to the effected result if not "normal"
    if blend_mode != "normal":
        effected = _apply_blend_mode(original, effected, blend_mode)

    # Core compositing equation
    output = original * (1.0 - alpha) + effected * alpha

    return np.clip(output, 0.0, 1.0)


def _apply_blend_mode(
    base: np.ndarray, top: np.ndarray, mode: str
) -> np.ndarray:
    """Apply a Photoshop-style blend mode between base and top layers."""

    if mode == "overlay":
        # Overlay: combines multiply and screen
        low = 2.0 * base * top
        high = 1.0 - 2.0 * (1.0 - base) * (1.0 - top)
        result = np.where(base < 0.5, low, high)

    elif mode == "soft_light":
        # Soft Light (Pegtop formula)
        result = (1.0 - 2.0 * top) * base * base + 2.0 * top * base

    elif mode == "color_burn":
        # Color Burn: darkens base by increasing contrast
        safe_top = np.maximum(top, 1e-6)
        result = 1.0 - (1.0 - base) / safe_top
        result = np.maximum(result, 0.0)

    elif mode == "multiply":
        result = base * top

    elif mode == "screen":
        result = 1.0 - (1.0 - base) * (1.0 - top)

    elif mode == "difference":
        result = np.abs(base - top)

    elif mode == "exclusion":
        result = base + top - 2.0 * base * top

    else:
        result = top  # Fallback to normal

    return np.clip(result, 0.0, 1.0)
