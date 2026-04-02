"""
tonal_desanitize.py — Tonal Desanitizing

AI generators produce unnaturally clean tonal distributions:
  - Highlights clip perfectly at 1.0 (no analog rolloff)
  - Blacks are mathematically black (no noise floor)
  - Local contrast is uniformly smooth (no organic breakup)
  - Color channels track each other perfectly (no subtle imbalance)

This filter introduces the controlled irregularities that make tones
feel photographed rather than rendered:
  - Highlight rolloff (soft shoulder instead of hard clip)
  - Black floor (raise black point slightly, add shadow noise)
  - Local contrast breakup (localized micro-contrast variation)
  - Channel imbalance (subtle per-channel curve offsets)
"""

import numpy as np
import cv2
from engine.filters.base import BaseFilter


class TonalDesanitizeFilter(BaseFilter):
    name = "Tonal Desanitize"
    description = "Break sterile AI tones — rolloff, floor, contrast breakup, channel drift"
    family = "surface"
    category = "tone"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        highlight_rolloff = params.get("highlight_rolloff", 0.4)
        black_floor = params.get("black_floor", 0.3)
        contrast_breakup = params.get("contrast_breakup", 0.3)
        channel_imbalance = params.get("channel_imbalance", 0.15)
        seed = params.get("seed", 42)

        result = image.copy()
        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)

        # ─── Highlight Rolloff ─────────────────────────────
        # Replace hard clip at 1.0 with soft shoulder curve
        if highlight_rolloff > 0:
            threshold = 0.82 - highlight_rolloff * 0.15
            # Soft compression above threshold
            for c in range(min(3, result.shape[2])):
                ch = result[:, :, c]
                above = ch > threshold
                if above.any():
                    # Smooth sigmoid compression in highlight zone
                    overshoot = (ch[above] - threshold) / (1.0 - threshold + 1e-6)
                    compressed = threshold + (1.0 - threshold) * (1.0 - np.exp(-overshoot * (2.0 - highlight_rolloff)))
                    result[:, :, c][above] = compressed

        # ─── Black Floor ───────────────────────────────────
        # Raise blacks slightly and add shadow noise
        if black_floor > 0:
            floor_level = black_floor * 0.025
            result = result * (1.0 - floor_level) + floor_level

            # Add subtle noise to shadows
            shadow_threshold = 0.2
            luma = np.mean(result[:, :, :3], axis=2)
            shadow_mask = np.clip((shadow_threshold - luma) / shadow_threshold, 0.0, 1.0)
            shadow_noise = rng.standard_normal((h, w)).astype(np.float32) * 0.008 * black_floor
            shadow_noise = shadow_noise * shadow_mask
            for c in range(min(3, result.shape[2])):
                result[:, :, c] += shadow_noise

        # ─── Local Contrast Breakup ────────────────────────
        # Introduce localized micro-contrast variation
        if contrast_breakup > 0:
            gray = np.mean(result[:, :, :3], axis=2).astype(np.float32)

            # Generate low-frequency modulation map
            mod_w = max(w // 24, 4)
            mod_h = max(h // 24, 4)
            mod_noise = rng.standard_normal((mod_h, mod_w)).astype(np.float32)
            mod_noise = cv2.GaussianBlur(mod_noise, (3, 3), 1.0)
            mod_map = cv2.resize(mod_noise, (w, h), interpolation=cv2.INTER_CUBIC)

            # Normalize to [-1, 1]
            m_std = mod_map.std()
            if m_std > 0:
                mod_map = mod_map / (m_std * 2.5)
            mod_map = np.clip(mod_map, -1.0, 1.0)

            # Apply as local contrast shift
            contrast_amount = contrast_breakup * 0.04
            for c in range(min(3, result.shape[2])):
                local_mean = cv2.blur(result[:, :, c], (15, 15))
                deviation = result[:, :, c] - local_mean
                # Modulate local contrast
                result[:, :, c] = local_mean + deviation * (1.0 + mod_map * contrast_amount)

        # ─── Channel Imbalance ─────────────────────────────
        # Subtle per-channel curve offsets (color channels shouldn't track perfectly)
        if channel_imbalance > 0 and result.shape[2] >= 3:
            imb_amount = channel_imbalance * 0.012
            offsets = rng.standard_normal(3).astype(np.float32) * imb_amount
            # Apply as gentle gamma shifts per channel
            for c in range(3):
                gamma = 1.0 + offsets[c]
                gamma = max(gamma, 0.9)
                result[:, :, c] = np.power(np.clip(result[:, :, c], 1e-6, 1.0), gamma)

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "highlight_rolloff": 0.4,
            "black_floor": 0.3,
            "contrast_breakup": 0.3,
            "channel_imbalance": 0.15,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "highlight_rolloff", "label": "Highlight Rolloff", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.4},
            {"key": "black_floor", "label": "Black Floor", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "contrast_breakup", "label": "Contrast Breakup", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "channel_imbalance", "label": "Channel Drift", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.15},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = TonalDesanitizeFilter()
