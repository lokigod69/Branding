"""
dither.py — Dither / Tonal Breakup

Simulates the tonal quantization and pattern-based dithering found in
printed materials, risograph art, and retro digital output. Breaks smooth
gradients into visible tonal steps with optional noise modulation.

Three dither modes:
  - Noise dither (random threshold perturbation)
  - Ordered dither (Bayer matrix pattern)
  - Halftone dots (simulated halftone screen)
"""
import numpy as np
import cv2
from engine.filters.base import BaseFilter


class DitherFilter(BaseFilter):
    name = "Dither / Tonal Breakup"
    description = "Quantized tones — noise dither, ordered Bayer, or halftone dots"
    family = "finish"
    category = "material"
    pre_upscale_safe = False

    def apply(self, image, params, target_resolution=None):
        levels = max(params.get("levels", 8), 2)
        amount = params.get("amount", 0.5)
        dither_mode = params.get("dither_mode", "noise")
        dot_size = max(params.get("dot_size", 4), 2)
        seed = params.get("seed", 42)

        if amount <= 0:
            return image

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)

        result = image.copy()

        for c in range(min(3, image.shape[2])):
            channel = image[:, :, c].copy()

            if dither_mode == "noise":
                # Random threshold dithering
                noise = rng.uniform(-0.5, 0.5, (h, w)).astype(np.float32) / levels
                channel = channel + noise

            elif dither_mode == "ordered":
                # Bayer 4x4 ordered dither matrix
                bayer_4 = np.array([
                    [ 0,  8,  2, 10],
                    [12,  4, 14,  6],
                    [ 3, 11,  1,  9],
                    [15,  7, 13,  5],
                ], dtype=np.float32) / 16.0 - 0.5

                # Tile to image size
                tile_h = (h + 3) // 4
                tile_w = (w + 3) // 4
                threshold = np.tile(bayer_4, (tile_h, tile_w))[:h, :w]
                channel = channel + threshold / levels

            elif dither_mode == "halftone":
                # Simulated halftone dots
                cell_h = max(dot_size, 2)
                cell_w = max(dot_size, 2)
                n_cells_y = (h + cell_h - 1) // cell_h
                n_cells_x = (w + cell_w - 1) // cell_w

                # Create distance-from-center pattern for each cell
                cy, cx = np.mgrid[0:cell_h, 0:cell_w]
                center = np.sqrt(
                    ((cx - cell_w / 2) / (cell_w / 2)) ** 2 +
                    ((cy - cell_h / 2) / (cell_h / 2)) ** 2
                ).astype(np.float32)
                center = center / center.max()

                # Tile pattern
                pattern = np.tile(center, (n_cells_y, n_cells_x))[:h, :w]

                # Threshold: pixels brighter than pattern dot = white, else black
                quantized = np.floor(channel * levels) / levels
                dot_threshold = (channel - quantized) * levels
                channel = np.where(dot_threshold > pattern, quantized + 1.0 / levels, quantized)

            # Quantize to N levels
            quantized = np.round(channel * (levels - 1)) / (levels - 1)

            # Blend original with dithered
            result[:, :, c] = image[:, :, c] * (1 - amount) + quantized * amount

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "levels": 8,
            "amount": 0.5,
            "dither_mode": "noise",
            "dot_size": 4,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "amount", "label": "Amount", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "levels", "label": "Tonal Levels", "type": "slider", "min": 2, "max": 32, "step": 1, "default": 8},
            {"key": "dither_mode", "label": "Mode", "type": "select",
             "options": ["noise", "ordered", "halftone"], "default": "noise"},
            {"key": "dot_size", "label": "Dot Size (Halftone)", "type": "slider", "min": 2, "max": 16, "step": 1, "default": 4},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = DitherFilter()
