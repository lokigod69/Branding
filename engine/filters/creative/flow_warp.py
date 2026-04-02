"""
flow_warp.py — Flow-Field Warping

Generates a coherent vector field (flow field) and warps the image along
it via displacement mapping. Produces organic, wave-like distortions that
can look like heat haze, water refraction, or abstract art scarring.
"""
import numpy as np
import cv2
from engine.filters.base import BaseFilter


class FlowWarpFilter(BaseFilter):
    name = "Flow Warp"
    description = "Coherent flow-field displacement — wave, scar, haze"
    family = "creative"
    category = "displacement"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        strength = params.get("strength", 0.3)
        scale = params.get("scale", 3.0)
        turbulence = params.get("turbulence", 0.5)
        edge_protect = params.get("edge_protect", 0.5)
        direction = params.get("direction", 0.0)  # 0=random, 1=horizontal, 2=vertical
        seed = params.get("seed", 42)

        if strength <= 0:
            return image

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)

        # Generate base flow field at lower res then upscale for coherence
        flow_w = max(int(w / (scale * 8)), 4)
        flow_h = max(int(h / (scale * 8)), 4)

        # Primary flow direction
        dx_base = rng.standard_normal((flow_h, flow_w)).astype(np.float32)
        dy_base = rng.standard_normal((flow_h, flow_w)).astype(np.float32)

        # Smooth for coherent flow
        smooth_k = max(int(scale) | 1, 3)
        dx_base = cv2.GaussianBlur(dx_base, (smooth_k, smooth_k), scale * 0.5)
        dy_base = cv2.GaussianBlur(dy_base, (smooth_k, smooth_k), scale * 0.5)

        # Add turbulence at a higher frequency
        if turbulence > 0:
            turb_w = max(flow_w * 2, 8)
            turb_h = max(flow_h * 2, 8)
            dx_turb = rng.standard_normal((turb_h, turb_w)).astype(np.float32)
            dy_turb = rng.standard_normal((turb_h, turb_w)).astype(np.float32)
            dx_turb = cv2.resize(dx_turb, (flow_w, flow_h), interpolation=cv2.INTER_LINEAR)
            dy_turb = cv2.resize(dy_turb, (flow_w, flow_h), interpolation=cv2.INTER_LINEAR)
            dx_base += dx_turb * turbulence * 0.5
            dy_base += dy_turb * turbulence * 0.5

        # Direction bias
        direction = int(direction)
        if direction == 1:  # Horizontal dominant
            dy_base *= 0.2
        elif direction == 2:  # Vertical dominant
            dx_base *= 0.2

        # Upscale to image size
        dx = cv2.resize(dx_base, (w, h), interpolation=cv2.INTER_CUBIC)
        dy = cv2.resize(dy_base, (w, h), interpolation=cv2.INTER_CUBIC)

        # Edge protection — reduce displacement near strong edges
        if edge_protect > 0:
            gray = np.mean(image[:, :, :3], axis=2).astype(np.float32)
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            edge_mag = np.sqrt(gx * gx + gy * gy)
            e_max = edge_mag.max()
            if e_max > 0:
                edge_mag /= e_max
            suppress = 1.0 - edge_mag * edge_protect
            dx *= suppress
            dy *= suppress

        # Scale displacement to pixels
        disp_px = strength * min(w, h) * 0.05
        dx *= disp_px
        dy *= disp_px

        # Apply remap
        map_x = np.arange(w, dtype=np.float32)[np.newaxis, :].repeat(h, axis=0) + dx
        map_y = np.arange(h, dtype=np.float32)[:, np.newaxis].repeat(w, axis=1) + dy

        result = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REFLECT_101)

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "strength": 0.3,
            "scale": 3.0,
            "turbulence": 0.5,
            "edge_protect": 0.5,
            "direction": 0,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "strength", "label": "Strength", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "scale", "label": "Scale", "type": "slider", "min": 1, "max": 10, "step": 0.5, "default": 3.0},
            {"key": "turbulence", "label": "Turbulence", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "edge_protect", "label": "Edge Protection", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "direction", "label": "Direction", "type": "select",
             "options": [{"value": 0, "label": "Random"}, {"value": 1, "label": "Horizontal"}, {"value": 2, "label": "Vertical"}],
             "default": 0},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = FlowWarpFilter()
