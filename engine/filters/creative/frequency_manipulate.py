"""
frequency_manipulate.py — Frequency-Domain Manipulation

Decomposes the image into frequency bands using Gaussian pyramid or
DCT-like approach, manipulates individual bands (boost, attenuate,
shift, randomize), then recomposes. Creates effects ranging from
subtle detail emphasis to surreal frequency-shifted textures.
"""
import numpy as np
import cv2
from engine.filters.base import BaseFilter


class FrequencyManipulateFilter(BaseFilter):
    name = "Frequency Manipulate"
    description = "Decompose into frequency bands and manipulate — boost, suppress, shift"
    family = "creative"
    category = "frequency"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        n_bands = max(params.get("bands", 4), 2)
        low_boost = params.get("low_boost", 1.0)
        mid_boost = params.get("mid_boost", 1.0)
        high_boost = params.get("high_boost", 1.0)
        band_shuffle = params.get("band_shuffle", 0.0)
        seed = params.get("seed", 42)

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)

        # Process each channel independently
        result = np.zeros_like(image)
        for c in range(min(3, image.shape[2])):
            channel = image[:, :, c].astype(np.float32)
            result[:, :, c] = self._process_channel(
                channel, n_bands, low_boost, mid_boost, high_boost,
                band_shuffle, rng, h, w
            )

        # Copy alpha if present
        if image.shape[2] == 4:
            result[:, :, 3] = image[:, :, 3]

        return np.clip(result, 0.0, 1.0)

    def _process_channel(self, channel, n_bands, low_boost, mid_boost, high_boost,
                         band_shuffle, rng, h, w):
        """Decompose, modify, and recompose a single channel."""
        # Build Gaussian pyramid (progressively blurred versions)
        pyramid = [channel]
        current = channel
        for i in range(n_bands - 1):
            k = max(int(2 ** (i + 1) * 3) | 1, 3)
            k = min(k, min(h, w) | 1)
            blurred = cv2.GaussianBlur(current, (k, k), 2 ** i)
            pyramid.append(blurred)
            current = blurred

        # Extract frequency bands (Laplacian-like decomposition)
        bands = []
        for i in range(len(pyramid) - 1):
            band = pyramid[i] - pyramid[i + 1]
            bands.append(band)
        bands.append(pyramid[-1])  # Residual (lowest frequency)

        # Assign boost factors per band
        n = len(bands)
        boosts = np.ones(n, dtype=np.float32)
        if n >= 3:
            # Low bands (last entries), mid, high (first entries)
            third = max(n // 3, 1)
            boosts[:third] *= high_boost         # High freq
            boosts[third:2 * third] *= mid_boost  # Mid freq
            boosts[2 * third:] *= low_boost       # Low freq
        elif n == 2:
            boosts[0] *= high_boost
            boosts[1] *= low_boost

        # Band shuffle: randomly swap band amplitudes
        if band_shuffle > 0:
            for i in range(n):
                if rng.random() < band_shuffle:
                    j = int(rng.integers(0, n))
                    boosts[i], boosts[j] = boosts[j], boosts[i]

        # Recompose with modified bands
        result = np.zeros_like(channel)
        for i, band in enumerate(bands):
            result += band * boosts[i]

        return result

    def get_default_params(self):
        return {
            "bands": 4,
            "low_boost": 1.0,
            "mid_boost": 1.0,
            "high_boost": 1.0,
            "band_shuffle": 0.0,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "bands", "label": "Bands", "type": "slider", "min": 2, "max": 8, "step": 1, "default": 4},
            {"key": "high_boost", "label": "High Freq", "type": "slider", "min": 0, "max": 3.0, "step": 0.1, "default": 1.0},
            {"key": "mid_boost", "label": "Mid Freq", "type": "slider", "min": 0, "max": 3.0, "step": 0.1, "default": 1.0},
            {"key": "low_boost", "label": "Low Freq", "type": "slider", "min": 0, "max": 3.0, "step": 0.1, "default": 1.0},
            {"key": "band_shuffle", "label": "Band Shuffle", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.0},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = FrequencyManipulateFilter()
