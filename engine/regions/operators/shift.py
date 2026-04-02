"""Shift operator — displaces each region by a random offset."""
import numpy as np
from engine.regions.base import RegionOperator, RegionMap


class ShiftOperator(RegionOperator):
    name = "Shift"
    description = "Displace each region by a random offset"

    def operate(self, image, region_map, params):
        result = image.copy()
        n = region_map.n_regions
        seed = params.get("seed", 42)
        max_shift = params.get("max_shift", 0.05)
        rng = np.random.default_rng(seed)

        h, w = image.shape[:2]
        max_dx = int(max_shift * w)
        max_dy = int(max_shift * h)

        for rid in range(n):
            mask = region_map.labels == rid
            if not mask.any():
                continue

            dx = int(rng.integers(-max_dx, max_dx + 1))
            dy = int(rng.integers(-max_dy, max_dy + 1))

            if dx == 0 and dy == 0:
                continue

            rows, cols = np.where(mask)
            new_rows = np.clip(rows + dy, 0, h - 1)
            new_cols = np.clip(cols + dx, 0, w - 1)
            result[new_rows, new_cols] = image[rows, cols]

        return np.clip(result, 0.0, 1.0)


OPERATOR = ShiftOperator()
