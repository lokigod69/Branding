"""
spatial.py — Spatial Mask Generators

Generate masks based on image structure:
  - flat_areas: low local variance (smooth/plastic zones)
  - edges: high gradient magnitude
"""

import numpy as np
import cv2


def flat_areas_mask(
    image: np.ndarray,
    sensitivity: float = 0.7,
    radius: int = 5,
) -> np.ndarray:
    """
    Mask for flat/smooth areas — where AI plastic look is most visible.

    Uses local variance in a sliding window. Low variance = flat = mask 1.0.

    Args:
        sensitivity: 0–1, higher means more area is considered "flat"
        radius: analysis window radius

    Returns:
        float32 (H, W) mask, 1.0 in flat areas, 0.0 in textured areas
    """
    # Convert to grayscale
    gray = np.mean(image[:, :, :3], axis=2).astype(np.float32)

    ksize = radius * 2 + 1

    # Local mean and variance via box filter
    local_mean = cv2.blur(gray, (ksize, ksize))
    local_sq_mean = cv2.blur(gray * gray, (ksize, ksize))
    local_var = np.maximum(local_sq_mean - local_mean * local_mean, 0.0)

    # Map variance to mask: low variance → high mask
    # Sensitivity controls the threshold
    # At sensitivity=1.0, almost everything is "flat"
    # At sensitivity=0.0, only perfectly smooth areas
    threshold = 0.001 + (1.0 - sensitivity) * 0.02
    mask = np.clip(1.0 - local_var / max(threshold, 1e-8), 0.0, 1.0)

    # Smooth the mask
    mask = cv2.GaussianBlur(mask, (ksize, ksize), radius * 0.5)

    return mask.astype(np.float32)


def edges_mask(
    image: np.ndarray,
    threshold: float = 0.1,
    radius: int = 1,
) -> np.ndarray:
    """
    Mask for edge regions — high gradient magnitude.

    Args:
        threshold: gradient magnitude threshold (0–1)
        radius: Sobel kernel radius

    Returns:
        float32 (H, W) mask, 1.0 at edges, 0.0 in flat areas
    """
    gray = np.mean(image[:, :, :3], axis=2).astype(np.float32)

    ksize = radius * 2 + 1
    if ksize < 3:
        ksize = 3

    # Sobel gradients
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=ksize)
    magnitude = np.sqrt(gx * gx + gy * gy)

    # Normalize
    max_mag = magnitude.max()
    if max_mag > 0:
        magnitude = magnitude / max_mag

    # Threshold with soft transition
    mask = np.clip((magnitude - threshold * 0.5) / max(threshold * 0.5, 1e-6), 0.0, 1.0)

    return mask.astype(np.float32)
