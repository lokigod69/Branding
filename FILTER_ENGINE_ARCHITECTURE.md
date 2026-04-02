# LAZART Filter Engine — Architecture & Implementation Roadmap

## 1. Vision

Extend the existing LAZART Signing Engine into a **unified image finishing studio** with two stage groups:

| Stage Group | Purpose |
|---|---|
| **Filter Engine** | Alters the image itself (surface realism, creative manipulation, final finish) |
| **Signing Engine** | Embeds the mark/logo/text (existing functionality) |

Both live in one pipeline. Both are toggleable. Both are saved in the same preset. Both export together.

The pipeline is:

```
Input → [Filter Stage(s)] → [Signing Stage] → [Final Finish Stage(s)] → Export
```

The user can reorder stages to achieve two key workflows:

- **Mode A — Clean Gallery Finish:** Filter → Sign (signature stays crisp)
- **Mode B — Integrated Art-Object:** Base Filter → Sign → Final Texture Pass (signature gets absorbed into the finish)

---

## 2. Current Architecture Snapshot

### Backend (Python / FastAPI)

| Module | Role |
|---|---|
| `main.py` | FastAPI app, serves SPA + API, runs on port 8001 |
| `api/routes.py` | REST endpoints: upload, preview, export, presets, fonts, effects |
| `api/websocket.py` | WebSocket for batch progress |
| `engine/compositor.py` | Pixel blending with blend modes (normal, overlay, soft_light, etc.) |
| `engine/mask_generator.py` | Text → anti-aliased alpha mask (with skew, perspective, rotation) |
| `engine/io_handler.py` | Image load/save with ICC, EXIF, 16-bit, proxy generation |
| `engine/presets.py` | Pydantic schemas: `PresetSchema` → font, layout, effect, random, export |
| `engine/batch_processor.py` | Async batch processing with progress callbacks |
| `engine/effects/base.py` | `BaseEffect` ABC + `EffectRegistry` (auto-discovers via `EFFECT` module var) |
| `engine/effects/*.py` | 12 effects: difference, channel_invert, duotone, edge_sharpen, emboss, frequency_split, frosted_glass, glass_displacement, high_contrast_burn, luma_invert, micro_contrast, solarize |

### Frontend (React / Vite)

| Module | Role |
|---|---|
| `App.jsx` (1757 lines) | Monolithic component: state, preview logic, canvas, inspector panel |
| `hooks/useApi.js` | REST API wrappers |
| `utils/constants.js` | `DEFAULT_SETTINGS`, blend modes, anchors, effect icons/categories, themes |
| `components/AnalysisMode/` | Print Analysis mode (separate tab) |
| `index.css` | Full design system with CSS variables, 3 themes |

### Current Pipeline

```
Upload → Load (float32) → Generate Text Mask → Apply Effect → Composite (mask × strength) → Save
```

### Current Preset Schema (v1)

```json
{
  "version": 1,
  "name": "...",
  "text": "LAZART",
  "font": { "family": "Arial", "path": null },
  "layout": { "mode": "relative", "size_rel_width": 0.22, "position": {...}, "rotation_deg": -8, ... },
  "effect": { "type": "difference", "params": {...}, "blend_mode": "normal", "strength": 0.85 },
  "random": { "seed": 12345 },
  "export": { "keep_format": true, "suffix": "__signed__diff", "include_timestamp": false }
}
```

---

## 3. Proposed Architecture

### 3.1 Core Concept: The Stage Stack

Instead of a hardcoded `mask → effect → composite` pipeline, introduce a **stage stack** — an ordered list of processing stages that the image flows through. Each stage is one of:

| Stage Type | Description |
|---|---|
| `filter` | A full-image filter (surface realism, creative, or final finish) |
| `signing` | The existing text-mask-based signing pipeline |

The stack is an array in the preset:

```json
{
  "version": 2,
  "name": "Gallery Matte + Sign",
  "stages": [
    { "id": "s1", "type": "filter", "filter_key": "deplasticize", "enabled": true, "intensity": 0.7, "mask_source": "global", "seed": 42, "params": {...} },
    { "id": "s2", "type": "filter", "filter_key": "film_grain", "enabled": true, "intensity": 0.5, "mask_source": "flat_areas", "seed": 100, "params": {...} },
    { "id": "s3", "type": "signing", "enabled": true, ... },
    { "id": "s4", "type": "filter", "filter_key": "gallery_matte", "enabled": false, "intensity": 1.0, "mask_source": "global", "params": {...} }
  ],
  "signing": { "text": "LAZART", "font": {...}, "layout": {...}, "effect": {...} },
  "random": { "seed": 12345 },
  "export": { ... }
}
```

