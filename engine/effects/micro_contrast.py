"""
micro_contrast.py — Micro-Contrast Boost Effect

Boosts local contrast / clarity inside the mask only.
No color change — just makes the text area sharper and more "present."
"""

import numpy as np
import cv2
from engine.effects.base import BaseEffect


class MicroContrastEffect(BaseEffect):
    name = "Micro-Contrast Boost"
    description = "Boost local contrast/clarity — makes the signature feel sharper."
    category = "branding"

    def apply(self, image, mask, params):
        amount = params.get("amount", 1.5)  # Unsharp mask amount
        radius = params.get("radius", 20)   # Large radius = local contrast

        rgb = image[:, :, :3]
        has_alpha = image.shape[2] == 4

        # Convert to LAB to modify luminance only
        rgb_uint8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
        lab = cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2LAB).astype(np.float32)

        l_channel = lab[:, :, 0]

        # Unsharp mask with large radius = local contrast enhancement
        ksize = int(radius * 2) | 1
        ksize = max(ksize, 3)
        blurred = cv2.GaussianBlur(l_channel, (ksize, ksize), radius)

        # USM: sharpened = original + amount * (original - blurred)
        enhanced = l_channel + amount * (l_channel - blurred)
        lab[:, :, 0] = np.clip(enhanced, 0, 255)

        result_uint8 = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB)
        result = result_uint8.astype(np.float32) / 255.0

        if has_alpha:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"amount": 1.5, "radius": 20}


EFFECT = MicroContrastEffect()
