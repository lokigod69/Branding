"""Swap operator — trades pixel content between pairs of regions."""
import numpy as np
from engine.regions.base import RegionOperator, RegionMap


class SwapOperator(RegionOperator):
    name = "Swap"
    description = "Exchange pixel content between region pairs"

    def operate(self, image, region_map, params):
        result = image.copy()
        n = region_map.n_regions
        seed = params.get("seed", 42)
        rng = np.random.default_rng(seed)

        # Build swap pairs: shuffle region IDs, pair consecutive
        ids = list(range(n))
        rng.shuffle(ids)
        pairs = [(ids[i], ids[i + 1]) for i in range(0, len(ids) - 1, 2)]

        for a, b in pairs:
            mask_a = region_map.labels == a
            mask_b = region_map.labels == b

            # Only swap if both regions have pixels
            if not mask_a.any() or not mask_b.any():
                continue

            # Find bounding boxes for efficient copy
            rows_a, cols_a = np.where(mask_a)
            rows_b, cols_b = np.where(mask_b)

            # Store region A content
            temp = result[mask_a].copy()

            # Assign B's mean-shifted content to A's positions, and vice versa
            a_pixels = result[mask_a].copy()
            b_pixels = result[mask_b].copy()

            # Simple replacement: sample from b to fill a (with wrapping)
            if len(a_pixels) <= len(b_pixels):
                result[mask_a] = b_pixels[:len(a_pixels)]
            else:
                repeats = len(a_pixels) // len(b_pixels) + 1
                result[mask_a] = np.tile(b_pixels, (repeats, 1))[:len(a_pixels)]

            if len(b_pixels) <= len(a_pixels):
                result[mask_b] = a_pixels[:len(b_pixels)]
            else:
                repeats = len(b_pixels) // len(a_pixels) + 1
                result[mask_b] = np.tile(a_pixels, (repeats, 1))[:len(b_pixels)]

        return np.clip(result, 0.0, 1.0)


OPERATOR = SwapOperator()