### 3.2 Backend Architecture Changes

#### New Module: `engine/pipeline.py` — Stage Stack Executor

```python
def execute_pipeline(image: np.ndarray, meta: ImageMeta, preset: PresetSchemaV2) -> np.ndarray:
    """Execute the full stage stack on an image."""
    result = image.copy()
    for stage in preset.stages:
        if not stage.enabled:
            continue
        if stage.type == "filter":
            result = execute_filter_stage(result, stage)
        elif stage.type == "signing":
            result = execute_signing_stage(result, meta, preset.signing)
    return result
```

#### New Module: `engine/filters/` — Filter Family (Separate from Signing Effects)

The existing `engine/effects/` stays for **signing effects** (applied within the text mask). The new `engine/filters/` is for **full-image filters** that operate globally or with configurable masks.

```
engine/
├── effects/          # Existing: signing effects (mask-based)
│   ├── base.py       # BaseEffect + EffectRegistry
│   ├── difference.py
│   └── ...
├── filters/          # NEW: full-image filters
│   ├── base.py       # BaseFilter + FilterRegistry
│   ├── surface/      # Pillar 1: Surface Realism
│   │   ├── film_grain.py
│   │   ├── microtexture.py
│   │   ├── edge_deperfection.py
│   │   ├── tonal_desanitize.py
│   │   └── halation.py
│   ├── creative/     # Pillar 2: Region Manipulation
│   │   ├── patch_swap.py
│   │   ├── echo_ghost.py
│   │   ├── flow_warp.py
│   │   ├── cellular_automata.py
│   │   ├── region_contaminate.py
│   │   └── frequency_manipulate.py
│   └── finish/       # Pillar 3: Final Material Finish
│       ├── print_grain.py
│       ├── chromatic_misreg.py
│       ├── dither.py
│       ├── scan_residue.py
│       └── surface_glaze.py
├── regions/          # NEW: Region System (reusable core)
│   ├── base.py       # RegionGenerator ABC + RegionOperator ABC
│   ├── generators/
│   │   ├── grid.py
│   │   ├── voronoi.py
│   │   ├── golden_ratio.py
│   │   ├── radial.py
│   │   ├── random_rects.py
│   │   └── automata_cells.py
│   └── operators/
│       ├── swap.py
│       ├── duplicate.py
│       ├── shift.py
│       ├── blur.py
│       ├── contaminate.py
│       ├── invert.py
│       ├── crossfade.py
│       ├── mirror.py
│       └── displace.py
├── masks/            # NEW: Filter Mask System
│   ├── tonal.py      # shadows_only, mids_only, highlights_only
│   ├── spatial.py    # edges_only, flat_areas_only
│   ├── color.py      # high_saturation, low_saturation
│   ├── procedural.py # noise-based, gradient-based
│   └── composite.py  # combine multiple mask sources
├── pipeline.py       # NEW: Stage stack executor
├── compositor.py     # EXISTING (no changes)
├── mask_generator.py # EXISTING (no changes)
├── io_handler.py     # EXISTING (no changes)
├── presets.py        # MODIFIED: add v2 schema
└── batch_processor.py # MODIFIED: use pipeline
```

#### `BaseFilter` vs `BaseEffect` — Key Difference

```python
# engine/filters/base.py
class BaseFilter(ABC):
    """Full-image filter. Operates on the entire image (or masked region)."""
    
    name: str
    description: str
    family: str  # "surface", "creative", "finish"
    category: str  # specific subcategory
    
    # Whether this filter is safe before upscaling
    pre_upscale_safe: bool = True
    
    @abstractmethod
    def apply(self, image: np.ndarray, params: dict) -> np.ndarray:
        """Apply filter to entire image. Returns modified image."""
        pass
    
    def get_default_params(self) -> dict:
        return {}
    
    def get_param_schema(self) -> list:
        """Return UI-friendly parameter definitions for the frontend."""
        return []
```

