"""
mask_generator.py — Text → Anti-aliased Alpha Mask

Renders text as a smooth alpha mask suitable for pixel-level compositing.
All positioning uses relative coordinates (percentages) for batch consistency.
"""

import math
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2


# ── Default font fallback ──────────────────────────────────
_DEFAULT_FONT_PATHS = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _find_default_font() -> str:
    for p in _DEFAULT_FONT_PATHS:
        if Path(p).exists():
            return p
    return ""  # Will use Pillow's built-in default


# ── Primary API ─────────────────────────────────────────────
def generate_mask(
    text: str,
    image_width: int,
    image_height: int,
    font_path: Optional[str] = None,
    size_rel_width: float = 0.22,
    x_pct: float = 0.50,
    y_pct: float = 0.50,
    anchor: str = "center",
    rotation_deg: float = 0.0,
    tracking: float = 0.0,
    feather_px: float = 2.0,
    skew_x: float = 0.0,
    skew_y: float = 0.0,
    perspective_x: float = 0.0,
    perspective_y: float = 0.0,
    vertical: bool = False,
    mirror_x: bool = False,
    mirror_y: bool = False,
) -> np.ndarray:
    """
    Generate an anti-aliased alpha mask from text.

    Args:
        text: The text to render (e.g., "LAZART")
        image_width: Target image width in pixels
        image_height: Target image height in pixels
        font_path: Path to .ttf/.otf font file (None = system default)
        size_rel_width: Text width as fraction of image width (0.0–1.0)
        x_pct: Horizontal position as fraction (0.0 = left, 1.0 = right)
        y_pct: Vertical position as fraction (0.0 = top, 1.0 = bottom)
        anchor: Anchor point: "center", "top-left", "top-right", "bottom-left", "bottom-right"
        rotation_deg: Rotation in degrees (counter-clockwise positive)
        tracking: Letter spacing as fraction of font size (0.0 = normal)
        feather_px: Gaussian feather radius in pixels (0 = sharp edges)

    Returns:
        2D float32 array (H, W) with values 0.0–1.0 (anti-aliased)
    """
    # ── Calculate font size from relative width ──────────
    # Render at 4× for superior anti-aliasing, then downscale
    supersample = 4
    canvas_w = image_width * supersample
    canvas_h = image_height * supersample
    target_text_width = image_width * size_rel_width * supersample
    feather_ss = feather_px * supersample

    # Load font and find the right size
    # For vertical text, the "target width" actually determines the vertical length
    font = _load_font_for_size(text, font_path, target_text_width, tracking, vertical)

    # ── Render text onto oversized canvas ────────────────
    text_img = _render_text_image(text, font, tracking, canvas_w, canvas_h, vertical)

    # ── Mirror / Flip ────────────────────────────────────
    if mirror_x:
        text_img = cv2.flip(text_img, 1)  # 1 = horizontal flip
    if mirror_y:
        text_img = cv2.flip(text_img, 0)  # 0 = vertical flip

    # ── Rotate ───────────────────────────────────────────
    if abs(rotation_deg) > 0.01:
        text_img = _rotate_image(text_img, rotation_deg)

    # ── Skew (shear) ────────────────────────────────────
    if abs(skew_x) > 0.01 or abs(skew_y) > 0.01:
        text_img = _skew_image(text_img, skew_x, skew_y)

    # ── Perspective tilt ────────────────────────────────
    if abs(perspective_x) > 0.01 or abs(perspective_y) > 0.01:
        text_img = _perspective_tilt(text_img, perspective_x, perspective_y)

    # ── Position on final canvas ─────────────────────────
    mask_ss = _position_on_canvas(
        text_img, canvas_w, canvas_h, x_pct, y_pct, anchor
    )

    # ── Downscale from supersample ───────────────────────
    mask = cv2.resize(
        mask_ss,
        (image_width, image_height),
        interpolation=cv2.INTER_AREA,
    ).astype(np.float32)

    # ── Feather (Gaussian blur on mask) ──────────────────
    if feather_px > 0.1:
        ksize = int(feather_px * 6) | 1  # Ensure odd kernel
        ksize = max(ksize, 3)
        mask = cv2.GaussianBlur(mask, (ksize, ksize), feather_px)

    return np.clip(mask, 0.0, 1.0)


