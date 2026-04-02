"""
microtexture.py — Microtexture Reconstruction

Injects subtle surface microstructure into flat/smooth areas where AI
generators produce an unnaturally clean, plastic look. This is the core
"deplasticizer" — it adds the tiny irregularities that make surfaces
feel real (skin pores, paper fiber, canvas weave, fabric grain).

The filter selectively targets flat areas (low local variance) and
avoids disrupting edges or detailed regions.
"""

import numpy as np
import cv2
from engine.filters.base import BaseFilter


class MicrotextureFilter(BaseFilter):
    name = "Microtexture"
    description = "Inject surface microdetail into flat/plastic areas"
    family = "surface"
    category = "detail"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        scale = params.get("scale", 1.0)
        contrast = params.get("contrast", 0.5)
        flat_sensitivity = params.get("flat_sensitivity", 0.7)
        edge_protection = params.get("edge_protection", 0.8)
        seed = params.get("seed", 42)

        if contrast <= 0:
            return image

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)

        # Step 1: Generate multi-octave procedural texture
        # Two octaves of noise at different scales for organic feel
        texture = np.zeros((h, w), dtype=np.float32)

        for octave, weight in [(scale, 0.7), (scale * 2.5, 0.3)]:
            noise_w = max(int(w / max(octave * 3, 1)), 8)
            noise_h = max(int(h / max(octave * 3, 1)), 8)
            raw = rng.standard_normal((noise_h, noise_w)).astype(np.float32)
            # Smooth for organic shapes
            ksize = max(int(octave) | 1, 3)
            raw = cv2.GaussianBlur(raw, (ksize, ksize), octave * 0.4)
            up = cv2.resize(raw, (w, h), interpolation=cv2.INTER_CUBIC)
            texture += up * weight

        # Normalize to [-1, 1]
        t_std = texture.std()
        if t_std > 0:
            texture = texture / (t_std * 3.0)
        texture = np.clip(texture, -1.0, 1.0)

        # Step 2: Compute flat-area mask (where texture should be applied)
        gray = np.mean(image[:, :, :3], axis=2).astype(np.float32)
        radius = max(int(scale * 3), 3)
        ksize_var = radius * 2 + 1
        local_mean = cv2.blur(gray, (ksize_var, ksize_var))
        local_sq = cv2.blur(gray * gray, (ksize_var, ksize_var))
        local_var = np.maximum(local_sq - local_mean * local_mean, 0.0)

        # Higher sensitivity = more area considered "flat"
        threshold = 0.001 + (1.0 - flat_sensitivity) * 0.015
        flat_mask = np.clip(1.0 - local_var / max(threshold, 1e-8), 0.0, 1.0)

        # Step 3: Edge protection — reduce texture near strong edges
        if edge_protection > 0:
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            edge_mag = np.sqrt(gx * gx + gy * gy)
            edge_max = edge_mag.max()
            if edge_max > 0:
                edge_mag /= edge_max
            edge_suppress = 1.0 - edge_mag * edge_protection
            flat_mask *= np.clip(edge_suppress, 0.0, 1.0)

        # Smooth the mask for natural transitions
        flat_mask = cv2.GaussianBlur(flat_mask, (11, 11), 3.0)

        # Step 4: Apply texture to image
        strength = contrast * 0.06  # Scale to subtle range
        texture_3ch = texture[:, :, np.newaxis] * strength
        mask_3ch = flat_mask[:, :, np.newaxis]

        result = image + texture_3ch * mask_3ch

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "scale": 1.0,
            "contrast": 0.5,
            "flat_sensitivity": 0.7,
            "edge_protection": 0.8,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "contrast", "label": "Contrast", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "scale", "label": "Scale", "type": "slider", "min": 0.3, "max": 4.0, "step": 0.1, "default": 1.0},
            {"key": "flat_sensitivity", "label": "Flat Area Sensitivity", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.7},
            {"key": "edge_protection", "label": "Edge Protection", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.8},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = MicrotextureFilter()
