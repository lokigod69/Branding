"""
film_grain.py — Resolution-Aware Film Grain

Adds photographic film grain that scales correctly between proxy and full-res.
The grain character responds to image tonality (more in mids, subtler in
shadows/highlights) to mimic real photochemical behavior.

Key design: grain size is specified in "output pixels" and scaled by the ratio
of current image size to target_resolution so preview grain matches export.
"""

import numpy as np
import cv2
from engine.filters.base import BaseFilter


class FilmGrainFilter(BaseFilter):
    name = "Film Grain"
    description = "Photographic film grain with tonal response and chroma variation"
    family = "surface"
    category = "texture"
    pre_upscale_safe = False  # Grain added after upscale looks wrong

    def apply(self, image, params, target_resolution=None):
        amount = params.get("amount", 0.08)
        size = params.get("size", 1.5)
        roughness = params.get("roughness", 0.6)
        chroma_amount = params.get("chroma_amount", 0.3)
        tonal_response = params.get("tonal_response", 0.7)
        seed = params.get("seed", 42)

        if amount <= 0:
            return image

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)

        # Resolution scale: grain size in output pixels, scaled to current res
        res_scale = 1.0
        if target_resolution is not None:
            target_w, target_h = target_resolution
            res_scale = w / max(target_w, 1)

        effective_size = max(size * res_scale, 1.0)

        # Generate base grain at potentially lower resolution then upscale
        if effective_size > 1.5:
            grain_w = max(int(w / effective_size), 16)
            grain_h = max(int(h / effective_size), 16)
            small_grain = rng.standard_normal((grain_h, grain_w)).astype(np.float32)
            # Roughness controls how much the grain is smoothed
            if roughness < 0.9:
                ksize = int((1.0 - roughness) * 4) | 1
                ksize = max(ksize, 3)
                small_grain = cv2.GaussianBlur(small_grain, (ksize, ksize), 0)
            # Upscale to image size
            luma_grain = cv2.resize(small_grain, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            luma_grain = rng.standard_normal((h, w)).astype(np.float32)
            if roughness < 0.9:
                ksize = int((1.0 - roughness) * 4) | 1
                ksize = max(ksize, 3)
                luma_grain = cv2.GaussianBlur(luma_grain, (ksize, ksize), 0)

        # Tonal response: real film grain is more visible in mid-tones
        if tonal_response > 0:
            luma = 0.2126 * image[:, :, 0] + 0.7152 * image[:, :, 1] + 0.0722 * image[:, :, 2]
            # Bell curve centered at 0.5 — grain strongest in mids
            tonal_weight = np.exp(-((luma - 0.5) ** 2) / (0.18 * (1.0 + tonal_response)))
            # Blend between flat response and tonal response
            grain_weight = (1.0 - tonal_response) + tonal_response * tonal_weight
            luma_grain = luma_grain * grain_weight

        # Apply luminance grain
        result = image.copy()
        result[:, :, 0] += luma_grain * amount
        result[:, :, 1] += luma_grain * amount
        result[:, :, 2] += luma_grain * amount

        # Chroma grain: separate noise per channel (subtle color shifts)
        if chroma_amount > 0:
            chroma_strength = amount * chroma_amount * 0.5
            for c in range(min(3, image.shape[2])):
                ch_grain = rng.standard_normal((h, w)).astype(np.float32)
                if effective_size > 1.5:
                    ch_small = cv2.resize(
                        rng.standard_normal((grain_h, grain_w)).astype(np.float32),
                        (w, h), interpolation=cv2.INTER_LINEAR,
                    )
                    ch_grain = ch_small
                result[:, :, c] += ch_grain * chroma_strength

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "amount": 0.08,
            "size": 1.5,
            "roughness": 0.6,
            "chroma_amount": 0.3,
            "tonal_response": 0.7,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "amount", "label": "Amount", "type": "slider", "min": 0, "max": 0.3, "step": 0.005, "default": 0.08},
            {"key": "size", "label": "Size", "type": "slider", "min": 0.5, "max": 5.0, "step": 0.1, "default": 1.5},
            {"key": "roughness", "label": "Roughness", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.6},
            {"key": "chroma_amount", "label": "Chroma", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "tonal_response", "label": "Tonal Response", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.7},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = FilmGrainFilter()
