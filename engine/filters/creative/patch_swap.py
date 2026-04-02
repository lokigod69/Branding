"""
patch_swap.py — Patch/Quadrant Swap

Partitions the image using a chosen region generator, then swaps pixel
content between randomly paired regions. The result is a glitchy,
collage-like rearrangement that can range from subtle to dramatic.
"""
import numpy as np
from engine.filters.base import BaseFilter
from engine.regions.base import RegionGeneratorRegistry, RegionOperatorRegistry


class PatchSwapFilter(BaseFilter):
    name = "Patch Swap"
    description = "Swap pixel content between region pairs — glitchy collage"
    family = "creative"
    category = "region"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        region_type = params.get("region_type", "golden_ratio")
        seed = params.get("seed", 42)

        gen = RegionGeneratorRegistry.get(region_type)
        if gen is None:
            gen = RegionGeneratorRegistry.get("grid")
        if gen is None:
            return image

        h, w = image.shape[:2]
        region_map = gen.generate(w, h, params)

        op = RegionOperatorRegistry.get("swap")
        if op is None:
            return image

        return op.operate(image, region_map, {"seed": seed})

    def get_default_params(self):
        return {
            "region_type": "golden_ratio",
            "depth": 4,
            "cols": 4,
            "rows": 4,
            "n_cells": 12,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "region_type", "label": "Region Type", "type": "select",
             "options": ["grid", "golden_ratio", "voronoi", "random_rects", "radial"],
             "default": "golden_ratio"},
            {"key": "depth", "label": "Depth (Golden)", "type": "slider", "min": 2, "max": 8, "step": 1, "default": 4},
            {"key": "cols", "label": "Columns (Grid)", "type": "slider", "min": 2, "max": 12, "step": 1, "default": 4},
            {"key": "rows", "label": "Rows (Grid)", "type": "slider", "min": 2, "max": 12, "step": 1, "default": 4},
            {"key": "n_cells", "label": "Cells (Voronoi)", "type": "slider", "min": 3, "max": 40, "step": 1, "default": 12},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = PatchSwapFilter()
