"""
print_grain.py — Print Grain / Paper Tooth

Simulates the micro-texture of paper or canvas surface that a printed
image would exhibit. Unlike film grain (which is photographic randomness),
print grain is structural — it follows the substrate material's fiber
pattern, tooth depth, and ink absorption characteristics.

Result feels like looking at an inkjet or lithographic print surface.
"""
import numpy as np
import cv2
from engine.filters.base import BaseFilter


class PrintGrainFilter(BaseFilter):
    name = "Print Grain"
    description = "Paper tooth / canvas texture — feels like a physical print"
    family = "finish"
    category = "material"
    pre_upscale_safe = False

    def apply(self, image, params, target_resolution=None):
        amount = params.get("amount", 0.15)
        tooth_scale = params.get("tooth_scale", 2.0)
        fiber_direction = params.get("fiber_direction", 0.3)
        ink_absorption = params.get("ink_absorption", 0.4)
        paper_type = params.get("paper_type", 0)  # 0=smooth, 1=cotton, 2=canvas
        seed = params.get("seed", 42)

        if amount <= 0:
            return image

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)

        # Resolution scaling
        res_scale = 1.0
        if target_resolution:
            res_scale = w / max(target_resolution[0], 1)
        effective_tooth = max(tooth_scale * res_scale, 1.0)

        # Base texture noise at tooth scale
        grain_w = max(int(w / effective_tooth), 8)
        grain_h = max(int(h / effective_tooth), 8)
        base = rng.standard_normal((grain_h, grain_w)).astype(np.float32)

        # Paper type character
        paper_type = int(paper_type)
        if paper_type == 1:  # Cotton — softer, larger fiber
            base = cv2.GaussianBlur(base, (5, 5), 1.5)
        elif paper_type == 2:  # Canvas — weave pattern
            # Add periodic component for weave texture
            yy = np.linspace(0, grain_h * 0.5, grain_h)
            xx = np.linspace(0, grain_w * 0.5, grain_w)
            weave_x = np.sin(xx * np.pi * 2)[np.newaxis, :].repeat(grain_h, axis=0)
            weave_y = np.sin(yy * np.pi * 2)[:, np.newaxis].repeat(grain_w, axis=1)
            base = base * 0.5 + (weave_x + weave_y).astype(np.float32) * 0.25

        # Fiber directionality — stretch noise in one direction
        if fiber_direction > 0:
            k_w = max(int(fiber_direction * 8) | 1, 1)
            if k_w > 1:
                base = cv2.GaussianBlur(base, (k_w, 1), fiber_direction * 2)

        # Upscale to image size
        texture = cv2.resize(base, (w, h), interpolation=cv2.INTER_LINEAR)

        # Normalize
        t_std = texture.std()
        if t_std > 0:
            texture = texture / (t_std * 3.0)
        texture = np.clip(texture, -1.0, 1.0)

        # Ink absorption — darken effect in deep fibers (negative texture values)
        # Paper tooth catches more ink in valleys = slightly darker
        if ink_absorption > 0:
            absorption_mask = np.clip(-texture, 0, 1) * ink_absorption
            absorption_3 = absorption_mask[:, :, np.newaxis] * 0.03
            result = image * (1.0 - absorption_3)
        else:
            result = image.copy()

        # Apply surface texture as brightness modulation
        texture_3 = texture[:, :, np.newaxis] * amount * 0.08
        result = result + texture_3

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "amount": 0.15,
            "tooth_scale": 2.0,
            "fiber_direction": 0.3,
            "ink_absorption": 0.4,
            "paper_type": 0,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "amount", "label": "Amount", "type": "slider", "min": 0, "max": 0.5, "step": 0.01, "default": 0.15},
            {"key": "tooth_scale", "label": "Tooth Scale", "type": "slider", "min": 0.5, "max": 6.0, "step": 0.25, "default": 2.0},
            {"key": "fiber_direction", "label": "Fiber Direction", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "ink_absorption", "label": "Ink Absorption", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.4},
            {"key": "paper_type", "label": "Paper Type", "type": "select",
             "options": [{"value": 0, "label": "Smooth"}, {"value": 1, "label": "Cotton"}, {"value": 2, "label": "Canvas"}],
             "default": 0},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = PrintGrainFilter()