Key differences from `BaseEffect`:

- **No mask parameter in `apply()`** — masks are handled by the pipeline executor, which composites the filtered result with the original using the mask
- **`family` field** — groups into surface/creative/finish
- **`pre_upscale_safe` flag** — informs the user about upscaling compatibility
- **`get_param_schema()`** — structured parameter definitions for dynamic UI generation

#### Preset Schema v2

```python
class FilterStageConfig(BaseModel):
    id: str                    # Unique stage ID
    type: Literal["filter"] = "filter"
    filter_key: str            # Registry key
    enabled: bool = True
    intensity: float = 1.0     # 0.0–1.0, overall blend
    mask_source: str = "global"  # global, shadows, mids, highlights, flat_areas, edges, etc.
    mask_params: dict = {}     # Additional mask configuration
    seed: int = 0              # Deterministic randomness
    params: dict = {}          # Filter-specific parameters

class SigningStageConfig(BaseModel):
    id: str
    type: Literal["signing"] = "signing"
    enabled: bool = True

class StageConfig(BaseModel):
    """Union of filter and signing stages."""
    # Resolved at runtime based on 'type'

class SigningConfig(BaseModel):
    """All signing-related settings (text, font, layout, effect)."""
    text: str = "LAZART"
    font: FontConfig = FontConfig()
    layout: LayoutConfig = LayoutConfig()
    effect: EffectConfig = EffectConfig()

class PresetSchemaV2(BaseModel):
    version: int = 2
    name: str = "Custom Preset"
    stages: list = []          # Ordered stage stack
    signing: SigningConfig = SigningConfig()
    random: RandomConfig = RandomConfig()
    export: ExportConfig = ExportConfig()
```

Backward compatibility: if `version == 1`, auto-migrate to v2 by wrapping the signing config into a single signing stage.

### 3.3 Region System Architecture

The Region System is the reusable backbone for creative filters.

```python
# engine/regions/base.py
class RegionMap:
    """A partition of the image into labeled regions."""
    labels: np.ndarray   # (H, W) int array, each pixel labeled 0..N-1
    n_regions: int
    metadata: dict       # e.g., centroids, areas, bounding boxes

class RegionGenerator(ABC):
    @abstractmethod
    def generate(self, width: int, height: int, params: dict) -> RegionMap:
        pass

class RegionOperator(ABC):
    @abstractmethod
    def operate(self, image: np.ndarray, region_map: RegionMap, params: dict) -> np.ndarray:
        pass
```

Region generators partition the image space. Region operators act on the partitions. Creative filters compose these:

```python
# Example: engine/filters/creative/patch_swap.py
class PatchSwapFilter(BaseFilter):
    def apply(self, image, params):
        gen = RegionGeneratorRegistry.get(params.get("region_type", "golden_ratio"))
        region_map = gen.generate(image.shape[1], image.shape[0], params)
        op = RegionOperatorRegistry.get("swap")
        return op.operate(image, region_map, params)
```

### 3.4 Filter Mask System

Every filter stage can be masked. The pipeline executor handles this:

```python
def execute_filter_stage(image, stage):
    filt = FilterRegistry.get(stage.filter_key)
    filtered = filt.apply(image, stage.params)
    
    # Apply mask if not global
    if stage.mask_source != "global":
        mask = generate_filter_mask(image, stage.mask_source, stage.mask_params)
        filtered = image * (1 - mask * stage.intensity) + filtered * (mask * stage.intensity)
    else:
        filtered = image * (1 - stage.intensity) + filtered * stage.intensity
    
    return np.clip(filtered, 0, 1)
```

Available mask sources:

| Mask Source | Logic |
|---|---|
| `global` | Apply everywhere (mask = 1.0) |
| `shadows` | Luminance < threshold |
| `mids` | Luminance in mid range |
| `highlights` | Luminance > threshold |
| `flat_areas` | Low local variance (where AI plastic is most visible) |
| `edges` | High gradient magnitude |
| `high_saturation` | Saturation > threshold |
| `low_saturation` | Saturation < threshold |
| `procedural` | Noise-generated mask |
| `region` | From RegionMap (grid/Voronoi/automata cells) |

