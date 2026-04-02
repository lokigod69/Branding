"""Blur operator — selectively blurs regions at different strengths."""
import numpy as np
import cv2
from engine.regions.base import RegionOperator, RegionMap


class BlurOperator(RegionOperator):
    name = "Blur"
    description = "Selectively blur specific regions"

    def operate(self, image, region_map, params):
        result = image.copy()
        n = region_map.n_regions
        seed = params.get("seed", 42)
        base_radius = params.get("radius", 15)
        fraction = params.get("fraction", 0.5)  # What fraction of regions get blurred
        rng = np.random.default_rng(seed)

        # Pick which regions to blur
        ids = list(range(n))
        rng.shuffle(ids)
        n_blur = max(1, int(len(ids) * fraction))
        blur_ids = set(ids[:n_blur])

        for rid in blur_ids:
            mask = (region_map.labels == rid).astype(np.float32)
            if mask.sum() < 4:
                continue

            # Vary blur radius per region for organic feel
            radius = max(int(base_radius * rng.uniform(0.5, 1.5)) | 1, 3)
            blurred = cv2.GaussianBlur(image, (radius, radius), 0)

            # Soft mask edge
            soft_mask = cv2.GaussianBlur(mask, (7, 7), 2.0)
            mask_3 = soft_mask[:, :, np.newaxis]
            result = result * (1.0 - mask_3) + blurred * mask_3

        return np.clip(result, 0.0, 1.0)


OPERATOR = BlurOperator()
