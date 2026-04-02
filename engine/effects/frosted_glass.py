"""
frosted_glass.py — Frosted Glass (Branded Blur) Effect

Localized Gaussian blur inside the mask with a brightness boost
for a backlit, etched-glass feel.
"""

import numpy as np
import cv2
from engine.effects.base import BaseEffect


class FrostedGlassEffect(BaseEffect):
    name = "Frosted Glass"
    description = "Localized blur with a brightness boost — backlit etched glass."
    category = "integrated"

    def apply(self, image, mask, params):
        blur_radius = params.get("blur_radius", 15)
        brightness_boost = params.get("brightness_boost", 1.15)

        rgb = image[:, :, :3]
        has_alpha = image.shape[2] == 4

        # Ensure odd kernel size
        ksize = int(blur_radius * 2) | 1
        ksize = max(ksize, 3)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(rgb, (ksize, ksize), blur_radius)

        # Apply brightness boost
        result = blurred * brightness_boost

        result = np.clip(result, 0, 1)

        if has_alpha:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"blur_radius": 15, "brightness_boost": 1.15}


EFFECT = FrostedGlassEffect()