### 3.5 Frontend Architecture Changes

The 1757-line `App.jsx` needs to be extended, not restructured (yet). Key additions:

#### New State

```js
// Filter stack state
const [filterStages, setFilterStages] = useState([]);
const [stageOrder, setStageOrder] = useState([]); // ordered IDs
const [filterEngineEnabled, setFilterEngineEnabled] = useState(false);
```

#### Right Panel — Stage Stack UI

The existing Inspector panel gets a new section above the current "Signature Text" section:

```
┌──────────────────────────────┐
│  INSPECTOR                   │
├──────────────────────────────┤
│  ▼ Filter Engine        [ON] │  ← Toggle filter engine
│  ┌────────────────────────┐  │
│  │ ☰ Film Grain     [✓]  │  │  ← Drag handle, toggle, expand
│  │   Amount: ───●────     │  │
│  │   Mask: [Flat Areas ▾] │  │
│  ├────────────────────────┤  │
│  │ ☰ Edge De-Perf  [✓]   │  │
│  │   Strength: ──●───     │  │
│  ├────────────────────────┤  │
│  │ + Add Filter Stage     │  │
│  └────────────────────────┘  │
│                              │
│  ─── · ─── · ─── · ───      │  ← Visual pipeline divider
│                              │
│  ▼ Signing Engine       [ON] │
│  Signature Text              │
│  [LAZART_______________]     │
│  ... (existing controls) ... │
│                              │
│  ─── · ─── · ─── · ───      │
│                              │
│  ▼ Final Finish        [ON]  │  ← Post-signing filters
│  ┌────────────────────────┐  │
│  │ ☰ Gallery Matte  [ ]  │  │
│  │ + Add Finish Stage     │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

#### Preview Pipeline

The preview API call must send the entire stage stack:

```js
const params = {
    image_id: activeImageId,
    pipeline: {
        stages: filterStages.filter(s => s.enabled),
        signing: { text, font_path, size_rel_width, ... },
        stage_order: stageOrder,
    }
};
```

#### New API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /api/pipeline/preview` | Preview with full pipeline (replaces `/api/preview`) |
| `POST /api/pipeline/export` | Export with full pipeline |
| `GET /api/filters` | List available filters with param schemas |
| `GET /api/filters/{key}` | Get filter details and defaults |

The old `/api/preview` and `/api/export` remain for backward compatibility.

### 3.6 Resolution-Aware Processing

For fine-grain filters (film grain, dither, print residue), the filter needs to know the target output resolution to scale its effect correctly:

```python
class BaseFilter(ABC):
    def apply(self, image, params, target_resolution=None):
        """
        target_resolution: (width, height) of final output.
        If None, assume image IS the final resolution.
        For proxy previews, this lets grain scale correctly.
        """
```

This ensures preview-vs-export consistency — a critical requirement.

---

## 4. Implementation Phases

### Phase 1: Foundation (The Plumbing)

**Goal:** Build the infrastructure without any visible filter effects yet. Get the pipeline, registry, mask system, and stage stack working end-to-end.

| Task | Files | Scope |
|---|---|---|
| Create `engine/filters/base.py` | FilterRegistry, BaseFilter ABC | Backend |
| Create `engine/pipeline.py` | `execute_pipeline()`, stage routing | Backend |
| Create `engine/masks/` | Tonal masks (shadows/mids/highlights), flat-area mask | Backend |
| Update `engine/presets.py` | PresetSchemaV2, v1→v2 migration | Backend |
| Add `/api/pipeline/preview` endpoint | `api/routes.py` | Backend |
| Add `/api/filters` endpoint | `api/routes.py` | Backend |
| Add Filter Engine toggle + stage stack UI | `App.jsx` | Frontend |
| Add filter stage card (on/off, intensity, mask selector) | `App.jsx` | Frontend |
| Add drag-to-reorder for stages | `App.jsx` | Frontend |
| Wire preview to use pipeline when filters are active | `App.jsx`, `useApi.js` | Frontend |

**Verification:** Upload an image → Add a "passthrough" test filter → Preview should render identically to original → Reorder stages → Toggle on/off → Save/load preset with v2 schema.

---

### Phase 2: Surface Realism Filters (Pillar 1 — "Deplasticize")

