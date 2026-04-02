"""
edge_deperfection.py — Edge De-Perfection

AI generators produce unnaturally perfect, razor-clean edges. This filter
introduces subtle organic irregularity along edges to make them feel
hand-made or photographed — micro-wobble, soft aliasing variation,
and controlled edge roughness.

The filter identifies edge regions via gradient magnitude and applies
localized, low-frequency displacement noise to shift edge pixels slightly.
"""

import numpy as np
import cv2
from engine.filters.base import BaseFilter


class EdgeDeperfectionFilter(BaseFilter):
    name = "Edge De-perfection"
    description = "Break AI-perfect edges with subtle organic irregularity"
    family = "surface"
    category = "detail"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        radius = params.get("radius", 1.5)
        strength = params.get("strength", 0.5)
        protect_detail = params.get("protect_detail", 0.6)
        halo_reduction = params.get("halo_reduction", 0.5)
        seed = params.get("seed", 42)

        if strength <= 0:
            return image

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)

        # Step 1: Detect edges
        gray = np.mean(image[:, :, :3], axis=2).astype(np.float32)
        ksize = max(int(radius * 2) | 1, 3)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=min(ksize, 7))
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=min(ksize, 7))
        edge_mag = np.sqrt(gx * gx + gy * gy)

        # Normalize
        edge_max = edge_mag.max()
        if edge_max <= 0:
            return image
        edge_mag /= edge_max

        # Create edge mask — where we'll apply the effect
        edge_threshold = 0.05 + protect_detail * 0.2
        edge_mask = np.clip((edge_mag - edge_threshold * 0.5) / max(edge_threshold, 1e-6), 0.0, 1.0)

        # Detail protection: suppress very fine detail edges
        if protect_detail > 0:
            # Blur the mask to avoid hitting tiny details
            blur_k = max(int(protect_detail * 6) | 1, 3)
            edge_mask = cv2.GaussianBlur(edge_mask, (blur_k, blur_k), protect_detail * 2)

        # Step 2: Generate displacement noise
        # Low-frequency noise for organic wobble (not per-pixel jitter)
        disp_scale = max(int(radius * 8), 8)
        noise_w = max(w // disp_scale, 4)
        noise_h = max(h // disp_scale, 4)
        dx_small = rng.standard_normal((noise_h, noise_w)).astype(np.float32)
        dy_small = rng.standard_normal((noise_h, noise_w)).astype(np.float32)

        # Smooth for coherent flow
        dx_small = cv2.GaussianBlur(dx_small, (3, 3), 1.0)
        dy_small = cv2.GaussianBlur(dy_small, (3, 3), 1.0)

        # Upscale to image size
        dx = cv2.resize(dx_small, (w, h), interpolation=cv2.INTER_CUBIC)
        dy = cv2.resize(dy_small, (w, h), interpolation=cv2.INTER_CUBIC)

        # Scale displacement by strength and mask (only at edges)
        disp_amount = strength * radius
        dx = dx * disp_amount * edge_mask
        dy = dy * disp_amount * edge_mask

        # Step 3: Apply displacement via remap
        map_x = np.arange(w, dtype=np.float32)[np.newaxis, :].repeat(h, axis=0)
        map_y = np.arange(h, dtype=np.float32)[:, np.newaxis].repeat(w, axis=1)
        map_x = map_x + dx
        map_y = map_y + dy

        result = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REFLECT_101)

        # Step 4: Halo reduction — blend back original in non-edge areas
        # to prevent remap artifacts from spreading into flat zones
        if halo_reduction > 0:
            anti_halo = 1.0 - edge_mask * (1.0 - halo_reduction)
            anti_halo_3 = anti_halo[:, :, np.newaxis]
            result = result * (1.0 - anti_halo_3) + image * anti_halo_3
            # Actually — invert: we want to keep result at edges, original away from edges
            result = image * (1.0 - edge_mask[:, :, np.newaxis]) + result * edge_mask[:, :, np.newaxis]

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "radius": 1.5,
            "strength": 0.5,
            "protect_detail": 0.6,
            "halo_reduction": 0.5,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "strength", "label": "Strength", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "radius", "label": "Radius", "type": "slider", "min": 0.5, "max": 5.0, "step": 0.25, "default": 1.5},
            {"key": "protect_detail", "label": "Detail Protection", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.6},
            {"key": "halo_reduction", "label": "Halo Reduction", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = EdgeDeperfectionFilter()
