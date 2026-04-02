"""
tonal.py — Tonal Mask Generators

Generate masks based on image luminance:
  - shadows: dark areas
  - mids: mid-tone areas
  - highlights: bright areas
"""

import numpy as np
import cv2


def _luminance(image: np.ndarray) -> np.ndarray:
    """Compute perceptual luminance from RGB. Returns float32 (H, W)."""
    rgb = image[:, :, :3]
    # Rec. 709 luminance weights
    return 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]


def shadows_mask(
    image: np.ndarray,
    threshold: float = 0.35,
    feather: float = 0.1,
) -> np.ndarray:
    """
    Mask for shadow regions (luminance < threshold).

    Args:
        threshold: luminance cutoff (0–1)
        feather: width of the soft transition zone

    Returns:
        float32 (H, W) mask, 1.0 in deep shadows, 0.0 in bright areas
    """
    luma = _luminance(image)
    if feather > 0.001:
        low = max(0.0, threshold - feather)
        # Smooth ramp: 1.0 where luma < low, 0.0 where luma > threshold
        mask = np.clip((threshold - luma) / max(feather, 1e-6), 0.0, 1.0)
    else:
        mask = (luma < threshold).astype(np.float32)
    return mask.astype(np.float32)


def mids_mask(
    image: np.ndarray,
    low: float = 0.25,
    high: float = 0.75,
    feather: float = 0.1,
) -> np.ndarray:
    """
    Mask for mid-tone regions (luminance between low and high).

    Args:
        low: lower boundary
        high: upper boundary
        feather: transition softness

    Returns:
        float32 (H, W) mask, 1.0 in mid tones
    """
    luma = _luminance(image)
    if feather > 0.001:
        # Ramp up from low, ramp down from high
        ramp_up = np.clip((luma - (low - feather)) / max(feather, 1e-6), 0.0, 1.0)
        ramp_down = np.clip(((high + feather) - luma) / max(feather, 1e-6), 0.0, 1.0)
        mask = ramp_up * ramp_down
    else:
        mask = ((luma >= low) & (luma <= high)).astype(np.float32)
    return mask.astype(np.float32)


def highlights_mask(
    image: np.ndarray,
    threshold: float = 0.65,
    feather: float = 0.1,
) -> np.ndarray:
    """
    Mask for highlight regions (luminance > threshold).

    Args:
        threshold: luminance cutoff (0–1)
        feather: transition softness

    Returns:
        float32 (H, W) mask, 1.0 in bright areas
    """
    luma = _luminance(image)
    if feather > 0.001:
        mask = np.clip((luma - threshold) / max(feather, 1e-6), 0.0, 1.0)
    else:
        mask = (luma > threshold).astype(np.float32)
    return mask.astype(np.float32)