**Goal:** Deliver the most-wanted filters that fix the AI plastic look.

| Filter | File | Key Controls |
|---|---|---|
| Film Grain | `engine/filters/surface/film_grain.py` | amount, size, roughness, chroma_amount, tonal_response, seed |
| Microtexture Reconstruction | `engine/filters/surface/microtexture.py` | scale, contrast, flat_area_sensitivity, edge_protection |
| Edge De-perfection | `engine/filters/surface/edge_deperfection.py` | radius, strength, protect_detail, halo_reduction |
| Tonal Desanitizing | `engine/filters/surface/tonal_desanitize.py` | highlight_rolloff, black_floor, local_contrast_breakup, channel_imbalance |
| Halation / Bloom | `engine/filters/surface/halation.py` | radius, threshold, halation_bias, shadow_safe |

**Starter Presets:**

- "Deplasticize" — microtexture + edge de-perf + tonal breakup + subtle grain
- "Film Breath" — luma grain + slight halation + mild tonal rolloff
- "Dust Memory" — grain + dither + paper residue

**Verification:** Upload an AI-generated image → Apply "Deplasticize" preset → Compare before/after → The image should lose the plastic sheen, look more photographic.

---

### Phase 3: Region System + Creative Filters (Pillar 2 — "Pixel Choreography")

**Goal:** Build the reusable region system and the first creative filters.

| Component | File |
|---|---|
| Region System: base, generators (grid, golden_ratio, voronoi, random_rects, radial) | `engine/regions/` |
| Region Operators: swap, duplicate, shift, blur, contaminate | `engine/regions/operators/` |
| Patch/Quadrant Swap | `engine/filters/creative/patch_swap.py` |
| Echo/Ghost Displacement | `engine/filters/creative/echo_ghost.py` |
| Flow-Field Warping | `engine/filters/creative/flow_warp.py` |
| Cellular Automata Engine | `engine/filters/creative/cellular_automata.py` |
| Region Contamination | `engine/filters/creative/region_contaminate.py` |
| Frequency-Domain Manipulation | `engine/filters/creative/frequency_manipulate.py` |

**Starter Presets:**

- "Golden Swap" — golden-ratio patch exchange
- "Ghost Quadrants" — patch duplication with falloff
- "Cell Drift" — automata activation map controlling blur/invert/displace
- "Flow Scar" — flow-field warp with edge protection  
- "Borrowed Skin" — regional texture contamination

**Verification:** Apply "Golden Swap" to an image → Regions should swap cleanly along golden-ratio partitions. Apply "Flow Scar" → Image should warp coherently along flow field without artifacts.

---

### Phase 4: Final Finish Filters (Pillar 3 — "Material Output")

**Goal:** Filters that make the output feel like a physical object — printed, coated, scanned.

| Filter | File |
|---|---|
| Print Grain / Paper Tooth | `engine/filters/finish/print_grain.py` |
| Chromatic Misregistration | `engine/filters/finish/chromatic_misreg.py` |
| Dither / Tonal Breakup | `engine/filters/finish/dither.py` |
| Scan / Compression Residue | `engine/filters/finish/scan_residue.py` |
| Surface Glaze (matte/gloss/metallic) | `engine/filters/finish/surface_glaze.py` |

**Starter Presets:**

- "Gallery Matte" — matte surface + subtle dither
- "Print Vein" — print grain + micro misregistration  
- "Chrome Ruin" — metallic glaze + heavy grain
- "Scan Phantom" — scan lines + compression artifacts

**Verification:** Apply "Gallery Matte" → Image should feel like a museum print. Toggle before/after.

---

### Phase 5: Advanced Mask System + Polish

**Goal:** Complete the sophistication of masking and polish the UX.

| Feature | Scope |
|---|---|
| Full mask system (procedural, composite, drawn) | Backend |
| Mask preview / visualization in the UI | Frontend |
| Advanced mask controls (feather, invert, combine) | Both |
| Preset browser with filter/signing/combined views | Frontend |
| Stage duplication UI | Frontend |
| Resolution-aware export vs preview consistency | Backend |
| Pre-upscale vs post-upscale filter classification | Both |

---

### Phase 6: UX Polish + Preset Ecosystem

**Goal:** Make it feel finished and professional.

