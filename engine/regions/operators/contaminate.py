"""Contaminate operator — bleeds texture from one region into adjacent regions."""
import numpy as np
import cv2
from engine.regions.base import RegionOperator, RegionMap


class ContaminateOperator(RegionOperator):
    name = "Contaminate"
    description = "Bleed texture from one region into adjacent regions"

    def operate(self, image, region_map, params):
        result = image.copy()
        n = region_map.n_regions
        seed = params.get("seed", 42)
        spread = params.get("spread", 10)
        strength = params.get("strength", 0.5)
        rng = np.random.default_rng(seed)

        if n < 2:
            return result

        # Pick source region
        source_id = int(rng.integers(0, n))
        source_mask = (region_map.labels == source_id).astype(np.float32)
        if source_mask.sum() < 4:
            return result

        # Dilate source mask to create contamination zone
        kernel_size = max(int(spread * 2) | 1, 3)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        dilated = cv2.dilate(source_mask, kernel, iterations=1)

        # Contamination zone is dilated minus original
        contam_zone = dilated - source_mask
        contam_zone = np.clip(contam_zone, 0.0, 1.0)

        # Smooth the contamination for natural bleed
        contam_zone = cv2.GaussianBlur(contam_zone, (kernel_size, kernel_size), spread * 0.3)

        # Heavily blur the source content to get its "texture essence"
        blur_k = max(int(spread * 3) | 1, 5)
        blurred_source = cv2.GaussianBlur(image, (blur_k, blur_k), spread * 0.5)

        # Blend into contamination zone
        mask_3 = (contam_zone * strength)[:, :, np.newaxis]
        result = result * (1.0 - mask_3) + blurred_source * mask_3

        return np.clip(result, 0.0, 1.0)


OPERATOR = ContaminateOperator()
