"""
scan_residue.py — Scan / Compression Residue

Simulates the artifacts left by physical scanning or heavy compression:
  - Scan lines (periodic horizontal banding)
  - JPEG-like block artifacts (8×8 grid quantization)
  - Color bleeding from scanner CCD misalignment
  - Noise floor from scanner electronics

Together these make the image feel like a found scan or a
twice-compressed artifact — the digital patina of degradation.
"""
import numpy as np
import cv2
from engine.filters.base import BaseFilter


class ScanResidueFilter(BaseFilter):
    name = "Scan Residue"
    description = "Scan lines, block artifacts, color bleed — digital patina"
    family = "finish"
    category = "degradation"
    pre_upscale_safe = False

    def apply(self, image, params, target_resolution=None):
        scanlines = params.get("scanlines", 0.3)
        block_artifacts = params.get("block_artifacts", 0.2)
        color_bleed = params.get("color_bleed", 0.15)
        noise_floor = params.get("noise_floor", 0.1)
        seed = params.get("seed", 42)

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)
        result = image.copy()

        # ─── Scan Lines ──────────────────────────────────
        if scanlines > 0:
            # Periodic horizontal brightness modulation
            line_period = max(int(h / 200), 2)
            yy = np.arange(h, dtype=np.float32)
            line_pattern = np.sin(yy * np.pi / line_period) * 0.5 + 0.5
            # Sharpen the pattern for defined lines
            line_pattern = np.power(line_pattern, 3.0)
            line_mod = 1.0 - line_pattern * scanlines * 0.08
            result = result * line_mod[:, np.newaxis, np.newaxis]

        # ─── Block Artifacts (JPEG-style) ─────────────────
        if block_artifacts > 0:
            block_size = 8
            # Quantize by downsampling and upsampling each block
            small_h = max(h // block_size, 1)
            small_w = max(w // block_size, 1)
            blocky = cv2.resize(
                cv2.resize(result, (small_w, small_h), interpolation=cv2.INTER_AREA),
                (w, h), interpolation=cv2.INTER_NEAREST,
            )

            # Add block grid edges
            grid_mask = np.zeros((h, w), dtype=np.float32)
            grid_mask[::block_size, :] = 1.0
            grid_mask[:, ::block_size] = 1.0
            grid_mask = cv2.GaussianBlur(grid_mask, (3, 3), 0.5) * 0.3

            edge_darken = grid_mask[:, :, np.newaxis] * block_artifacts * 0.05
            result = result * (1 - block_artifacts * 0.5) + blocky * (block_artifacts * 0.5)
            result = result - edge_darken

        # ─── Color Bleed ─────────────────────────────────
        if color_bleed > 0 and result.shape[2] >= 3:
            # Shift each channel slightly in different directions
            shift_px = max(int(color_bleed * 3), 1)
            for c, (dx, dy) in enumerate([(shift_px, 0), (0, 0), (0, shift_px)]):
                if dx == 0 and dy == 0:
                    continue
                M = np.float32([[1, 0, dx], [0, 1, dy]])
                shifted = cv2.warpAffine(
                    result[:, :, c], M, (w, h),
                    borderMode=cv2.BORDER_REFLECT_101,
                )
                result[:, :, c] = result[:, :, c] * (1 - color_bleed * 0.3) + shifted * (color_bleed * 0.3)

        # ─── Noise Floor ─────────────────────────────────
        if noise_floor > 0:
            noise = rng.standard_normal((h, w)).astype(np.float32) * noise_floor * 0.015
            result = result + noise[:, :, np.newaxis]

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "scanlines": 0.3,
            "block_artifacts": 0.2,
            "color_bleed": 0.15,
            "noise_floor": 0.1,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "scanlines", "label": "Scan Lines", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "block_artifacts", "label": "Block Artifacts", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.2},
            {"key": "color_bleed", "label": "Color Bleed", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.15},
            {"key": "noise_floor", "label": "Noise Floor", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.1},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = ScanResidueFilter()
