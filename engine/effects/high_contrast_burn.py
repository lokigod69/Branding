"""
high_contrast_burn.py — High-Contrast Burn Effect

Gamma curve manipulation: crushes shadows and peaks highlights
inside the mask for a dramatic, branded look.
"""

import numpy as np
from engine.effects.base import BaseEffect


class HighContrastBurnEffect(BaseEffect):
    name = "High-Contrast Burn"
    description = "Crush shadows and peak highlights — dramatic gamma manipulation."
    category = "integrated"

    def apply(self, image, mask, params):
        shadow_gamma = params.get("shadow_gamma", 0.4)     # < 1 = darker shadows
        highlight_gamma = params.get("highlight_gamma", 1.8)  # > 1 = brighter highlights
        midpoint = params.get("midpoint", 0.5)

        rgb = image[:, :, :3]
        has_alpha = image.shape[2] == 4

        # S-curve via split gamma
        result = np.zeros_like(rgb)

        # Below midpoint: crush shadows
        dark_mask = rgb < midpoint
        normalized_dark = rgb / (midpoint + 1e-6)
        result = np.where(
            dark_mask,
            midpoint * np.power(np.clip(normalized_dark, 1e-6, 1.0), 1.0 / shadow_gamma),
            result,
        )

        # Above midpoint: peak highlights
        light_mask = ~dark_mask
        normalized_light = (rgb - midpoint) / (1.0 - midpoint + 1e-6)
        result = np.where(
            light_mask,
            midpoint + (1.0 - midpoint) * np.power(np.clip(normalized_light, 1e-6, 1.0), 1.0 / highlight_gamma),
            result,
        )

        result = np.clip(result, 0, 1)

        if has_alpha:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"shadow_gamma": 0.4, "highlight_gamma": 1.8, "midpoint": 0.5}


EFFECT = HighContrastBurnEffect()
