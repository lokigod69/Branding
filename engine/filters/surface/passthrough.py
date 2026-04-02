"""
passthrough.py — Identity / Passthrough Filter

Returns the image unchanged. Used for:
  - Testing pipeline plumbing end-to-end
  - Placeholder stages
  - Verifying mask application without any filter effect
"""

import numpy as np
from engine.filters.base import BaseFilter


class PassthroughFilter(BaseFilter):
    name = "Passthrough"
    description = "No-op filter — passes image through unchanged. Useful for testing."
    family = "surface"
    category = "utility"
    pre_upscale_safe = True

    def apply(self, image, params, target_resolution=None):
        return image.copy()

    def get_default_params(self):
        return {}

    def get_param_schema(self):
        return []


FILTER = PassthroughFilter()
