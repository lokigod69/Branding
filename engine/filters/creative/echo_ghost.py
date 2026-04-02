"""
echo_ghost.py — Echo / Ghost Displacement

Creates ghostly echoes of regions — duplicated fragments with offset,
opacity falloff, and optional color desaturation. Produces a haunting,
layered look where parts of the image appear to haunt other parts.
"""
import numpy as np
import cv2
from engine.filters.base import BaseFilter
from engine.regions.base import RegionGeneratorRegistry


class EchoGhostFilter(BaseFilter):
    name = "Echo Ghost"
    description = "Ghostly displaced echoes of image regions"
    family = "creative"
    category = "displacement"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        region_type = params.get("region_type", "voronoi")
        n_echoes = max(params.get("echoes", 3), 1)
        displacement = params.get("displacement", 0.05)
        fade = params.get("fade", 0.5)
        desaturate = params.get("desaturate", 0.3)
        seed = params.get("seed", 42)

        gen = RegionGeneratorRegistry.get(region_type)
        if gen is None:
            return image

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)
        region_map = gen.generate(w, h, params)
        result = image.copy()

        max_dx = int(displacement * w)
        max_dy = int(displacement * h)

        for echo_i in range(n_echoes):
            # Pick a random region to echo
            src_id = int(rng.integers(0, region_map.n_regions))
            mask = (region_map.labels == src_id).astype(np.float32)
            if mask.sum() < 4:
                continue

            # Random displacement per echo
            dx = int(rng.integers(-max_dx, max_dx + 1))
            dy = int(rng.integers(-max_dy, max_dy + 1))

            # Extract and shift the region content
            rows, cols = np.where(mask > 0)
            new_rows = np.clip(rows + dy, 0, h - 1)
            new_cols = np.clip(cols + dx, 0, w - 1)

            # Ghost opacity decays with echo index
            opacity = fade * (1.0 / (echo_i + 1))

            # Optionally desaturate the echo
            ghost_pixels = image[rows, cols].copy()
            if desaturate > 0 and ghost_pixels.shape[1] >= 3:
                gray_val = np.mean(ghost_pixels[:, :3], axis=1, keepdims=True)
                gray_3 = np.repeat(gray_val, 3, axis=1)
                ghost_pixels[:, :3] = ghost_pixels[:, :3] * (1 - desaturate) + gray_3 * desaturate

            # Blend ghost into result
            result[new_rows, new_cols] = (
                result[new_rows, new_cols] * (1 - opacity) +
                ghost_pixels * opacity
            )

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "region_type": "voronoi",
            "echoes": 3,
            "displacement": 0.05,
            "fade": 0.5,
            "desaturate": 0.3,
            "n_cells": 12,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "region_type", "label": "Region Type", "type": "select",
             "options": ["grid", "golden_ratio", "voronoi", "random_rects", "radial"],
             "default": "voronoi"},
            {"key": "echoes", "label": "Echoes", "type": "slider", "min": 1, "max": 8, "step": 1, "default": 3},
            {"key": "displacement", "label": "Displacement", "type": "slider", "min": 0.01, "max": 0.2, "step": 0.01, "default": 0.05},
            {"key": "fade", "label": "Fade", "type": "slider", "min": 0.1, "max": 1.0, "step": 0.05, "default": 0.5},
            {"key": "desaturate", "label": "Desaturate", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "n_cells", "label": "Cells (Voronoi)", "type": "slider", "min": 3, "max": 40, "step": 1, "default": 12},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = EchoGhostFilter()
