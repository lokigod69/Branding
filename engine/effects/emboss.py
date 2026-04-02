"""
emboss.py — Emboss / Engrave Effect

Light-based depth illusion with adjustable light direction.
Creates a 3D embossed or engraved look through convolution kernels.
"""

import math
import numpy as np
import cv2
from engine.effects.base import BaseEffect


class EmbossEffect(BaseEffect):
    name = "Emboss / Engrave"
    description = "3D depth illusion with adjustable light direction — embossed or engraved."
    category = "branding"

    def apply(self, image, mask, params):
        angle = params.get("light_angle", 135)  # degrees, 0=right, 90=top
        depth = params.get("depth", 1.0)  # multiplier for the effect
        style = params.get("style", "emboss")  # "emboss" or "engrave"

        rgb = image[:, :, :3]
        has_alpha = image.shape[2] == 4

        # Convert to grayscale for the emboss computation
        gray = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

        # Build directional emboss kernel based on light angle
        rad = math.radians(angle)
        dx = math.cos(rad)
        dy = -math.sin(rad)  # Negative because y-axis is flipped

        # 3×3 directional kernel
        kernel = np.zeros((3, 3), dtype=np.float32)
        kernel[1, 1] = 0

        # Map direction to kernel positions
        # Positions: TL(0,0) T(0,1) TR(0,2) L(1,0) C(1,1) R(1,2) BL(2,0) B(2,1) BR(2,2)
        positions = [
            (-1, -1, 0, 0), (-1, 0, 0, 1), (-1, 1, 0, 2),
            (0, -1, 1, 0),                  (0, 1, 1, 2),
            (1, -1, 2, 0),  (1, 0, 2, 1),   (1, 1, 2, 2),
        ]

        for py, px, ky, kx in positions:
            dot = px * dx + py * dy
            kernel[ky, kx] = dot * depth

        if style == "engrave":
            kernel = -kernel

        # Apply per channel
        result = np.zeros_like(rgb)
        for c in range(3):
            embossed = cv2.filter2D(rgb[:, :, c], -1, kernel)
            # Shift to 50% gray baseline + original color
            result[:, :, c] = rgb[:, :, c] + embossed * 0.5

        result = np.clip(result, 0, 1)

        if has_alpha:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"light_angle": 135, "depth": 1.0, "style": "emboss"}


EFFECT = EmbossEffect()
