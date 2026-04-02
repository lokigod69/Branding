"""
duotone.py — Duotone / Gradient Map Effect

Maps pixel luminance inside the mask to a two-color gradient.
Black → color_a, White → color_b.
"""

import numpy as np
from engine.effects.base import BaseEffect


class DuotoneEffect(BaseEffect):
    name = "Duotone"
    description = "Two-color gradient map inside letters — stylish color branding."
    category = "integrated"

    def apply(self, image, mask, params):
        color_a = np.array(params.get("color_a", [20, 20, 80]), dtype=np.float32) / 255.0
        
        # If the user selected a base text color, use it for the bright mapping
        user_color = params.get("color_rgb")
        if user_color is not None:
            color_b = np.array(user_color, dtype=np.float32) / 255.0
        else:
            color_b = np.array(params.get("color_b", [255, 200, 100]), dtype=np.float32) / 255.0

        rgb = image[:, :, :3]
        has_alpha = image.shape[2] == 4

        # Compute luminance
        luma = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

        # Linear interpolation between color_a and color_b
        result = np.zeros_like(rgb)
        for c in range(3):
            result[:, :, c] = color_a[c] * (1.0 - luma) + color_b[c] * luma

        result = np.clip(result, 0, 1)

        if has_alpha:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"color_a": [20, 20, 80], "color_b": [255, 200, 100]}


EFFECT = DuotoneEffect()
