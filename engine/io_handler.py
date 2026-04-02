"""
io_handler.py — Image Loading & Saving with Full Fidelity

Handles:
  - EXIF orientation normalization
  - ICC color profile preservation
  - 8-bit and 16-bit bit depth support (float32 internal)
  - RGBA / alpha channel handling
  - Proxy generation for preview rendering
"""

import io
import struct
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageCms, ExifTags
import cv2


# ── Metadata container ─────────────────────────────────────
class ImageMeta:
    """Stores metadata alongside the pixel array."""

    def __init__(
        self,
        original_path: str,
        format: str,
        icc_profile: Optional[bytes],
        bit_depth: int,
        has_alpha: bool,
        original_size: Tuple[int, int],
        exif_data: Optional[bytes] = None,
    ):
        self.original_path = original_path
        self.format = format.upper()
        self.icc_profile = icc_profile
        self.bit_depth = bit_depth
        self.has_alpha = has_alpha
        self.original_size = original_size  # (width, height)
        self.exif_data = exif_data


# ── Load ────────────────────────────────────────────────────
def load_image(path: str) -> Tuple[np.ndarray, ImageMeta]:
    """
    Load an image from disk.

    Returns:
        array: float32 NumPy array, shape (H, W, C), range [0.0, 1.0]
                C = 3 (RGB) or 4 (RGBA)
        meta:  ImageMeta with preserved metadata for round-tripping
    """
    pil_img = Image.open(path)

    # ── EXIF orientation ─────────────────────────────────
    pil_img = _normalize_exif_orientation(pil_img)

    # ── Extract metadata ─────────────────────────────────
    icc_profile = pil_img.info.get("icc_profile")
    exif_data = pil_img.info.get("exif")
    fmt = pil_img.format or Path(path).suffix.lstrip(".").upper()
    if fmt == "JPG":
        fmt = "JPEG"

    # ── Determine bit depth ──────────────────────────────
    mode = pil_img.mode
    bit_depth = 16 if mode in ("I;16", "I;16B", "I;16L", "I;16N") else 8

    # Handle 16-bit images
    if bit_depth == 16:
        arr = np.array(pil_img, dtype=np.float32) / 65535.0
        if arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=-1)
        has_alpha = False
    else:
        # Convert to RGBA or RGB
        has_alpha = mode in ("RGBA", "LA", "PA")
        if has_alpha:
            pil_img = pil_img.convert("RGBA")
        else:
            pil_img = pil_img.convert("RGB")

        arr = np.array(pil_img, dtype=np.float32) / 255.0

    original_size = (pil_img.width, pil_img.height)

    meta = ImageMeta(
        original_path=str(path),
        format=fmt,
        icc_profile=icc_profile,
        bit_depth=bit_depth,
        has_alpha=has_alpha,
        original_size=original_size,
        exif_data=exif_data,
    )

    return arr, meta