def generate_per_letter_masks(
    text: str,
    image_width: int,
    image_height: int,
    font_path: Optional[str] = None,
    size_rel_width: float = 0.22,
    x_pct: float = 0.50,
    y_pct: float = 0.50,
    anchor: str = "center",
    rotation_deg: float = 0.0,
    tracking: float = 0.0,
    feather_px: float = 2.0,
    skew_x: float = 0.0,
    skew_y: float = 0.0,
    perspective_x: float = 0.0,
    perspective_y: float = 0.0,
    vertical: bool = False,
    mirror_x: bool = False,
    mirror_y: bool = False,
) -> list:
    """
    Generate individual masks for each character in the text.
    
    Returns a list of (character, mask) tuples where each mask is a
    float32 (H, W) array. Characters are positioned exactly where they
    would appear in the full-text render.
    """
    if not text:
        return []

    supersample = 4
    canvas_w = image_width * supersample
    canvas_h = image_height * supersample
    target_text_width = image_width * size_rel_width * supersample

    font = _load_font_for_size(text, font_path, target_text_width, tracking, vertical)

    # Measure full text dimensions (same as _render_text_image)
    total_width, total_height = _measure_text_dimensions(text, font, tracking, vertical)
    
    # Calculate each character's x and y offset
    char_offsets = []
    x, y = 10, 10
    ascent, descent = font.getmetrics()
    
    for i, char in enumerate(text):
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        char_height = ascent + descent
        
        char_offsets.append((char, x, y, char_width, char_height))
        
        if vertical:
            y += char_height
            if i < len(text) - 1:
                y += int(font.size * tracking)
        else:
            x += char_width
            if i < len(text) - 1:
                x += int(font.size * tracking)

    results = []
    for char, char_x, char_y, char_w, char_h in char_offsets:
        # Render single character on same-size canvas as full text
        img = Image.new("L", (int(total_width) + 20, int(total_height) + 20), 0)
        draw = ImageDraw.Draw(img)
        draw.text((char_x, char_y), char, fill=255, font=font)
        char_img = np.array(img, dtype=np.float32) / 255.0

        # Apply same transforms as generate_mask
        if mirror_x:
            char_img = cv2.flip(char_img, 1)
        if mirror_y:
            char_img = cv2.flip(char_img, 0)
        if abs(rotation_deg) > 0.01:
            char_img = _rotate_image(char_img, rotation_deg)
        if abs(skew_x) > 0.01 or abs(skew_y) > 0.01:
            char_img = _skew_image(char_img, skew_x, skew_y)
        if abs(perspective_x) > 0.01 or abs(perspective_y) > 0.01:
            char_img = _perspective_tilt(char_img, perspective_x, perspective_y)

        # Position on canvas
        mask_ss = _position_on_canvas(
            char_img, canvas_w, canvas_h, x_pct, y_pct, anchor
        )

        # Downscale
        mask = cv2.resize(
            mask_ss, (image_width, image_height),
            interpolation=cv2.INTER_AREA,
        ).astype(np.float32)

        # Feather
        if feather_px > 0.1:
            ksize = int(feather_px * 6) | 1
            ksize = max(ksize, 3)
            mask = cv2.GaussianBlur(mask, (ksize, ksize), feather_px)

        results.append((char, np.clip(mask, 0.0, 1.0)))

    return results



def _load_font_for_size(
    text: str,
    font_path: Optional[str],
    target_size: float,
    tracking: float,
    vertical: bool = False,
) -> ImageFont.FreeTypeFont:
    """Binary-search for the font size that makes text span target_size on its major axis."""
    path = font_path or _find_default_font()

    # Start with an estimate
    lo, hi = 8, 2000
    best_font = None

    for _ in range(20):  # Binary search iterations
        mid = (lo + hi) // 2
        try:
            if path:
                font = ImageFont.truetype(path, mid)
            else:
                font = ImageFont.load_default()
                return font
        except Exception:
            font = ImageFont.load_default()
            return font

        w, h = _measure_text_dimensions(text, font, tracking, vertical)
        major_axis = h if vertical else w
        best_font = font

        if abs(major_axis - target_size) < 2:
            break
        elif major_axis < target_size:
            lo = mid + 1
        else:
            hi = mid - 1

    return best_font or ImageFont.load_default()


