"""
base.py — Abstract Base Effect & Registry

All effects implement apply(image, mask, params) → image.
The registry auto-discovers effects for the preset system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import importlib
import pkgutil
from pathlib import Path

import numpy as np


class BaseEffect(ABC):
    """Abstract base class for all pixel effects."""

    # Human-readable name for the preset gallery
    name: str = "Base Effect"
    description: str = ""
    # Category for UI grouping
    category: str = "general"

    @abstractmethod
    def apply(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        params: Dict[str, Any],
    ) -> np.ndarray:
        """
        Apply the effect to the image within the masked region.

        Args:
            image: float32 (H, W, C), range [0, 1] — the original image
            mask: float32 (H, W), range [0, 1] — the text alpha mask
            params: effect-specific parameters from the preset

        Returns:
            Modified float32 array (H, W, C) — the effected version.
            The compositor will blend this with the original using the mask.
        """
        pass

    def get_default_params(self) -> Dict[str, Any]:
        """Return the default parameter dict for this effect."""
        return {}


class EffectRegistry:
    """Auto-discovers and provides lookup for effect modules."""

    _effects: Dict[str, BaseEffect] = {}

    @classmethod
    def register(cls, key: str, effect: BaseEffect):
        cls._effects[key] = effect

    @classmethod
    def get(cls, key: str) -> Optional[BaseEffect]:
        cls._discover()
        return cls._effects.get(key)

    @classmethod
    def list_all(cls) -> Dict[str, BaseEffect]:
        cls._discover()
        return dict(cls._effects)

    @classmethod
    def _discover(cls):
        """Auto-import all modules in the effects package."""
        if cls._effects:
            return

        effects_dir = Path(__file__).parent
        for module_info in pkgutil.iter_modules([str(effects_dir)]):
            if module_info.name.startswith("_") or module_info.name == "base":
                continue
            try:
                mod = importlib.import_module(f".{module_info.name}", package="engine.effects")
                # Each module should have an EFFECT instance
                if hasattr(mod, "EFFECT"):
                    cls._effects[module_info.name] = mod.EFFECT
            except Exception as e:
                print(f"Warning: failed to load effect '{module_info.name}': {e}")
