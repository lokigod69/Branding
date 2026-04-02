"""
base.py — Abstract Base Filter & Registry

All filters implement apply(image, params) → image.
Filters operate on the full image (masking is handled by the pipeline).
The registry auto-discovers filters from subpackages (surface/, creative/, finish/).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import importlib
import pkgutil
from pathlib import Path

import numpy as np


class BaseFilter(ABC):
    """
    Full-image filter. Operates on the entire image (or a masked region,
    handled externally by the pipeline executor).
    """

    # Human-readable name for the UI
    name: str = "Base Filter"
    description: str = ""

    # Family grouping: "surface", "creative", "finish"
    family: str = "surface"
    # Specific subcategory within the family
    category: str = "general"

    # Whether this filter's output survives upscaling well
    pre_upscale_safe: bool = True

    @abstractmethod
    def apply(
        self,
        image: np.ndarray,
        params: Dict[str, Any],
        target_resolution: Optional[Tuple[int, int]] = None,
    ) -> np.ndarray:
        """
        Apply the filter to the entire image.

        Args:
            image: float32 (H, W, C), range [0, 1]
            params: filter-specific parameters
            target_resolution: (width, height) of final output for
                               resolution-aware effects (grain scaling, etc.).
                               None means the image IS the final resolution.

        Returns:
            Modified float32 array (H, W, C).
            The pipeline executor will handle masking and intensity blending.
        """
        pass

    def get_default_params(self) -> Dict[str, Any]:
        """Return the default parameter dict for this filter."""
        return {}

    def get_param_schema(self) -> List[Dict[str, Any]]:
        """
        Return UI-friendly parameter definitions for dynamic frontend rendering.

        Each entry:
            {"key": "amount", "label": "Amount", "type": "slider",
             "min": 0, "max": 1, "step": 0.01, "default": 0.5}
        Supported types: slider, number, select, toggle
        """
        return []


class FilterRegistry:
    """Auto-discovers and provides lookup for filter modules."""

    _filters: Dict[str, BaseFilter] = {}
    _discovered: bool = False

    @classmethod
    def register(cls, key: str, filt: BaseFilter):
        cls._filters[key] = filt

    @classmethod
    def get(cls, key: str) -> Optional[BaseFilter]:
        cls._discover()
        return cls._filters.get(key)

    @classmethod
    def list_all(cls) -> Dict[str, BaseFilter]:
        cls._discover()
        return dict(cls._filters)

    @classmethod
    def _discover(cls):
        """Auto-import all filter modules from subpackages."""
        if cls._discovered:
            return
        cls._discovered = True

        filters_dir = Path(__file__).parent
        # Scan subpackages: surface/, creative/, finish/
        for subdir in ["surface", "creative", "finish"]:
            sub_path = filters_dir / subdir
            if not sub_path.is_dir():
                continue
            for module_info in pkgutil.iter_modules([str(sub_path)]):
                if module_info.name.startswith("_"):
                    continue
                try:
                    mod = importlib.import_module(
                        f".{subdir}.{module_info.name}",
                        package="engine.filters",
                    )
                    if hasattr(mod, "FILTER"):
                        key = module_info.name
                        cls._filters[key] = mod.FILTER
                except Exception as e:
                    print(f"Warning: failed to load filter '{subdir}/{module_info.name}': {e}")