# ── Save ────────────────────────────────────────────────────
def save_image(
    array: np.ndarray,
    path: str,
    meta: ImageMeta,
    format_override: Optional[str] = None,
    quality: int = 95,
) -> str:
    """
    Save a float32 array to disk, preserving ICC profile and format.

    Args:
        array: float32 (H, W, 3 or 4), range [0.0, 1.0]
        path: output file path
        meta: ImageMeta from load_image
        format_override: force output format (JPEG, PNG, WEBP, TIFF)
        quality: JPEG/WEBP quality (1-100)

    Returns:
        The resolved output path as string
    """
    out_format = (format_override or meta.format).upper()
    if out_format == "JPG":
        out_format = "JPEG"

    # Clip and convert back to uint
    arr = np.clip(array, 0.0, 1.0)

    if meta.bit_depth == 16 and out_format in ("PNG", "TIFF"):
        arr_int = (arr * 65535.0).astype(np.uint16)
    else:
        arr_int = (arr * 255.0).astype(np.uint8)

    # Handle alpha
    channels = arr_int.shape[2] if arr_int.ndim == 3 else 1
    if channels == 4:
        if out_format == "JPEG":
            # JPEG doesn't support alpha — composite on white
            alpha = arr[:, :, 3:4]
            rgb = arr[:, :, :3] * alpha + (1.0 - alpha)
            arr_int = (np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
            pil_mode = "RGB"
        else:
            pil_mode = "RGBA"
    elif channels == 3:
        pil_mode = "RGB"
    else:
        pil_mode = "L"

    if meta.bit_depth == 16 and out_format in ("PNG", "TIFF") and channels >= 3:
        # For 16-bit, we save via cv2 which handles it natively
        out_path = str(Path(path).resolve())
        if channels == 4:
            cv2_img = cv2.cvtColor(arr_int, cv2.COLOR_RGBA2BGRA)
        else:
            cv2_img = cv2.cvtColor(arr_int, cv2.COLOR_RGB2BGR)
        cv2.imwrite(out_path, cv2_img)
        return out_path

    pil_img = Image.fromarray(arr_int, mode=pil_mode)

    # Build save kwargs
    save_kwargs = {}
    if meta.icc_profile:
        save_kwargs["icc_profile"] = meta.icc_profile
    if out_format == "JPEG":
        save_kwargs["quality"] = quality
        save_kwargs["subsampling"] = 0  # 4:4:4
    elif out_format == "PNG":
        save_kwargs["compress_level"] = 6
    elif out_format == "WEBP":
        save_kwargs["quality"] = quality
        save_kwargs["method"] = 4

    out_path = str(Path(path).resolve())
    pil_img.save(out_path, format=out_format, **save_kwargs)
    return out_path


# ── Proxy ───────────────────────────────────────────────────
def create_proxy(
    array: np.ndarray, max_side: int = 1600
) -> Tuple[np.ndarray, float]:
    """
    Create a downscaled proxy for fast preview.

    Returns:
        proxy_array: downscaled float32 array
        scale_factor: ratio of proxy to original (proxy_side / original_side)
    """
    h, w = array.shape[:2]
    longest = max(h, w)

    if longest <= max_side:
        return array.copy(), 1.0

    scale = max_side / longest
    new_w = int(w * scale)
    new_h = int(h * scale)

    # Use cv2 for high-quality Lanczos resampling
    arr_uint8 = (np.clip(array, 0, 1) * 255).astype(np.uint8)
    resized = cv2.resize(arr_uint8, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    proxy = resized.astype(np.float32) / 255.0

    return proxy, scale


# ── Encode to bytes (for API responses) ────────────────────
def encode_to_bytes(array: np.ndarray, format: str = "PNG") -> bytes:
    """
    Encode a float32 array to image bytes (for sending in API responses).
    """
    arr = np.clip(array, 0.0, 1.0)
    arr_uint8 = (arr * 255.0).astype(np.uint8)

    channels = arr_uint8.shape[2] if arr_uint8.ndim == 3 else 1
    mode = "RGBA" if channels == 4 else "RGB"
    pil_img = Image.fromarray(arr_uint8, mode=mode)

    buf = io.BytesIO()
    save_kwargs = {}
    if format.upper() == "JPEG":
        if mode == "RGBA":
            pil_img = pil_img.convert("RGB")
        save_kwargs["quality"] = 85
    elif format.upper() == "PNG":
        save_kwargs["compress_level"] = 3  # Faster for previews

    pil_img.save(buf, format=format.upper(), **save_kwargs)
    return buf.getvalue()


# ── Internal helpers ────────────────────────────────────────
def _normalize_exif_orientation(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation tag and strip it."""
    try:
        exif = img.getexif()
        orientation_tag = None
        for tag, name in ExifTags.TAGS.items():
            if name == "Orientation":
                orientation_tag = tag
                break

        if orientation_tag is None or orientation_tag not in exif:
            return img

        orientation = exif[orientation_tag]

        transforms = {
            2: (Image.FLIP_LEFT_RIGHT,),
            3: (Image.ROTATE_180,),
            4: (Image.FLIP_TOP_BOTTOM,),
            5: (Image.FLIP_LEFT_RIGHT, Image.ROTATE_90),
            6: (Image.ROTATE_270,),
            7: (Image.FLIP_LEFT_RIGHT, Image.ROTATE_270),
            8: (Image.ROTATE_90,),
        }

        if orientation in transforms:
            for t in transforms[orientation]:
                img = img.transpose(t)

        return img
    except Exception:
        return img
