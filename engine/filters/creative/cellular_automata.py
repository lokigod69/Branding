"""
cellular_automata.py — Cellular Automata Engine

Runs a Game-of-Life-style cellular automaton on a low-res grid, then uses
the resulting activation pattern as a mask to apply operations:
blur, invert, displace, or desaturate. The automata state evolves
across iterations, creating organic, evolving patterns.
"""
import numpy as np
import cv2
from engine.filters.base import BaseFilter


class CellularAutomataFilter(BaseFilter):
    name = "Cellular Automata"
    description = "Automata-driven activation mask — blur, invert, displace, desaturate"
    family = "creative"
    category = "generative"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        cell_size = max(params.get("cell_size", 8), 2)
        iterations = max(params.get("iterations", 5), 1)
        fill_probability = params.get("fill_probability", 0.4)
        operation = params.get("operation", "blur")
        op_strength = params.get("op_strength", 0.7)
        seed = params.get("seed", 42)

        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)

        # Create grid
        grid_w = max(w // cell_size, 4)
        grid_h = max(h // cell_size, 4)

        # Random initial state
        grid = (rng.random((grid_h, grid_w)) < fill_probability).astype(np.int32)

        # Run automata iterations (Game of Life rules with slight variation)
        for _ in range(iterations):
            # Count neighbors (wrap around)
            padded = np.pad(grid, 1, mode='wrap')
            neighbors = np.zeros_like(grid)
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    neighbors += padded[1 + dy:grid_h + 1 + dy, 1 + dx:grid_w + 1 + dx]

            # Standard Conway rules: survive with 2-3 neighbors, born with 3
            new_grid = np.zeros_like(grid)
            new_grid[(grid == 1) & ((neighbors == 2) | (neighbors == 3))] = 1
            new_grid[(grid == 0) & (neighbors == 3)] = 1
            grid = new_grid

        # Upscale grid to image mask
        mask = cv2.resize(grid.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
        # Soften edges
        mask = cv2.GaussianBlur(mask, (7, 7), 2.0)
        mask_3 = mask[:, :, np.newaxis]

        # Apply operation to masked areas
        result = image.copy()

        if operation == "blur":
            k = max(int(op_strength * 30) | 1, 3)
            operated = cv2.GaussianBlur(image, (k, k), 0)
            result = image * (1 - mask_3) + operated * mask_3

        elif operation == "invert":
            inverted = 1.0 - image
            result = image * (1 - mask_3 * op_strength) + inverted * (mask_3 * op_strength)

        elif operation == "displace":
            disp_amount = op_strength * min(w, h) * 0.02
            noise_dx = rng.standard_normal((h, w)).astype(np.float32)
            noise_dy = rng.standard_normal((h, w)).astype(np.float32)
            noise_dx = cv2.GaussianBlur(noise_dx, (9, 9), 3.0) * disp_amount * mask
            noise_dy = cv2.GaussianBlur(noise_dy, (9, 9), 3.0) * disp_amount * mask
            map_x = np.arange(w, dtype=np.float32)[np.newaxis, :].repeat(h, axis=0) + noise_dx
            map_y = np.arange(h, dtype=np.float32)[:, np.newaxis].repeat(w, axis=1) + noise_dy
            result = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REFLECT_101)

        elif operation == "desaturate":
            if image.shape[2] >= 3:
                gray = np.mean(image[:, :, :3], axis=2, keepdims=True)
                gray_3 = np.repeat(gray, 3, axis=2)
                if image.shape[2] == 4:
                    gray_3 = np.concatenate([gray_3, image[:, :, 3:]], axis=2)
                result = image * (1 - mask_3 * op_strength) + gray_3 * (mask_3 * op_strength)

        return np.clip(result, 0.0, 1.0)

    def get_default_params(self):
        return {
            "cell_size": 8,
            "iterations": 5,
            "fill_probability": 0.4,
            "operation": "blur",
            "op_strength": 0.7,
            "seed": 42,
        }

    def get_param_schema(self):
        return [
            {"key": "cell_size", "label": "Cell Size", "type": "slider", "min": 2, "max": 32, "step": 1, "default": 8},
            {"key": "iterations", "label": "Iterations", "type": "slider", "min": 1, "max": 20, "step": 1, "default": 5},
            {"key": "fill_probability", "label": "Fill Probability", "type": "slider", "min": 0.1, "max": 0.8, "step": 0.05, "default": 0.4},
            {"key": "operation", "label": "Operation", "type": "select",
             "options": ["blur", "invert", "displace", "desaturate"], "default": "blur"},
            {"key": "op_strength", "label": "Op Strength", "type": "slider", "min": 0.1, "max": 1, "step": 0.05, "default": 0.7},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]


FILTER = CellularAutomataFilter()
