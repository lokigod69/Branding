"""
region_contaminate.py — Region Contamination

Uses the region system to bleed texture from one area of the image into
adjacent areas. The effect is like ink bleeding through paper, or one
material's surface contaminating another — "borrowed skin."
"""
import numpy as np
from engine.filters.base import BaseFilter
from engine.regions.base import RegionGeneratorRegistry, RegionOperatorRegistry


class RegionContaminateFilter(BaseFilter):
    name = "Region Contaminate"
    description = "Bleed texture between adjacent regions — borrowed skin"
    family = "creative"
    category = "region"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        region_type = params.get("region_type", "voronoi")
        spread = params.get("spread", 10)
        strength = params.get("strength", 0.5)
        seed = params.get("seed", 42)
        passes = max(params.get("passes", 1), 1)

        gen = RegionGeneratorRegistry.get(region_type)
        if gen is None:
            return image

        h, w = image.shape[:2]
        region_map = gen.generate(w, h, params)

        op = RegionOperatorRegistry.get("contaminate")
        if op is None:
            return image

        result = image.copy()
        for p in range(passes):
            result = op.operate(result, region_map, {
                "seed": seed + p,
                "spread": spread,
                "strength": strength / passes,
            })

        return result

    def get_default_params(self):
        return {
            "region_type": "voronoi",
            "spread": 10,
            "strength": 0.5,
            "passes": 1,
            "n_cells": 12,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "region_type", "label": "Region Type", "type": "select",
             "options": ["grid", "golden_ratio", "voronoi", "random_rects", "radial"],
             "default": "voronoi"},
            {"key": "spread", "label": "Spread", "type": "slider", "min": 3, "max": 50, "step": 1, "default": 10},
            {"key": "strength", "label": "Strength", "type": "slider", "min": 0.1, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "passes", "label": "Passes", "type": "slider", "min": 1, "max": 5, "step": 1, "default": 1},
            {"key": "n_cells", "label": "Cells (Voronoi)", "type": "slider", "min": 3, "max": 40, "step": 1, "default": 12},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = RegionContaminateFilter()
