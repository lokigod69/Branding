"""
glass_displacement.py — Glass / Heat Shimmer Displacement Effect

Uses a seeded noise field to warp pixel positions inside the mask,
creating a glass refraction or heat shimmer look.
"""

import numpy as np
import cv2
from engine.effects.base import BaseEffect


class GlassDisplacementEffect(BaseEffect):
    name = "Glass Displacement"
    description = "Noise-field pixel warp — glass refraction or heat shimmer."
    category = "integrated"

    def apply(self, image, mask, params):
        seed = params.get("seed", 12345)
        displacement_strength = params.get("displacement", 8.0)  # pixels
        noise_scale = params.get("noise_scale", 0.02)

        h, w = image.shape[:2]
        has_alpha = image.shape[2] == 4

        # Seed the RNG for reproducibility
        rng = np.random.RandomState(seed)

        # Generate smooth noise fields for X and Y displacement
        # Start with random noise, then smooth it
        noise_x = rng.randn(h, w).astype(np.float32)
        noise_y = rng.randn(h, w).astype(np.float32)

        # Smooth the noise for organic flow
        smooth_size = max(int(displacement_strength * 4) | 1, 3)
        noise_x = cv2.GaussianBlur(noise_x, (smooth_size, smooth_size), displacement_strength)
        noise_y = cv2.GaussianBlur(noise_y, (smooth_size, smooth_size), displacement_strength)

        # Normalize to [-1, 1] range
        noise_x = noise_x / (np.abs(noise_x).max() + 1e-6)
        noise_y = noise_y / (np.abs(noise_y).max() + 1e-6)

        # Scale by displacement strength
        dx = noise_x * displacement_strength
        dy = noise_y * displacement_strength

        # Create remap arrays
        map_y, map_x = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        map_x = (map_x + dx).astype(np.float32)
        map_y = (map_y + dy).astype(np.float32)

        # Apply remapping
        result = cv2.remap(
            image[:, :, :3], map_x, map_y,
            interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )

        result = np.clip(result, 0, 1)

        if has_alpha:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"seed": 12345, "displacement": 8.0, "noise_scale": 0.02}


EFFECT = GlassDisplacementEffect()