def _measure_text_dimensions(text: str, font: ImageFont.FreeTypeFont, tracking: float, vertical: bool = False) -> Tuple[float, float]:
    """Measure total text width and height including tracking."""
    if not text:
        return (0.0, 0.0)

    total_w = 0.0
    total_h = 0.0
    ascent, descent = font.getmetrics()
    char_height = ascent + descent
    
    max_w = 0.0

    for i, char in enumerate(text):
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        
        if vertical:
            total_h += char_height
            max_w = max(max_w, char_width)
            if i < len(text) - 1:
                total_h += font.size * tracking
        else:
            total_w += char_width
            max_w = max(max_w, char_height)
            if i < len(text) - 1:
                total_w += font.size * tracking

    if vertical:
        return (max_w, total_h)
    else:
        return (total_w, max_w)


def _render_text_image(
    text: str,
    font: ImageFont.FreeTypeFont,
    tracking: float,
    canvas_w: int,
    canvas_h: int,
    vertical: bool = False,
) -> np.ndarray:
    """Render text with tracking onto a tight-fit image."""
    # Measure dimensions
    total_w, total_h = _measure_text_dimensions(text, font, tracking, vertical)
    
    # Create image
    img = Image.new("L", (int(total_w) + 20, int(total_h) + 20), 0)
    draw = ImageDraw.Draw(img)

    ascent, descent = font.getmetrics()
    char_height = ascent + descent

    # Draw character by character for tracking
    x = 10
    y = 10
    for i, char in enumerate(text):
        draw.text((x, y), char, fill=255, font=font)
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        
        if vertical:
            y += char_height
            if i < len(text) - 1:
                y += int(font.size * tracking)
        else:
            x += char_width
            if i < len(text) - 1:
                x += int(font.size * tracking)

    return np.array(img, dtype=np.float32) / 255.0


