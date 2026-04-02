"""
luma_invert.py — Luminance Inversion Effect

Inverts brightness only (in LAB color space), keeping hue stable.
Includes a 50%-gray safeguard to guarantee visibility on mid-tone backgrounds.
"""

import numpy as np
import cv2
from engine.effects.base import BaseEffect


class LumaInvertEffect(BaseEffect):
    name = "Luminance Invert"
    description = "Inverts brightness while preserving color hue — always visible."
    category = "signature"

    def apply(self, image, mask, params):
        brightness_shift = params.get("mid_gray_shift", 25)  # ±% shift for 50% gray

        rgb = image[:, :, :3]
        has_alpha = image.shape[2] == 4

        # Convert to LAB
        rgb_uint8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
        lab = cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2LAB).astype(np.float32)

        l_channel = lab[:, :, 0]  # L range: 0-255 in OpenCV's LAB

        # ── 50%-gray safeguard ──────────────────────────
        # L in OpenCV LAB: 0-255, mid gray ≈ 128
        # If L is in [40%, 60%] range (102-153), shift before inversion
        mid_low = 255 * 0.40
        mid_high = 255 * 0.60
        mid_mask = (l_channel >= mid_low) & (l_channel <= mid_high)

        # Apply shift: push away from 50% gray
        shift_amount = 255 * (brightness_shift / 100.0)
        # If below mid, push darker; if above or at mid, push lighter
        l_shifted = l_channel.copy()
        above_mid = l_channel >= 128
        l_shifted[mid_mask & above_mid] += shift_amount
        l_shifted[mid_mask & ~above_mid] -= shift_amount
        l_shifted = np.clip(l_shifted, 0, 255)

        # ── Invert luminance ────────────────────────────
        l_inverted = 255.0 - l_shifted

        lab[:, :, 0] = l_inverted

        # Convert back to RGB
        result_uint8 = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB)
        result = result_uint8.astype(np.float32) / 255.0

        if has_alpha:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"mid_gray_shift": 25}


EFFECT = LumaInvertEffect()
