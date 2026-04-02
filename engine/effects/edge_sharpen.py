"""
edge_sharpen.py — Edge-Aware Sharpen Effect

Sharpens along detected edges inside the mask for an etched/engraved look.
Uses Sobel edge detection combined with unsharp masking.
"""

import numpy as np
import cv2
from engine.effects.base import BaseEffect


class EdgeSharpenEffect(BaseEffect):
    name = "Edge Sharpen"
    description = "Edge-aware sharpening — etched/engraved look."
    category = "branding"

    def apply(self, image, mask, params):
        sharpen_amount = params.get("sharpen_amount", 2.0)
        edge_threshold = params.get("edge_threshold", 0.1)

        rgb = image[:, :, :3]
        has_alpha = image.shape[2] == 4

        # Convert to grayscale for edge detection
        gray = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])
        gray_uint8 = (np.clip(gray, 0, 1) * 255).astype(np.uint8)

        # Sobel edge detection
        sobelx = cv2.Sobel(gray_uint8, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray_uint8, cv2.CV_64F, 0, 1, ksize=3)
        edge_magnitude = np.sqrt(sobelx ** 2 + sobely ** 2)
        edge_magnitude = edge_magnitude / (edge_magnitude.max() + 1e-6)

        # Edge mask: only sharpen where there are edges
        edge_mask = np.clip(edge_magnitude / (edge_threshold + 1e-6), 0, 1).astype(np.float32)

        # Unsharp mask for sharpening
        blurred = cv2.GaussianBlur(rgb, (3, 3), 1.0)
        sharpened = rgb + sharpen_amount * (rgb - blurred)

        # Blend: sharpen only at edges
        edge_mask_3ch = edge_mask[:, :, np.newaxis]
        result = rgb * (1 - edge_mask_3ch) + sharpened * edge_mask_3ch

        result = np.clip(result, 0, 1)

        if has_alpha:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)

        return result

    def get_default_params(self):
        return {"sharpen_amount": 2.0, "edge_threshold": 0.1}


EFFECT = EdgeSharpenEffect()
