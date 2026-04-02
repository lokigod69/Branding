"""
routes.py — FastAPI API Routes

Handles all REST endpoints for image upload, preview, export, presets, and fonts.
"""

import uuid
import shutil
import base64
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse
import numpy as np

from engine.io_handler import load_image, save_image, create_proxy, encode_to_bytes
from engine.mask_generator import generate_mask, generate_per_letter_masks, get_system_fonts
from engine.compositor import composite
from engine.effects.base import EffectRegistry
from engine.presets import (
    PresetSchema, load_preset, save_preset, list_presets, get_default_preset,
)
from engine.batch_processor import process_batch

router = APIRouter()

# ── In-memory session store ─────────────────────────────────
# Stores loaded images for the current session
_images: Dict[str, Dict[str, Any]] = {}

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
FONTS_DIR = BASE_DIR / "fonts"
PRESETS_DIR = BASE_DIR / "presets"
UPLOAD_DIR = BASE_DIR / "uploads"


# ═══════════════════════════════════════════════════════════
# IMAGE MANAGEMENT
# ═══════════════════════════════════════════════════════════

@router.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    """Upload one or more images. Returns metadata + proxy URLs."""
    results = []

    for file in files:
        img_id = str(uuid.uuid4())[:8]
        ext = Path(file.filename).suffix.lower()

        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif"):
            continue

        # Save to uploads/
        upload_path = UPLOAD_DIR / f"{img_id}{ext}"
        with open(upload_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Load and create proxy
        try:
            image_array, meta = load_image(str(upload_path))
            proxy, scale = create_proxy(image_array)
            proxy_bytes = encode_to_bytes(proxy, "JPEG")
            proxy_b64 = base64.b64encode(proxy_bytes).decode("utf-8")

            _images[img_id] = {
                "id": img_id,
                "filename": file.filename,
                "path": str(upload_path),
                "array": image_array,
                "meta": meta,
                "proxy": proxy,
                "proxy_scale": scale,
                "width": image_array.shape[1],
                "height": image_array.shape[0],
            }

            results.append({
                "id": img_id,
                "filename": file.filename,
                "width": image_array.shape[1],
                "height": image_array.shape[0],
                "proxy": f"data:image/jpeg;base64,{proxy_b64}",
            })
        except Exception as e:
            results.append({
                "id": img_id,
                "filename": file.filename,
                "error": str(e),
            })

    return {"images": results}


@router.get("/images")
async def list_images():
    """List all loaded images in the current session."""
    return {
        "images": [
            {
                "id": v["id"],
                "filename": v["filename"],
                "width": v["width"],
                "height": v["height"],
            }
            for v in _images.values()
        ]
    }


@router.delete("/images/{image_id}")
async def delete_image(image_id: str):
    """Remove an image from the session."""
    if image_id not in _images:
        raise HTTPException(404, "Image not found")

    info = _images.pop(image_id)
    # Clean up the upload file
    try:
        Path(info["path"]).unlink(missing_ok=True)
    except Exception:
        pass

    return {"status": "deleted", "id": image_id}


@router.post("/images/{image_id}/replace")
async def replace_image(image_id: str, file: UploadFile = File(...)):
    """Re-import: Replace an existing image with a new one."""
    if image_id not in _images:
        raise HTTPException(404, "Image not found")

    old_info = _images[image_id]
    ext = Path(file.filename).suffix.lower()
    upload_path = UPLOAD_DIR / f"{image_id}{ext}"

    # Clean up old file
    try:
        Path(old_info["path"]).unlink(missing_ok=True)
    except Exception:
        pass

    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    image_array, meta = load_image(str(upload_path))
    proxy, scale = create_proxy(image_array)
    proxy_bytes = encode_to_bytes(proxy, "JPEG")
    proxy_b64 = base64.b64encode(proxy_bytes).decode("utf-8")

    _images[image_id] = {
        "id": image_id,
        "filename": file.filename,
        "path": str(upload_path),
        "array": image_array,
        "meta": meta,
        "proxy": proxy,
        "proxy_scale": scale,
        "width": image_array.shape[1],
        "height": image_array.shape[0],
    }

    return {
        "id": image_id,
        "filename": file.filename,
        "width": image_array.shape[1],
        "height": image_array.shape[0],
        "proxy": f"data:image/jpeg;base64,{proxy_b64}",
    }


# ═══════════════════════════════════════════════════════════
# PREVIEW
# ═══════════════════════════════════════════════════════════

@router.post("/preview")
async def generate_preview(body: Dict[str, Any] = Body(...)):
    """
    Generate a preview image with the current settings.
    Processes on the proxy image for speed.
    """
    print("LEGACY PING - Single layer preview called", flush=True)
    image_id = body.get("image_id")
    if not image_id or image_id not in _images:
        raise HTTPException(404, "Image not found")

    info = _images[image_id]
    proxy = info["proxy"]
    h, w = proxy.shape[:2]

    # Parse settings
    text = body.get("text", "LAZART")
    font_path = body.get("font_path")
    size_rel_width = body.get("size_rel_width", 0.22)
    x_pct = body.get("x_pct", 0.50)
    y_pct = body.get("y_pct", 0.50)
    anchor = body.get("anchor", "center")
    rotation_deg = body.get("rotation_deg", -8.0)
    tracking = body.get("tracking", 0.02)
    feather_px = body.get("feather_px", 2.0)
    skew_x = body.get("skew_x", 0.0)
    skew_y = body.get("skew_y", 0.0)
    perspective_x = body.get("perspective_x", 0.0)
    perspective_y = body.get("perspective_y", 0.0)
    vertical = body.get("vertical", False)
    mirror_x = body.get("mirror_x", False)
    mirror_y = body.get("mirror_y", False)
    effect_type = body.get("effect_type", "difference")
    effect_params = body.get("effect_params", {})
    strength = body.get("strength", 0.85)
    blend_mode = body.get("blend_mode", "normal")
    per_letter_effects = body.get("per_letter_effects")
    base_color_rgb = body.get("base_color_rgb", [255, 255, 255])
    if "color_rgb" not in effect_params:
        effect_params["color_rgb"] = base_color_rgb

    # Scale feather for proxy
    scale = info["proxy_scale"]
    scaled_feather = feather_px * scale

    # Generate preview in thread pool
    result = await asyncio.to_thread(
        _render_preview,
        proxy, w, h, text, font_path, size_rel_width,
        x_pct, y_pct, anchor, rotation_deg, tracking, scaled_feather,
        effect_type, effect_params, strength, blend_mode,
        skew_x, skew_y, perspective_x, perspective_y,
        vertical, mirror_x, mirror_y,
        per_letter_effects,
    )

    # Encode to base64
    img_bytes = encode_to_bytes(result, "JPEG")
    b64 = base64.b64encode(img_bytes).decode("utf-8")

    return {"preview": f"data:image/jpeg;base64,{b64}"}


def _render_preview(
    proxy, w, h, text, font_path, size_rel_width,
    x_pct, y_pct, anchor, rotation_deg, tracking, feather_px,
    effect_type, effect_params, strength, blend_mode,
    skew_x=0.0, skew_y=0.0, perspective_x=0.0, perspective_y=0.0,
    vertical=False, mirror_x=False, mirror_y=False,
    per_letter_effects=None,
):
    """Render a preview (runs in thread pool)."""
    mask_kwargs = dict(
        text=text, image_width=w, image_height=h,
        font_path=font_path, size_rel_width=size_rel_width,
        x_pct=x_pct, y_pct=y_pct, anchor=anchor,
        rotation_deg=rotation_deg, tracking=tracking,
        feather_px=feather_px,
        skew_x=skew_x, skew_y=skew_y,
        perspective_x=perspective_x, perspective_y=perspective_y,
        vertical=vertical, mirror_x=mirror_x, mirror_y=mirror_y,
    )

    # Per-letter mode: each character gets its own effect
    if per_letter_effects and len(per_letter_effects) > 0:
        letter_masks = generate_per_letter_masks(**mask_kwargs)
        output = proxy.copy()
        for i, (char, mask) in enumerate(letter_masks):
            # Find effect config for this letter index
            if i < len(per_letter_effects):
                ple = per_letter_effects[i]
            else:
                ple = {}
            etype = ple.get("effect_type", effect_type)
            eparams = ple.get("effect_params", effect_params)
            estrength = ple.get("strength", strength)
            eblend = ple.get("blend_mode", blend_mode)

            effect = EffectRegistry.get(etype)
            if effect is None:
                effect = EffectRegistry.get("difference")
            effected = effect.apply(proxy, mask, eparams)
            output = composite(output, effected, mask, strength=estrength, blend_mode=eblend)
        return output

    # Uniform mode (original path)
    mask = generate_mask(**mask_kwargs)

    effect = EffectRegistry.get(effect_type)
    if effect is None:
        effect = EffectRegistry.get("difference")

    effected = effect.apply(proxy, mask, effect_params)
    output = composite(proxy, effected, mask, strength=strength, blend_mode=blend_mode)
    return output


# Also generate mask-only preview
@router.post("/preview/mask")
async def generate_mask_preview(body: Dict[str, Any] = Body(...)):
    """Generate a mask-only view for precise placement."""
    image_id = body.get("image_id")
    if not image_id or image_id not in _images:
        raise HTTPException(404, "Image not found")

    info = _images[image_id]
    proxy = info["proxy"]
    h, w = proxy.shape[:2]

    text = body.get("text", "LAZART")
    font_path = body.get("font_path")
    size_rel_width = body.get("size_rel_width", 0.22)
    x_pct = body.get("x_pct", 0.50)
    y_pct = body.get("y_pct", 0.50)
    anchor = body.get("anchor", "center")
    rotation_deg = body.get("rotation_deg", -8.0)
    tracking = body.get("tracking", 0.02)
    feather_px = body.get("feather_px", 2.0) * info["proxy_scale"]
    skew_x = body.get("skew_x", 0.0)
    skew_y = body.get("skew_y", 0.0)
    perspective_x = body.get("perspective_x", 0.0)
    perspective_y = body.get("perspective_y", 0.0)
    vertical = body.get("vertical", False)
    mirror_x = body.get("mirror_x", False)
    mirror_y = body.get("mirror_y", False)

    mask = await asyncio.to_thread(
        generate_mask,
        text=text, image_width=w, image_height=h,
        font_path=font_path, size_rel_width=size_rel_width,
        x_pct=x_pct, y_pct=y_pct, anchor=anchor,
        rotation_deg=rotation_deg, tracking=tracking,
        feather_px=feather_px,
        skew_x=skew_x, skew_y=skew_y,
        perspective_x=perspective_x, perspective_y=perspective_y,
        vertical=vertical, mirror_x=mirror_x, mirror_y=mirror_y,
    )

    # Render mask as red overlay on semi-transparent image
    overlay = proxy.copy()[:, :, :3] * 0.3
    mask_3ch = mask[:, :, np.newaxis]
    overlay = overlay * (1 - mask_3ch) + np.array([1.0, 0.2, 0.1]).reshape(1, 1, 3) * mask_3ch

    img_bytes = encode_to_bytes(np.clip(overlay, 0, 1), "JPEG")
    b64 = base64.b64encode(img_bytes).decode("utf-8")

    return {"preview": f"data:image/jpeg;base64,{b64}"}


# ═══════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════

@router.post("/export")
async def export_image(body: Dict[str, Any] = Body(...)):
    """Full-resolution export of a single image."""
    image_id = body.get("image_id")
    if not image_id or image_id not in _images:
        raise HTTPException(404, "Image not found")

    info = _images[image_id]
    image = info["array"]
    meta = info["meta"]
    h, w = image.shape[:2]

    # Parse settings (same as preview but at full resolution)
    text = body.get("text", "LAZART")
    font_path = body.get("font_path")
    size_rel_width = body.get("size_rel_width", 0.22)
    x_pct = body.get("x_pct", 0.50)
    y_pct = body.get("y_pct", 0.50)
    anchor = body.get("anchor", "center")
    rotation_deg = body.get("rotation_deg", -8.0)
    tracking = body.get("tracking", 0.02)
    feather_px = body.get("feather_px", 2.0)
    skew_x = body.get("skew_x", 0.0)
    skew_y = body.get("skew_y", 0.0)
    perspective_x = body.get("perspective_x", 0.0)
    perspective_y = body.get("perspective_y", 0.0)
    vertical = body.get("vertical", False)
    mirror_x = body.get("mirror_x", False)
    mirror_y = body.get("mirror_y", False)
    effect_type = body.get("effect_type", "difference")
    effect_params = body.get("effect_params", {})
    strength = body.get("strength", 0.85)
    blend_mode = body.get("blend_mode", "normal")
    suffix = body.get("suffix", "__signed")
    include_timestamp = body.get("include_timestamp", False)

    per_letter_effects = body.get("per_letter_effects")

    output = await asyncio.to_thread(
        _render_preview,
        image, w, h, text, font_path, size_rel_width,
        x_pct, y_pct, anchor, rotation_deg, tracking, feather_px,
        effect_type, effect_params, strength, blend_mode,
        skew_x, skew_y, perspective_x, perspective_y,
        vertical, mirror_x, mirror_y,
        per_letter_effects,
    )

    # Build output path
    stem = Path(info["filename"]).stem
    ext = Path(info["filename"]).suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if include_timestamp:
        out_name = f"{stem}{suffix}__{timestamp}{ext}"
    else:
        out_name = f"{stem}{suffix}{ext}"

    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Auto-increment filename if it exists
    out_path = OUTPUT_DIR / out_name
    counter = 1
    while out_path.exists():
        if include_timestamp:
            out_name = f"{stem}{suffix}__{timestamp} ({counter}){ext}"
        else:
            out_name = f"{stem}{suffix} ({counter}){ext}"
        out_path = OUTPUT_DIR / out_name
        counter += 1
        
    out_path = str(out_path)

    await asyncio.to_thread(save_image, output, out_path, meta)

    # Save sidecar preset
    import json
    sidecar = {**body, "source_file": info["filename"]}
    with open(out_path + ".preset.json", "w") as f:
        json.dump(sidecar, f, indent=2)

    return {
        "status": "exported",
        "output_path": out_path,
        "filename": out_name,
    }


@router.post("/batch/export")
async def batch_export(body: Dict[str, Any] = Body(...)):
    """Batch export. Progress is reported via WebSocket."""
    image_ids = body.get("image_ids", list(_images.keys()))
    preset_data = body.get("preset", get_default_preset().model_dump())
    overrides = body.get("overrides", {})

    preset = PresetSchema(**preset_data)
    image_paths = [_images[iid]["path"] for iid in image_ids if iid in _images]

    if not image_paths:
        raise HTTPException(400, "No images to export")

    OUTPUT_DIR.mkdir(exist_ok=True)
    results = await process_batch(
        image_paths=image_paths,
        preset=preset,
        output_dir=str(OUTPUT_DIR),
        overrides=overrides,
    )

    return {"results": results}


# ═══════════════════════════════════════════════════════════
# PRESETS
# ═══════════════════════════════════════════════════════════

@router.get("/presets")
async def get_presets():
    """List all available presets."""
    presets = list_presets(str(PRESETS_DIR))
    return {"presets": presets}


@router.get("/presets/{name}")
async def get_preset(name: str):
    """Load a specific preset by filename (without .json)."""
    path = PRESETS_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(404, "Preset not found")

    preset = load_preset(str(path))
    return preset.model_dump()


@router.post("/presets")
async def save_user_preset(body: Dict[str, Any] = Body(...)):
    """Save a new user preset."""
    preset = PresetSchema(**body)
    name = body.get("name", "custom_preset").replace(" ", "_").lower()
    path = PRESETS_DIR / f"user_{name}.json"
    save_preset(preset, str(path))
    return {"status": "saved", "path": str(path)}


# ═══════════════════════════════════════════════════════════
# FONTS
# ═══════════════════════════════════════════════════════════

@router.get("/fonts")
async def get_custom_fonts():
    """List custom uploaded fonts."""
    fonts = []
    FONTS_DIR.mkdir(exist_ok=True)
    for f in FONTS_DIR.glob("*"):
        if f.suffix.lower() in (".ttf", ".otf"):
            fonts.append({"name": f.stem, "path": str(f.resolve())})
    return {"fonts": sorted(fonts, key=lambda x: x["name"].lower())}


@router.post("/fonts")
async def upload_font(file: UploadFile = File(...)):
    """Upload a custom font file."""
    if not file.filename.lower().endswith((".ttf", ".otf")):
        raise HTTPException(400, "Only .ttf and .otf fonts are supported")

    FONTS_DIR.mkdir(exist_ok=True)
    font_path = FONTS_DIR / file.filename
    with open(font_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "status": "uploaded",
        "name": font_path.stem,
        "path": str(font_path.resolve()),
    }


@router.get("/system-fonts")
async def get_system_fonts_list():
    """List system-installed fonts."""
    fonts = get_system_fonts()
    return {"fonts": fonts}


# ═══════════════════════════════════════════════════════════
# EFFECTS METADATA
# ═══════════════════════════════════════════════════════════

@router.get("/effects")
async def get_effects():
    """List all available effects with their default params."""
    effects = EffectRegistry.list_all()
    result = []
    for key, effect in effects.items():
        result.append({
            "key": key,
            "name": effect.name,
            "description": effect.description,
            "category": effect.category,
            "default_params": effect.get_default_params(),
        })
    return {"effects": result}


# ═══════════════════════════════════════════════════════════
# PIPELINE (v2 — unified filter + signing pipeline)
# ═══════════════════════════════════════════════════════════

@router.post("/pipeline/preview")
async def pipeline_preview(body: Dict[str, Any] = Body(...)):
    """
    Generate a preview using the full pipeline (filter stages + signing).
    Processes on the proxy image for speed.
    """
    from engine.pipeline import execute_pipeline

    image_id = body.get("image_id")
    if not image_id or image_id not in _images:
        raise HTTPException(404, "Image not found")

    info = _images[image_id]
    proxy = info["proxy"]
    meta = info["meta"]

    stages = body.get("stages", [])
    signing_configs = body.get("signings")
    if signing_configs is None:
        signing_configs = body.get("signing", {})
    global_intensity = body.get("global_intensity", 1.0)

    print(f"PIPELINE PING - text layers sent: {len(signing_configs) if isinstance(signing_configs, list) else 1}", flush=True)

    # Scale feather for proxy
    scale = info["proxy_scale"]
    
    # Ensure it's a list uniformly for local mutating
    if not isinstance(signing_configs, list):
        signing_configs = [signing_configs]

    # Create deep copies so we don't mutate the original body dictionary
    import copy
    signing_configs_scaled = copy.deepcopy(signing_configs)
    
    for sc in signing_configs_scaled:
        if "layout" in sc:
            sc["layout"]["feather_px"] = sc["layout"].get("feather_px", 2.0) * scale

    # Full resolution for resolution-aware filters
    target_resolution = (info["width"], info["height"])

    result = await asyncio.to_thread(
        execute_pipeline,
        proxy, meta, stages, signing_configs_scaled,
        global_intensity, target_resolution,
    )

    img_bytes = encode_to_bytes(result, "JPEG")
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return {"preview": f"data:image/jpeg;base64,{b64}"}


@router.post("/pipeline/export")
async def pipeline_export(body: Dict[str, Any] = Body(...)):
    """Full-resolution export through the unified pipeline."""
    from engine.pipeline import execute_pipeline

    image_id = body.get("image_id")
    if not image_id or image_id not in _images:
        raise HTTPException(404, "Image not found")

    info = _images[image_id]
    image = info["array"]
    meta = info["meta"]

    stages = body.get("stages", [])
    signing_configs = body.get("signings")
    if signing_configs is None:
        signing_configs = body.get("signing", {})
    global_intensity = body.get("global_intensity", 1.0)
    suffix = body.get("suffix", "__finished")
    include_timestamp = body.get("include_timestamp", False)

    # Ensure signing_configs is a list uniformly
    if not isinstance(signing_configs, list):
        signing_configs = [signing_configs]

    result = await asyncio.to_thread(
        execute_pipeline,
        image, meta, stages, signing_configs,
        global_intensity, None,  # No target_resolution — image IS full res
    )

    # Build output path
    stem = Path(info["filename"]).stem
    ext = Path(info["filename"]).suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if include_timestamp:
        out_name = f"{stem}{suffix}__{timestamp}{ext}"
    else:
        out_name = f"{stem}{suffix}{ext}"

    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Auto-increment filename if it exists
    out_path = OUTPUT_DIR / out_name
    counter = 1
    while out_path.exists():
        if include_timestamp:
            out_name = f"{stem}{suffix}__{timestamp} ({counter}){ext}"
        else:
            out_name = f"{stem}{suffix} ({counter}){ext}"
        out_path = OUTPUT_DIR / out_name
        counter += 1
        
    out_path = str(out_path)

    await asyncio.to_thread(save_image, result, out_path, meta)

    # Save sidecar
    import json
    sidecar = {**body, "source_file": info["filename"]}
    with open(out_path + ".preset.json", "w") as f:
        json.dump(sidecar, f, indent=2)

    return {
        "status": "exported",
        "output_path": out_path,
        "filename": out_name,
    }


# ═══════════════════════════════════════════════════════════
# FILTERS METADATA (for dynamic UI)
# ═══════════════════════════════════════════════════════════

@router.get("/filters")
async def get_filters():
    """List all available filters with their param schemas."""
    from engine.filters.base import FilterRegistry
    filters = FilterRegistry.list_all()
    result = []
    for key, filt in filters.items():
        result.append({
            "key": key,
            "name": filt.name,
            "description": filt.description,
            "family": filt.family,
            "category": filt.category,
            "pre_upscale_safe": filt.pre_upscale_safe,
            "default_params": filt.get_default_params(),
            "param_schema": filt.get_param_schema(),
        })
    return {"filters": result}

