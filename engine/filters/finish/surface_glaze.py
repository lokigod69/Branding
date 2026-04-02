"""
surface_glaze.py — Surface Glaze (Matte / Gloss / Metallic)

Simulates the surface coating of a physical print:
  - Matte: softened specular, flattened contrast in highlights
  - Gloss: enhanced specular, deepened blacks, saturated color
  - Metallic: specular highlight emphasis, desaturated shadows, chrome sheen

This is the "material intent" filter — it answers "what does this
look like when printed on [material]?"
"""
import numpy as np
import cv2
from engine.filters.base import BaseFilter


class SurfaceGlazeFilter(BaseFilter):
    name = "Surface Glaze"
    description = "Matte, gloss, or metallic print surface finish"
    family = "finish"
    category = "material"
    pre_upscale_safe = False

    def apply(self, image, params, target_resolution=None):
        glaze_type = params.get("glaze_type", 0)  # 0=matte, 1=gloss, 2=metallic
        intensity = params.get("intensity", 0.5)
        sheen = params.get("sheen", 0.3)

        if intensity <= 0:
            return image

        h, w = image.shape[:2]
        result = image.copy()
        luma = np.mean(image[:, :, :3], axis=2)

        glaze_type = int(glaze_type)

        if glaze_type == 0:
            # ─── Matte ─────────────────────────────────
            # Flatten highlights, reduce specular, soften micro-contrast
            # Lift blacks slightly (matte doesn't go full black)
            black_lift = 0.015 * intensity
            result = result * (1.0 - black_lift) + black_lift

            # Compress highlights
            highlight_threshold = 0.75
            for c in range(min(3, result.shape[2])):
                ch = result[:, :, c]
                above = ch > highlight_threshold
                if above.any():
                    excess = (ch[above] - highlight_threshold) / (1.0 - highlight_threshold + 1e-6)
                    compressed = highlight_threshold + (1.0 - highlight_threshold) * 0.7 * excess * (1.0 - intensity * 0.3)
                    result[:, :, c][above] = compressed

            # Slight desaturation (matte absorbs color slightly)
            if result.shape[2] >= 3:
                gray = np.mean(result[:, :, :3], axis=2, keepdims=True)
                desat = intensity * 0.08
                result[:, :, :3] = result[:, :, :3] * (1 - desat) + np.repeat(gray, 3, axis=2) * desat

            # Subtle surface scattering (very mild blur)
            if sheen > 0:
                k = max(int(sheen * 4) | 1, 3)
                softened = cv2.GaussianBlur(result, (k, k), sheen * 0.5)
                result = result * (1 - sheen * 0.1 * intensity) + softened * (sheen * 0.1 * intensity)

        elif glaze_type == 1:
            # ─── Gloss ─────────────────────────────────
            # Deepen blacks, enhance saturation, add specular
            black_deepen = 0.02 * intensity
            result = np.clip(result - black_deepen, 0, 1)
            result = result * (1.0 / (1.0 - black_deepen + 1e-6))  # Redistribute range

            # Boost saturation
            if result.shape[2] >= 3:
                gray = np.mean(result[:, :, :3], axis=2, keepdims=True)
                sat_boost = 1.0 + intensity * 0.12
                result[:, :, :3] = gray + (result[:, :, :3] - gray) * sat_boost

            # Specular highlight — bright spots get brighter
            if sheen > 0:
                specular_threshold = 0.85
                specular = np.clip((luma - specular_threshold) / (1 - specular_threshold + 1e-6), 0, 1)
                specular = cv2.GaussianBlur(specular, (7, 7), 2.0)
                result = result + specular[:, :, np.newaxis] * sheen * intensity * 0.08

        elif glaze_type == 2:
            # ─── Metallic ──────────────────────────────
            # Desaturate shadows, emphasize specular, chrome-like sheen
            if result.shape[2] >= 3:
                gray = np.mean(result[:, :, :3], axis=2, keepdims=True)
                # Shadow desaturation
                shadow_mask = np.clip((0.4 - luma) / 0.4, 0, 1)
                desat_amount = shadow_mask[:, :, np.newaxis] * intensity * 0.4
                result[:, :, :3] = result[:, :, :3] * (1 - desat_amount) + np.repeat(gray, 3, axis=2) * desat_amount

            # Metallic curve: push mid-tones toward specular
            for c in range(min(3, result.shape[2])):
                ch = result[:, :, c]
                # S-curve for metallic contrast
                mid = 0.5
                ch = mid + (ch - mid) * (1.0 + intensity * 0.3)
                result[:, :, c] = ch

            # Chrome sheen — highlight bloom
            if sheen > 0:
                bright = np.clip(luma - 0.7, 0, 1)
                bloom = cv2.GaussianBlur(bright, (15, 15), 4.0)
                result = result + bloom[:, :, np.newaxis] * sheen * intensity * 0.12

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "glaze_type": 0,
            "intensity": 0.5,
            "sheen": 0.3,
        }

    def get_param_schema(self):
        return [
            {"key": "glaze_type", "label": "Surface", "type": "select",
             "options": [{"value": 0, "label": "Matte"}, {"value": 1, "label": "Gloss"}, {"value": 2, "label": "Metallic"}],
             "default": 0},
            {"key": "intensity", "label": "Intensity", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "sheen", "label": "Sheen", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
        ]


FILTER = SurfaceGlazeFilter()
