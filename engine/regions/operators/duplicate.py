"""Duplicate operator — copies one region's content into another with optional falloff."""
import numpy as np
import cv2
from engine.regions.base import RegionOperator, RegionMap


class DuplicateOperator(RegionOperator):
    name = "Duplicate"
    description = "Copy one region's texture into another with edge falloff"

    def operate(self, image, region_map, params):
        result = image.copy()
        n = region_map.n_regions
        seed = params.get("seed", 42)
        falloff = params.get("falloff", 0.3)
        rng = np.random.default_rng(seed)

        if n < 2:
            return result

        # Pick source and target regions
        ids = list(range(n))
        rng.shuffle(ids)
        source_id = ids[0]
        target_ids = ids[1:min(len(ids), 3)]  # Duplicate into up to 2 targets

        source_mask = (region_map.labels == source_id).astype(np.float32)
        if source_mask.sum() < 4:
            return result

        # Get source bounding box and content
        rows, cols = np.where(source_mask > 0)
        sy0, sy1 = rows.min(), rows.max() + 1
        sx0, sx1 = cols.min(), cols.max() + 1
        source_patch = image[sy0:sy1, sx0:sx1].copy()
        source_mask_patch = source_mask[sy0:sy1, sx0:sx1]

        for tid in target_ids:
            target_mask = (region_map.labels == tid).astype(np.float32)
            if target_mask.sum() < 4:
                continue

            tr, tc = np.where(target_mask > 0)
            ty0, ty1 = tr.min(), tr.max() + 1
            tx0, tx1 = tc.min(), tc.max() + 1
            th, tw = ty1 - ty0, tx1 - tx0

            # Resize source to fit target region
            resized_patch = cv2.resize(source_patch, (tw, th), interpolation=cv2.INTER_LINEAR)

            # Create falloff mask
            target_submask = target_mask[ty0:ty1, tx0:tx1]
            if falloff > 0:
                blur_k = max(int(falloff * min(th, tw) * 0.3) | 1, 3)
                target_submask = cv2.GaussianBlur(target_submask, (blur_k, blur_k), 0)

            mask_3 = target_submask[:, :, np.newaxis]
            result[ty0:ty1, tx0:tx1] = (
                result[ty0:ty1, tx0:tx1] * (1.0 - mask_3) + resized_patch * mask_3
            )

        return np.clip(result, 0.0, 1.0)


OPERATOR = DuplicateOperator()
