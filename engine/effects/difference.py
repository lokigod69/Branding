"""
difference.py — Difference Blend Effect

|original - tint_color| per pixel inside mask.
The classic "sees through anything" signature look.
"""

import numpy as np
from engine.effects.base import BaseEffect


class DifferenceEffect(BaseEffect):
    name = "Difference Blend"
    description = "Signature cuts through anything — inverts relative to a tint color."
    category = "signature"

    def apply(self, image, mask, params):
        # Tint color (default: white for pure difference)
        color_rgb = params.get("color_rgb", [255, 255, 255])
        tint = np.array(color_rgb, dtype=np.float32).reshape(1, 1, 3) / 255.0

        # Difference blend
        result = np.abs(image[:, :, :3] - tint)

        # Preserve alpha if present
        if image.shape[2] == 4:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"color_rgb": [255, 255, 255]}


EFFECT = DifferenceEffect()
