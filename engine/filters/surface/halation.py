"""
halation.py — Halation / Bloom

Simulates light bleeding outward from bright areas, as happens in real
film and lens systems. The effect is physically motivated: bright highlights
scatter through the film base or lens elements, creating a soft colored
glow that spills into adjacent darker areas.

The bias control lets the user shift the bloom color from warm (film halation,
reddish) to neutral (lens bloom, white).
"""

import numpy as np
import cv2
from engine.filters.base import BaseFilter


class HalationFilter(BaseFilter):
    name = "Halation / Bloom"
    description = "Light bleed from highlights — warm film halation or cool lens bloom"
    family = "surface"
    category = "optical"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        radius = params.get("radius", 30.0)
        threshold = params.get("threshold", 0.7)
        amount = params.get("amount", 0.3)
        halation_bias = params.get("halation_bias", 0.5)
        shadow_safe = params.get("shadow_safe", 0.6)

        if amount <= 0:
            return image

        h, w = image.shape[:2]

        # Step 1: Extract bright areas above threshold
        luma = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]
        bright_mask = np.clip((luma - threshold) / (1.0 - threshold + 1e-6), 0.0, 1.0)

        # Create the bloom source — bright pixels only
        bloom_source = image.copy()
        for c in range(min(3, image.shape[2])):
            bloom_source[:, :, c] *= bright_mask

        # Step 2: Blur heavily to create glow
        blur_radius = max(int(radius * 2) | 1, 3)
        # Two-pass blur for smoother, wider glow
        bloom = cv2.GaussianBlur(bloom_source, (blur_radius, blur_radius), radius * 0.35)
        # Second pass at larger radius
        bloom2_radius = max(blur_radius * 2 | 1, 5)
        bloom2 = cv2.GaussianBlur(bloom_source, (bloom2_radius, bloom2_radius), radius * 0.8)
        bloom = bloom * 0.6 + bloom2 * 0.4

        # Step 3: Apply halation color bias
        # bias=0: neutral white bloom, bias=1: warm reddish film halation
        if halation_bias > 0 and bloom.shape[2] >= 3:
            # Shift toward warm (boost red, reduce blue slightly)
            bloom[:, :, 0] *= 1.0 + halation_bias * 0.35  # Red boost
            bloom[:, :, 1] *= 1.0 + halation_bias * 0.05  # Very slight green
            bloom[:, :, 2] *= 1.0 - halation_bias * 0.2   # Blue reduction

        # Step 4: Shadow protection — don't add bloom into deep shadows
        if shadow_safe > 0:
            shadow_threshold = 0.15 + shadow_safe * 0.1
            shadow_mask = np.clip(luma / shadow_threshold, 0.0, 1.0)
            shadow_mask_3 = shadow_mask[:, :, np.newaxis]
            bloom = bloom * shadow_mask_3

        # Step 5: Composite — screen blend for natural light addition
        # Screen: result = 1 - (1-image) * (1-bloom*amount)
        bloom_scaled = bloom * amount
        result = 1.0 - (1.0 - image) * (1.0 - bloom_scaled)

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "radius": 30.0,
            "threshold": 0.7,
            "amount": 0.3,
            "halation_bias": 0.5,
            "shadow_safe": 0.6,
        }

    def get_param_schema(self):
        return [
            {"key": "amount", "label": "Amount", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "radius", "label": "Radius", "type": "slider", "min": 5, "max": 120, "step": 1, "default": 30},
            {"key": "threshold", "label": "Threshold", "type": "slider", "min": 0.3, "max": 0.95, "step": 0.05, "default": 0.7},
            {"key": "halation_bias", "label": "Warmth", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "shadow_safe", "label": "Shadow Protection", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.6},
        ]


FILTER = HalationFilter()
