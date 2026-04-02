"""
frequency_split.py — Frequency Split Effect

Modifies high-frequency detail only inside the mask.
Keeps overall tonality intact — makes the signature feel like it was always there.
"""

import numpy as np
import cv2
from engine.effects.base import BaseEffect


class FrequencySplitEffect(BaseEffect):
    name = "Frequency Split"
    description = "Modify high-frequency detail only — signature feels embedded in the image."
    category = "integrated"

    def apply(self, image, mask, params):
        blur_radius = params.get("blur_radius", 10)
        high_freq_boost = params.get("high_freq_boost", 2.0)
        invert_detail = params.get("invert_detail", False)

        rgb = image[:, :, :3]
        has_alpha = image.shape[2] == 4

        # Compute low-frequency layer (Gaussian blur)
        ksize = int(blur_radius * 2) | 1
        ksize = max(ksize, 3)
        low_freq = cv2.GaussianBlur(rgb, (ksize, ksize), blur_radius)

        # High-frequency = original - low_frequency
        high_freq = rgb - low_freq

        # Modify high-frequency detail
        if invert_detail:
            modified_high = -high_freq * high_freq_boost
        else:
            modified_high = high_freq * high_freq_boost

        # Recombine
        result = low_freq + modified_high
        result = np.clip(result, 0, 1)

        if has_alpha:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"blur_radius": 10, "high_freq_boost": 2.0, "invert_detail": False}


EFFECT = FrequencySplitEffect()
