// Theme + constants
export const THEMES = ['darkroom', 'forge', 'gallery'];

export const BLEND_MODES = [
    { value: 'normal', label: 'Normal' },
    { value: 'overlay', label: 'Overlay' },
    { value: 'soft_light', label: 'Soft Light' },
    { value: 'color_burn', label: 'Color Burn' },
    { value: 'multiply', label: 'Multiply' },
    { value: 'screen', label: 'Screen' },
    { value: 'difference', label: 'Difference' },
    { value: 'exclusion', label: 'Exclusion' },
];

export const ANCHORS = [
    { value: 'center', label: 'Center' },
    { value: 'top-left', label: 'Top Left' },
    { value: 'top-right', label: 'Top Right' },
    { value: 'bottom-left', label: 'Bottom Left' },
    { value: 'bottom-right', label: 'Bottom Right' },
];

export const EFFECT_ICONS = {
    difference: '◐',
    luma_invert: '◑',
    channel_invert: '🎨',
    solarize: '☀',
    frosted_glass: '❄',
    duotone: '🎭',
    high_contrast_burn: '🔥',
};

export const EFFECT_CATEGORIES = {
    signature: { label: 'Signature Looks', color: '#FF4500' },
    branding: { label: 'Branding / Engraving', color: '#00E5FF' },
    integrated: { label: 'Integrated Looks', color: '#7C4DFF' },
};

export const DEFAULT_SETTINGS = {
    text: 'LAZART',
    size_rel_width: 0.22,
    x_pct: 0.50,
    y_pct: 0.50,
    anchor: 'center',
    rotation_deg: -8,
    tracking: 0.02,
    feather_px: 2,
    skew_x: 0,
    skew_y: 0,
    perspective_x: 0,
    perspective_y: 0,
    effect_type: 'difference',
    effect_params: { color_rgb: [255, 255, 255] },
    strength: 0.85,
    blend_mode: 'normal',
};

// ── Filter Engine Constants ──────────────────────────────

export const FILTER_FAMILIES = {
    surface: { label: 'Surface Realism', color: '#4CAF50', icon: '🎭' },
    creative: { label: 'Creative', color: '#9C27B0', icon: '🌀' },
    finish: { label: 'Final Finish', color: '#FF9800', icon: '🖨' },
};

export const MASK_SOURCES = [
    { value: 'global', label: 'Global (everywhere)' },
    { value: 'shadows', label: 'Shadows only' },
    { value: 'mids', label: 'Mid-tones only' },
    { value: 'highlights', label: 'Highlights only' },
    { value: 'flat_areas', label: 'Flat areas (anti-plastic)' },
    { value: 'edges', label: 'Edges only' },
];

export const DEFAULT_FILTER_STAGE = {
    type: 'filter',
    filter_key: 'passthrough',
    enabled: true,
    intensity: 1.0,
    blend_mode: 'normal',
    mask_source: 'global',
    mask_params: {},
    mask_modifiers: {
        feather: 0,
        invert: false,
        clamp_min: 0,
        clamp_max: 1,
        noise_breakup: 0,
        border_softness: 0,
    },
    seed: 0,
    params: {},
};

export const DEFAULT_SIGNING_STAGE = {
    type: 'signing',
    enabled: true,
};
