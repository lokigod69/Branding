"""
chromatic_misreg.py — Chromatic Misregistration

Simulates the slight misalignment between color plates in offset printing
or the lateral chromatic aberration in camera lenses. Each color channel
is shifted by a slightly different amount, creating color fringing at
edges and a subtle analog imperfection.
"""
import numpy as np
import cv2
from engine.filters.base import BaseFilter


class ChromaticMisregFilter(BaseFilter):
    name = "Chromatic Misregistration"
    description = "Color plate misalignment — print registration error or lens fringing"
    family = "finish"
    category = "optical"
    pre_upscale_safe = False

    def apply(self, image, params, target_resolution=None):
        amount = params.get("amount", 0.3)
        angle = params.get("angle", 45.0)
        radial = params.get("radial", 0.0)
        center_x = params.get("center_x", 0.5)
        center_y = params.get("center_y", 0.5)

        if amount <= 0:
            return image

        h, w = image.shape[:2]
        max_shift = amount * min(w, h) * 0.005

        result = image.copy()

        if image.shape[2] < 3:
            return image

        if radial > 0:
            # Radial chromatic aberration — shift increases with distance from center
            cx = int(center_x * w)
            cy = int(center_y * h)
            yy, xx = np.mgrid[0:h, 0:w]
            dx = (xx - cx).astype(np.float32) / max(w, 1)
            dy = (yy - cy).astype(np.float32) / max(h, 1)
            dist = np.sqrt(dx * dx + dy * dy)

            for c, scale in enumerate([1.0 + radial * 0.01, 1.0, 1.0 - radial * 0.01]):
                map_x = (cx + (xx - cx) * scale).astype(np.float32)
                map_y = (cy + (yy - cy) * scale).astype(np.float32)
                result[:, :, c] = cv2.remap(
                    image[:, :, c], map_x, map_y,
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101
                )
        else:
            # Linear chromatic misregistration — plate offset
            angle_rad = np.radians(angle)
            shifts = [
                (max_shift * np.cos(angle_rad), max_shift * np.sin(angle_rad)),     # Red
                (0, 0),                                                               # Green (reference)
                (-max_shift * np.cos(angle_rad), -max_shift * np.sin(angle_rad)),   # Blue
            ]

            for c, (sx, sy) in enumerate(shifts):
                if abs(sx) < 0.01 and abs(sy) < 0.01:
                    continue
                M = np.float32([[1, 0, sx], [0, 1, sy]])
                result[:, :, c] = cv2.warpAffine(
                    image[:, :, c], M, (w, h),
                    borderMode=cv2.BORDER_REFLECT_101,
                )

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "amount": 0.3,
            "angle": 45.0,
            "radial": 0.0,
            "center_x": 0.5,
            "center_y": 0.5,
        }

    def get_param_schema(self):
        return [
            {"key": "amount", "label": "Amount", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "angle", "label": "Angle", "type": "slider", "min": 0, "max": 360, "step": 5, "default": 45},
            {"key": "radial", "label": "Radial", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.0},
            {"key": "center_x", "label": "Center X", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "center_y", "label": "Center Y", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
        ]


FILTER = ChromaticMisregFilter()