def _rotate_image(arr: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate array around its center, expanding canvas to fit."""
    h, w = arr.shape[:2]
    center = (w / 2, h / 2)

    # Compute rotation matrix
    M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)

    # Compute new bounding box
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)

    # Adjust translation
    M[0, 2] += (new_w - w) / 2
    M[1, 2] += (new_h - h) / 2

    rotated = cv2.warpAffine(
        arr, M, (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return rotated


def _skew_image(arr: np.ndarray, skew_x_deg: float, skew_y_deg: float) -> np.ndarray:
    """Apply 2D shear (skew) transform to the image."""
    h, w = arr.shape[:2]
    sx = math.tan(math.radians(skew_x_deg))
    sy = math.tan(math.radians(skew_y_deg))

    # Compute new dimensions to fit the skewed image
    new_w = int(w + abs(sx) * h)
    new_h = int(h + abs(sy) * w)

    # Build affine shear matrix
    # [1, sx, tx]   tx/ty shift to keep content centered
    # [sy, 1, ty]
    tx = max(0, -sx * h) if sx < 0 else 0
    ty = max(0, -sy * w) if sy < 0 else 0
    # Adjust for centering
    tx += (new_w - w - abs(sx) * h) / 2
    ty += (new_h - h - abs(sy) * w) / 2

    M = np.array([
        [1.0, sx, tx + (abs(sx) * h / 2 if sx < 0 else 0)],
        [sy, 1.0, ty + (abs(sy) * w / 2 if sy < 0 else 0)],
    ], dtype=np.float64)

    result = cv2.warpAffine(
        arr, M, (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return result


def _perspective_tilt(
    arr: np.ndarray, tilt_x_deg: float, tilt_y_deg: float
) -> np.ndarray:
    """
    Apply a perspective tilt to simulate 3D rotation.
    tilt_x_deg: rotation around X axis (tilting forward/backward)
    tilt_y_deg: rotation around Y axis (tilting left/right)
    """
    h, w = arr.shape[:2]

    # Focal length (larger = subtler perspective)
    focal = max(w, h) * 2.0

    # Convert tilt angles to radians
    ax = math.radians(tilt_x_deg)
    ay = math.radians(tilt_y_deg)

    # Source corners: TL, TR, BR, BL
    src = np.array([
        [0, 0], [w, 0], [w, h], [0, h]
    ], dtype=np.float32)

    # Apply perspective projection to each corner
    dst = []
    cx, cy = w / 2, h / 2
    for pt in src:
        x, y = pt[0] - cx, pt[1] - cy
        # Rotate around Y axis
        x2 = x * math.cos(ay)
        z2 = -x * math.sin(ay)
        # Rotate around X axis
        y3 = y * math.cos(ax) - z2 * math.sin(ax)
        z3 = y * math.sin(ax) + z2 * math.cos(ax)
        # Project back to 2D
        scale = focal / (focal + z3)
        px = x2 * scale + cx
        py = y3 * scale + cy
        dst.append([px, py])

    dst = np.array(dst, dtype=np.float32)

    # Compute bounding box of destination
    min_x, min_y = dst.min(axis=0)
    max_x, max_y = dst.max(axis=0)
    new_w = int(math.ceil(max_x - min_x))
    new_h = int(math.ceil(max_y - min_y))

    # Shift destination points so they fit in the new canvas
    dst[:, 0] -= min_x
    dst[:, 1] -= min_y

    M = cv2.getPerspectiveTransform(src, dst)
    result = cv2.warpPerspective(
        arr, M, (new_w, new_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return result


def _position_on_canvas(
    text_img: np.ndarray,
    canvas_w: int,
    canvas_h: int,
    x_pct: float,
    y_pct: float,
    anchor: str,
) -> np.ndarray:
    """Place the text image onto a full-size canvas at the specified position."""
    th, tw = text_img.shape[:2]

    # Canvas position in pixels
    cx = int(canvas_w * x_pct)
    cy = int(canvas_h * y_pct)

    # Anchor offset
    anchor_offsets = {
        "center": (tw // 2, th // 2),
        "top-left": (0, 0),
        "top-right": (tw, 0),
        "bottom-left": (0, th),
        "bottom-right": (tw, th),
    }
    ox, oy = anchor_offsets.get(anchor, (tw // 2, th // 2))

    # Top-left corner of text on canvas
    x0 = cx - ox
    y0 = cy - oy

    # Create output canvas
    canvas = np.zeros((canvas_h, canvas_w), dtype=np.float32)

    # Compute overlap region
    src_x0 = max(0, -x0)
    src_y0 = max(0, -y0)
    dst_x0 = max(0, x0)
    dst_y0 = max(0, y0)

    copy_w = min(tw - src_x0, canvas_w - dst_x0)
    copy_h = min(th - src_y0, canvas_h - dst_y0)

    if copy_w > 0 and copy_h > 0:
        canvas[dst_y0:dst_y0 + copy_h, dst_x0:dst_x0 + copy_w] = \
            text_img[src_y0:src_y0 + copy_h, src_x0:src_x0 + copy_w]

    return canvas


def get_system_fonts() -> list[dict]:
    """List available system fonts (Windows-focused)."""
    fonts = []
    font_dirs = [
        Path("C:/Windows/Fonts"),
        Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",
    ]

    for font_dir in font_dirs:
        if font_dir.exists():
            for f in font_dir.glob("*.ttf"):
                fonts.append({"name": f.stem, "path": str(f)})
            for f in font_dir.glob("*.otf"):
                fonts.append({"name": f.stem, "path": str(f)})

    # Deduplicate by name
    seen = set()
    unique = []
    for f in fonts:
        if f["name"] not in seen:
            seen.add(f["name"])
            unique.append(f)

    return sorted(unique, key=lambda x: x["name"].lower())