| Feature | Scope |
|---|---|
| Split canvas preview (original / filtered / signed / final) | Frontend |
| Filter parameter presets (sub-presets within a stage) | Both |
| Undo/redo for stage stack changes | Frontend |
| Performance: low-res proxy pipeline, full-res export pipeline match | Backend |
| Combined preset save/load with full stage stack | Both |

---

## 5. Key Design Decisions

### 5.1 Filters vs Effects — Why Separate?

**Effects** (`engine/effects/`) are signing effects. They produce a modified image that the compositor blends **through the text mask**. They answer: "What does the text look like?"

**Filters** (`engine/filters/`) are full-image manipulations. They modify the entire image (or a masked region of it). They answer: "What does the image itself look like?"

They are architecturally different:

- Effects receive `(image, mask, params)` — the mask is the text
- Filters receive `(image, params)` — masking is handled by the pipeline, not the filter

### 5.2 Why Not Just Add All Filters as Effects?

Because effects are composited through the text mask. A film grain effect would only add grain inside the text — useless. Filters need to operate on the whole image.

### 5.3 Backward Compatibility

- v1 presets auto-migrate to v2 (single signing stage, no filter stages)
- Old `/api/preview` and `/api/export` endpoints keep working
- The app detects preset version and handles both

### 5.4 Preview Performance

Full pipeline with 5+ filters will be slow on high-res images. Strategy:

- Use proxy images (already exists: `create_proxy()` generates 1600px max-side)
- Pipeline runs on proxy for interactive preview
- Full-res only on export
- Resolution-aware filters scale their effects for proxy → export consistency

### 5.5 The Upscaling Question

The tool is designed as a pre-Topaz step. Key guidance:

| Filter Category | Pre-Upscale Safe? | Notes |
|---|---|---|
| Surface realism (grain, microtexture, tonal) | ⚠️ Risky | Upscalers may eat fine texture. Need "robust mode" |
| Creative (patch swap, flow warp, contamination) | ✅ Yes | Structural changes survive upscaling |
| Final finish (print grain, dither, misregistration) | ❌ No | These should be post-upscale ideally |

Each filter carries a `pre_upscale_safe` flag. The UI can warn when adding fine-texture filters before an upscale workflow.

---

## 6. Technology Choices

| Area | Choice | Rationale |
|---|---|---|
| Image processing | NumPy + OpenCV + SciPy | Already in use, excellent for pixel manipulation |
| Perlin/Simplex noise | `opensimplex` or `noise` package | For flow fields, procedural masks, grain |
| Voronoi generation | `scipy.spatial.Voronoi` | For region partitioning |
| Cellular automata | Pure NumPy | Fast enough for mask generation |
| Frequency splitting | `numpy.fft` or `scipy.fft` | For frequency-domain manipulations |
| Frontend drag-reorder | HTML5 Drag & Drop or `@dnd-kit` | Native or lightweight library |

### New Python Dependencies

```
opensimplex>=0.4      # Simplex noise for flow fields, procedural masks
scipy>=1.10           # Voronoi, FFT, spatial operations (may already be indirect dep)
```

---

## 7. File-by-File Change Summary

### New Files

