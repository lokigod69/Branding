"""
presets.py — Preset Load/Save/Validation System

Manages JSON presets with schema versioning.
Supports built-in + user-saved presets.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Pydantic schemas ────────────────────────────────────────

class FontConfig(BaseModel):
    family: str = "Arial"
    path: Optional[str] = None


class PositionConfig(BaseModel):
    x_pct: float = 0.50
    y_pct: float = 0.50
    anchor: str = "center"


class LayoutConfig(BaseModel):
    mode: str = "relative"
    size_rel_width: float = 0.22
    position: PositionConfig = Field(default_factory=PositionConfig)
    rotation_deg: float = -8.0
    tracking: float = 0.02
    feather_px: float = 2.0


class EffectConfig(BaseModel):
    type: str = "difference"
    params: Dict[str, Any] = Field(default_factory=dict)
    blend_mode: str = "normal"
    strength: float = 0.85


class RandomConfig(BaseModel):
    seed: int = 12345


class ExportConfig(BaseModel):
    keep_format: bool = True
    suffix: str = "__signed__default"
    include_timestamp: bool = False


class PresetSchema(BaseModel):
    version: int = 1
    name: str = "Custom Preset"
    text: str = "LAZART"
    font: FontConfig = Field(default_factory=FontConfig)
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    effect: EffectConfig = Field(default_factory=EffectConfig)
    random: RandomConfig = Field(default_factory=RandomConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)


# ── V2 Schema — Unified Pipeline Presets ────────────────────
# Only one signing stage is supported in v2.
# Signing config remains top-level by design.
# stages[] array order IS the canonical processing order.

class MaskModifiers(BaseModel):
    """Post-generation modifiers applied to a stage's mask."""
    feather: float = 0.0
    invert: bool = False
    clamp_min: float = 0.0
    clamp_max: float = 1.0
    noise_breakup: float = 0.0
    border_softness: float = 0.0


class FilterStageConfig(BaseModel):
    """Configuration for a single filter stage in the pipeline."""
    id: str
    type: str = "filter"
    filter_key: str                          # Registry key (e.g., "film_grain")
    enabled: bool = True
    intensity: float = 1.0                   # 0.0–1.0, overall blend
    blend_mode: str = "normal"               # Stage-level blend mode
    mask_source: str = "global"              # global, shadows, mids, highlights, etc.
    mask_params: Dict[str, Any] = Field(default_factory=dict)
    mask_modifiers: MaskModifiers = Field(default_factory=MaskModifiers)
    seed: int = 0
    params: Dict[str, Any] = Field(default_factory=dict)


class SigningStageConfig(BaseModel):
    """Configuration for the signing stage in the pipeline."""
    id: str = "signing_1"
    type: str = "signing"
    enabled: bool = True


class SigningConfig(BaseModel):
    """All signing-related settings (grouped for v2)."""
    text: str = "LAZART"
    font: FontConfig = Field(default_factory=FontConfig)
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    effect: EffectConfig = Field(default_factory=EffectConfig)


class PresetSchemaV2(BaseModel):
    version: int = 2
    name: str = "Custom Preset"
    stages: List[Dict[str, Any]] = Field(default_factory=list)  # Ordered stage stack
    signing: SigningConfig = Field(default_factory=SigningConfig)
    global_intensity: float = 1.0            # Stack-level amount slider
    random: RandomConfig = Field(default_factory=RandomConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)


def migrate_v1_to_v2(v1_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-migrate a v1 preset dict to v2 format.
    Wraps the signing config into a single signing stage.
    """
    return {
        "version": 2,
        "name": v1_data.get("name", "Migrated Preset"),
        "stages": [
            {"id": "signing_1", "type": "signing", "enabled": True}
        ],
        "signing": {
            "text": v1_data.get("text", "LAZART"),
            "font": v1_data.get("font", {"family": "Arial", "path": None}),
            "layout": v1_data.get("layout", {}),
            "effect": v1_data.get("effect", {}),
        },
        "global_intensity": 1.0,
        "random": v1_data.get("random", {"seed": 12345}),
        "export": v1_data.get("export", {}),
    }


# ── Functions ───────────────────────────────────────────────

def load_preset(path: str):
    """Load and validate a preset from a JSON file. Auto-detects v1/v2."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    version = data.get("version", 1)
    if version >= 2:
        return PresetSchemaV2(**data)
    return PresetSchema(**data)


def save_preset(preset: PresetSchema, path: str) -> str:
    """Save a preset to a JSON file."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(preset.model_dump(), f, indent=2, ensure_ascii=False)
    return str(out.resolve())


def list_presets(directory: str) -> List[Dict[str, Any]]:
    """List all preset files in a directory with basic metadata."""
    presets = []
    d = Path(directory)
    if not d.exists():
        return presets

    for f in sorted(d.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            presets.append({
                "filename": f.name,
                "path": str(f.resolve()),
                "name": data.get("name", f.stem),
                "effect_type": data.get("effect", {}).get("type", "unknown"),
                "version": data.get("version", 1),
            })
        except Exception:
            pass

    return presets


def get_default_preset() -> PresetSchema:
    """Return the default 'LAZART Difference' preset."""
    return PresetSchema(
        name="Classic Difference",
        text="LAZART",
        font=FontConfig(family="Arial"),
        layout=LayoutConfig(
            size_rel_width=0.22,
            position=PositionConfig(x_pct=0.50, y_pct=0.50, anchor="center"),
            rotation_deg=-8.0,
            tracking=0.02,
            feather_px=2.0,
        ),
        effect=EffectConfig(
            type="difference",
            params={"color_rgb": [255, 255, 255]},
            blend_mode="normal",
            strength=0.85,
        ),
        random=RandomConfig(seed=12345),
        export=ExportConfig(suffix="__signed__diff"),
    )
