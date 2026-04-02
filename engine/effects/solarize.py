"""
solarize.py — Solarization Effect

Threshold-based inversion: pixels above a brightness threshold are inverted.
Gives a photographic burning / darkroom experiment vibe.
"""

import numpy as np
from engine.effects.base import BaseEffect


class SolarizeEffect(BaseEffect):
    name = "Solarize"
    description = "Threshold-based inversion — photographic burning vibe."
    category = "signature"

    def apply(self, image, mask, params):
        threshold = params.get("threshold", 0.5)

        result = image.copy()
        rgb = result[:, :, :3]

        # Compute luminance for threshold comparison
        luma = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

        # Invert pixels above threshold
        above = luma > threshold
        above_3ch = above[:, :, np.newaxis]
        rgb_inverted = np.where(above_3ch, 1.0 - rgb, rgb)

        result[:, :, :3] = rgb_inverted
        return result

    def get_default_params(self):
        return {"threshold": 0.5}


EFFECT = SolarizeEffect()