| File | Purpose |
|---|---|
| `engine/pipeline.py` | Stage stack executor |
| `engine/filters/base.py` | BaseFilter ABC + FilterRegistry |
| `engine/filters/__init__.py` | Package init |
| `engine/filters/surface/__init__.py` | Surface filter package |
| `engine/filters/surface/film_grain.py` | Luma-aware film grain |
| `engine/filters/surface/microtexture.py` | Smooth-area texture injection |
| `engine/filters/surface/edge_deperfection.py` | Edge de-perfection |
| `engine/filters/surface/tonal_desanitize.py` | Tonal breakup |
| `engine/filters/surface/halation.py` | Subtle highlight bloom |
| `engine/filters/creative/__init__.py` | Creative filter package |
| `engine/filters/creative/patch_swap.py` | Region-based patch swapping |
| `engine/filters/creative/echo_ghost.py` | Displacement echoes |
| `engine/filters/creative/flow_warp.py` | Flow-field warping |
| `engine/filters/creative/cellular_automata.py` | CA-driven mask/activation |
| `engine/filters/creative/region_contaminate.py` | Cross-region texture/color transfer |
| `engine/filters/creative/frequency_manipulate.py` | Frequency band manipulation |
| `engine/filters/finish/__init__.py` | Finish filter package |
| `engine/filters/finish/print_grain.py` | Paper tooth / print grain |
| `engine/filters/finish/chromatic_misreg.py` | Channel offset |
| `engine/filters/finish/dither.py` | Ordered/stochastic dither |
| `engine/filters/finish/scan_residue.py` | Scan/compression artifacts |
| `engine/filters/finish/surface_glaze.py` | Matte/gloss/metallic simulation |
| `engine/regions/base.py` | RegionMap, RegionGenerator ABC, RegionOperator ABC |
| `engine/regions/__init__.py` | Package init |
| `engine/regions/generators/` | Grid, Voronoi, golden ratio, radial, random rects, automata |
| `engine/regions/operators/` | Swap, duplicate, shift, blur, contaminate, invert, crossfade, mirror, displace |
| `engine/masks/tonal.py` | Shadow/mid/highlight masks |
| `engine/masks/spatial.py` | Edge/flat-area masks |
| `engine/masks/color.py` | Saturation-based masks |
| `engine/masks/procedural.py` | Noise-based masks |
| `engine/masks/composite.py` | Combine masks |

### Modified Files

| File | Changes |
|---|---|
| `engine/presets.py` | Add `PresetSchemaV2`, v1→v2 migration, new Pydantic models for stages |
| `engine/batch_processor.py` | Use `execute_pipeline()` instead of direct effect→composite |
| `api/routes.py` | Add `/api/pipeline/preview`, `/api/pipeline/export`, `/api/filters` |
| `frontend/src/App.jsx` | Filter Engine UI panel, stage stack, filter stage cards, pipeline preview |
| `frontend/src/hooks/useApi.js` | New API calls for pipeline preview/export and filter listing |
| `frontend/src/utils/constants.js` | Filter categories, families, default stage configs |
| `frontend/src/index.css` | Stage card styles, filter panel styles |
| `requirements.txt` | Add `opensimplex`, `scipy` |

---

## 8. Example: How a Surface Filter Works

### Film Grain (`engine/filters/surface/film_grain.py`)

```python
import numpy as np
from engine.filters.base import BaseFilter

class FilmGrainFilter(BaseFilter):
    name = "Film Grain"
    description = "Luma-dependent, channel-separated grain with resolution-aware scaling"
    family = "surface"
    category = "grain"
    pre_upscale_safe = False  # Upscalers may eat fine grain
    
    def apply(self, image, params, target_resolution=None):
        amount = params.get("amount", 0.04)
        size = params.get("size", 1.0)
        roughness = params.get("roughness", 0.5)
        chroma_amount = params.get("chroma_amount", 0.3)
        tonal_response = params.get("tonal_response", "shadow_bias")
        seed = params.get("seed", 0)
        
        h, w = image.shape[:2]
        rng = np.random.default_rng(seed)
        
        # Resolution-aware grain scale
        if target_resolution:
            scale_factor = max(target_resolution) / max(h, w)
        else:
            scale_factor = 1.0
        grain_size = max(1, int(size * scale_factor))
        
        # Generate base grain at possibly lower resolution, then upscale
        gh, gw = h // grain_size, w // grain_size
        base_grain = rng.normal(0, 1, (gh, gw)).astype(np.float32)
        
        # Resize to image size (creates clumped grain)
        if grain_size > 1:
            from cv2 import resize, INTER_LINEAR
            base_grain = resize(base_grain, (w, h), interpolation=INTER_LINEAR)
        
        # Roughness: blend between smooth and sharp grain
        if roughness < 1.0:
            from cv2 import GaussianBlur
            smooth = GaussianBlur(base_grain, (3, 3), 1.0)
            base_grain = smooth * (1 - roughness) + base_grain * roughness
        
        # Tonal response: more grain in shadows/mids, less in highlights
        luma = np.mean(image[:, :, :3], axis=2)
        if tonal_response == "shadow_bias":
            response = 1.0 - luma * 0.7  # More in darks
        elif tonal_response == "even":
            response = np.ones_like(luma)
        else:
            response = luma  # More in lights (unusual)
        
        # Apply luma grain
        luma_grain = base_grain * amount * response
        result = image[:, :, :3] + luma_grain[:, :, np.newaxis]
        
        # Chroma grain (separate per channel)
        if chroma_amount > 0:
            for c in range(3):
                ch_grain = rng.normal(0, 1, (h, w)).astype(np.float32)
                result[:, :, c] += ch_grain * amount * chroma_amount * response * 0.5
        
        result = np.clip(result, 0, 1)
        
        if image.shape[2] == 4:
            result = np.concatenate([result, image[:, :, 3:4]], axis=2)
        
        return result
    
    def get_default_params(self):
        return {
            "amount": 0.04,
            "size": 1.0,
            "roughness": 0.5,
            "chroma_amount": 0.3,
            "tonal_response": "shadow_bias",
            "seed": 42,
        }
    
    def get_param_schema(self):
        return [
            {"key": "amount", "label": "Amount", "type": "slider", "min": 0, "max": 0.2, "step": 0.005, "default": 0.04},
            {"key": "size", "label": "Grain Size", "type": "slider", "min": 0.5, "max": 4.0, "step": 0.1, "default": 1.0},
            {"key": "roughness", "label": "Roughness", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.5},
            {"key": "chroma_amount", "label": "Chroma Amount", "type": "slider", "min": 0, "max": 1, "step": 0.05, "default": 0.3},
            {"key": "tonal_response", "label": "Tonal Response", "type": "select", "options": ["shadow_bias", "even", "highlight_bias"], "default": "shadow_bias"},
            {"key": "seed", "label": "Seed", "type": "number", "min": 0, "max": 99999, "default": 42},
        ]

FILTER = FilmGrainFilter()
```

