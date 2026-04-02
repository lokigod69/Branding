"""
engine/regions/base.py — Region System Foundation

The Region System partitions images into labeled regions. Region generators
create the partitions; region operators act on them. Creative filters compose
these building blocks.

RegionMap: labels array (H,W int32) + metadata (centroids, areas, bboxes)
RegionGenerator ABC: generate(width, height, params) -> RegionMap
RegionOperator ABC: operate(image, region_map, params) -> image
"""

import importlib
import pkgutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

import numpy as np


class RegionMap:
    """A partition of the image into labeled regions."""

    __slots__ = ("labels", "n_regions", "metadata")

    def __init__(self, labels: np.ndarray, n_regions: int, metadata: dict = None):
        self.labels = labels          # (H, W) int32, each pixel 0..n_regions-1
        self.n_regions = n_regions
        self.metadata = metadata or {}

    def get_mask(self, region_id: int) -> np.ndarray:
        """Return float32 binary mask for a single region."""
        return (self.labels == region_id).astype(np.float32)

    def get_region_indices(self, region_id: int):
        """Return (rows, cols) indices for a region."""
        return np.where(self.labels == region_id)


class RegionGenerator(ABC):
    """Abstract base for region partition generators."""
    name: str = "unnamed"
    description: str = ""

    @abstractmethod
    def generate(self, width: int, height: int, params: dict) -> RegionMap:
        pass


class RegionOperator(ABC):
    """Abstract base for operations on region-partitioned images."""
    name: str = "unnamed"
    description: str = ""

    @abstractmethod
    def operate(self, image: np.ndarray, region_map: RegionMap, params: dict) -> np.ndarray:
        pass


# ── Registries ──────────────────────────────────────────────

class RegionGeneratorRegistry:
    _generators: Dict[str, RegionGenerator] = {}
    _discovered: bool = False

    @classmethod
    def get(cls, key: str) -> Optional[RegionGenerator]:
        cls._discover()
        return cls._generators.get(key)

    @classmethod
    def list_all(cls) -> Dict[str, RegionGenerator]:
        cls._discover()
        return dict(cls._generators)

    @classmethod
    def _discover(cls):
        if cls._discovered:
            return
        cls._discovered = True
        gen_dir = Path(__file__).parent / "generators"
        if not gen_dir.is_dir():
            return
        for mod_info in pkgutil.iter_modules([str(gen_dir)]):
            if mod_info.name.startswith("_"):
                continue
            try:
                mod = importlib.import_module(
                    f".generators.{mod_info.name}", package="engine.regions"
                )
                if hasattr(mod, "GENERATOR"):
                    cls._generators[mod_info.name] = mod.GENERATOR
            except Exception as e:
                print(f"Warning: failed to load region generator '{mod_info.name}': {e}")


class RegionOperatorRegistry:
    _operators: Dict[str, RegionOperator] = {}
    _discovered: bool = False

    @classmethod
    def get(cls, key: str) -> Optional[RegionOperator]:
        cls._discover()
        return cls._operators.get(key)

    @classmethod
    def list_all(cls) -> Dict[str, RegionOperator]:
        cls._discover()
        return dict(cls._operators)

    @classmethod
    def _discover(cls):
        if cls._discovered:
            return
        cls._discovered = True
        op_dir = Path(__file__).parent / "operators"
        if not op_dir.is_dir():
            return
        for mod_info in pkgutil.iter_modules([str(op_dir)]):
            if mod_info.name.startswith("_"):
                continue
            try:
                mod = importlib.import_module(
                    f".operators.{mod_info.name}", package="engine.regions"
                )
                if hasattr(mod, "OPERATOR"):
                    cls._operators[mod_info.name] = mod.OPERATOR
            except Exception as e:
                print(f"Warning: failed to load region operator '{mod_info.name}': {e}")