---

## 9. The Unified Preset File

A single preset file saves everything:

```json
{
  "version": 2,
  "name": "Gallery Ready + Sign",
  "stages": [
    {
      "id": "f1",
      "type": "filter",
      "filter_key": "microtexture",
      "enabled": true,
      "intensity": 0.6,
      "mask_source": "flat_areas",
      "mask_params": { "sensitivity": 0.7 },
      "seed": 42,
      "params": { "scale": 2.0, "contrast": 0.3, "edge_protection": true }
    },
    {
      "id": "f2",
      "type": "filter",
      "filter_key": "tonal_desanitize",
      "enabled": true,
      "intensity": 0.5,
      "mask_source": "global",
      "seed": 0,
      "params": { "highlight_rolloff": 0.15, "local_contrast_breakup": 0.3 }
    },
    {
      "id": "s1",
      "type": "signing",
      "enabled": true
    },
    {
      "id": "f3",
      "type": "filter",
      "filter_key": "film_grain",
      "enabled": true,
      "intensity": 0.8,
      "mask_source": "global",
      "seed": 100,
      "params": { "amount": 0.035, "size": 1.2, "roughness": 0.6, "chroma_amount": 0.2 }
    }
  ],
  "signing": {
    "text": "LAZART",
    "font": { "family": "Arial", "path": null },
    "layout": {
      "mode": "relative",
      "size_rel_width": 0.22,
      "position": { "x_pct": 0.5, "y_pct": 0.5, "anchor": "center" },
      "rotation_deg": -8,
      "tracking": 0.02,
      "feather_px": 2
    },
    "effect": {
      "type": "difference",
      "params": { "color_rgb": [255, 255, 255] },
      "blend_mode": "normal",
      "strength": 0.85
    }
  },
  "random": { "seed": 12345 },
  "export": { "keep_format": true, "suffix": "__finished", "include_timestamp": false }
}
```

---

## 10. Summary of Approach

1. **Phase 1** = Build the plumbing (pipeline, registry, masks, stage stack UI)
2. **Phase 2** = Deliver Surface Realism (the "deplasticize" toolkit that people want most)
3. **Phase 3** = Build the Region System + Creative Filters (the unique differentiator)
4. **Phase 4** = Final Finish filters (print/material simulation)
5. **Phase 5** = Advanced masks + polish
6. **Phase 6** = UX ecosystem

Each phase is independently shippable. Each phase adds real value without requiring later phases.

The architecture separates Filters from Effects, introduces a reusable Region System, keeps backward compatibility with v1 presets, and integrates everything into the existing UI without requiring a rewrite.
