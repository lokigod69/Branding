import React, { useState, useEffect, useCallback, useRef } from 'react';
import { uploadImages, getPresets, getPreset, getEffects, generatePreview, generateMaskPreview, exportImage, batchExport, deleteImage, replaceImage, uploadFont, getCustomFonts, getSystemFonts, pipelinePreview, pipelineExport, getFilters } from './hooks/useApi';
import { DEFAULT_SETTINGS, BLEND_MODES, ANCHORS, EFFECT_ICONS, EFFECT_CATEGORIES, THEMES, DEFAULT_SIGNING_STAGE } from './utils/constants';
import AnalysisMode from './components/AnalysisMode/AnalysisMode';
import StageStackPanel from './components/StageStackPanel.jsx';

function App() {
    // ── State ──────────────────────────────────────────────
    const [images, setImages] = useState([]);
    const [activeImageId, setActiveImageId] = useState(null);
    const [activeImageProxy, setActiveImageProxy] = useState(null);
    const [activeImageDims, setActiveImageDims] = useState({ w: 0, h: 0 });
    const [previewSrc, setPreviewSrc] = useState(null);
    const [maskViewSrc, setMaskViewSrc] = useState(null);
    const [isLoadingPreview, setIsLoadingPreview] = useState(false);

    const [presets, setPresets] = useState([]);
    const [selectedPreset, setSelectedPreset] = useState(null);
    const [effects, setEffects] = useState([]);

    const [showMaskView, setShowMaskView] = useState(false);
    const [compareMode, setCompareMode] = useState(false);
    const [zenMode, setZenMode] = useState(false);
    const [theme, setTheme] = useState('darkroom');

    // App mode: 'signing' or 'analysis'
    const [appMode, setAppMode] = useState('signing');

    // ── Filter Engine state ────────────────────────────────
    const [stages, setStages] = useState(() => [{ ...DEFAULT_SIGNING_STAGE, id: 'signing_default' }]);
    const [globalIntensity, setGlobalIntensity] = useState(1.0);
    const [filterEngineEnabled, setFilterEngineEnabled] = useState(true);
    const [signingEnabled, setSigningEnabled] = useState(true);
    const [availableFilters, setAvailableFilters] = useState([]);

    const [isExporting, setIsExporting] = useState(false);
    const [exportProgress, setExportProgress] = useState(0);
    const [toasts, setToasts] = useState([]);

    const [fonts, setFonts] = useState([]);
    const [systemFonts, setSystemFonts] = useState([]);
    const [fontSearch, setFontSearch] = useState('');
    const [favoriteFonts, setFavoriteFonts] = useState(() => {
        try { return JSON.parse(localStorage.getItem('lse-font-favorites') || '[]'); } catch { return []; }
    });
    const [fontsExpanded, setFontsExpanded] = useState(false);

    const [dragOver, setDragOver] = useState(false);
    const [fontDragOver, setFontDragOver] = useState(false);
    const [showFontModal, setShowFontModal] = useState(false);
    const [showOverlay, setShowOverlay] = useState(true);

    // Zoom & pan state
    const [zoom, setZoom] = useState(1);
    const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
    const [isPanning, setIsPanning] = useState(false);
    const [panStart, setPanStart] = useState({ x: 0, y: 0 });

    // Interactive text overlay state
    const [isDragging, setIsDragging] = useState(false);
    const [isResizing, setIsResizing] = useState(false);
    const [isRotating, setIsRotating] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const [textBoxHover, setTextBoxHover] = useState(false);

    const [transformMode, setTransformMode] = useState('normal');
    const [selectedLetterIdx, setSelectedLetterIdx] = useState(0);

    // ── Layer State ──────────────────────────────────────────
    const defaultLayer = () => ({
        id: crypto.randomUUID(),
        name: 'Layer 1',
        visible: true,
        locked: false,
        fontPath: null,
        perLetterMode: false,
        perLetterEffects: Array.from({ length: 9 }, () => ({
            effect_type: 'difference', effect_params: {}, strength: 0.85, blend_mode: 'normal'
        })),
        ...DEFAULT_SETTINGS,
    });
    const [textLayers, setTextLayers] = useState([defaultLayer()]);
    const [activeLayerId, setActiveLayerId] = useState(textLayers[0]?.id);

    // Aliases mapping to the active layer for backwards compatibility
    const activeLayer = textLayers.find(l => l.id === activeLayerId) || textLayers[0];
    const settings = activeLayer;
    const selectedFont = activeLayer?.fontPath;
    const perLetterMode = activeLayer?.perLetterMode;
    const perLetterEffects = activeLayer?.perLetterEffects || [];

    const updateSetting = useCallback((key, value) => {
        setTextLayers(prev => prev.map(l => l.id === activeLayerId ? { ...l, [key]: value } : l));
    }, [activeLayerId]);

    const setSettings = useCallback((val) => {
        setTextLayers(prev => prev.map(l => {
            if (l.id === activeLayerId) {
                const newVal = typeof val === 'function' ? val(l) : val;
                return { ...l, ...newVal };
            }
            return l;
        }));
    }, [activeLayerId]);

    const setSelectedFont = useCallback((path) => {
        setTextLayers(prev => prev.map(l => l.id === activeLayerId ? { ...l, fontPath: path } : l));
    }, [activeLayerId]);

    const setPerLetterMode = useCallback((val) => {
        setTextLayers(prev => prev.map(l => {
            if (l.id === activeLayerId) {
                const newVal = typeof val === 'function' ? val(l.perLetterMode) : val;
                return { ...l, perLetterMode: newVal };
            }
            return l;
        }));
    }, [activeLayerId]);

    const setPerLetterEffects = useCallback((val) => {
        setTextLayers(prev => prev.map(l => {
            if (l.id === activeLayerId) {
                const newVal = typeof val === 'function' ? val(l.perLetterEffects) : val;
                return { ...l, perLetterEffects: newVal };
            }
            return l;
        }));
    }, [activeLayerId]);

    // Per-image settings storage
    const perImageSettingsRef = useRef({});

    const previewTimeoutRef = useRef(null);
    const fileInputRef = useRef(null);
    const addImagesInputRef = useRef(null);
    const replaceInputRef = useRef(null);
    const fontInputRef = useRef(null);
    const canvasAreaRef = useRef(null);
    const imageRef = useRef(null);

    // ── Theme ──────────────────────────────────────────────
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
    }, [theme]);

    // ── Persist font favorites ────────────────────────────
    useEffect(() => {
        localStorage.setItem('lse-font-favorites', JSON.stringify(favoriteFonts));
    }, [favoriteFonts]);

    function toggleFontFavorite(fontPath) {
        setFavoriteFonts(prev =>
            prev.includes(fontPath) ? prev.filter(p => p !== fontPath) : [...prev, fontPath]
        );
    }

    // ── Load presets and effects on mount ──────────────────
    useEffect(() => {
        loadInit();
    }, []);

    async function loadInit(retries = 5, delayMs = 1000) {
        try {
            const [presetsRes, effectsRes, fontsRes, sysFontsRes, filtersRes] = await Promise.all([
                getPresets(), getEffects(), getCustomFonts(), getSystemFonts(), getFilters()
            ]);
            setPresets(presetsRes.presets || []);
            setEffects(effectsRes.effects || []);
            setFonts(fontsRes.fonts || []);
            setSystemFonts(sysFontsRes.fonts || []);
            setAvailableFilters(filtersRes.filters || []);
        } catch (e) {
            console.error('Init load failed:', e);
            if (retries > 0) {
                console.log(`Retrying init load in ${delayMs}ms. Retries left: ${retries - 1}`);
                setTimeout(() => loadInit(retries - 1, delayMs * 1.5), delayMs);
            } else {
                addToast('Failed to connect to backend server. Please make sure it is running.', 'error');
            }
        }
    }

    // ── Keyboard Shortcuts ─────────────────────────
    useEffect(() => {
        function handleKeyDown(e) {
            // Ignore if in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            // Ctrl+C / Cmd+C or Ctrl+D / Cmd+D or Ctrl+V (Duplicate Active Layer)
            if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'd' || e.key === 'v')) {
                e.preventDefault();
                const active = textLayers.find(l => l.id === activeLayerId);
                if (active) {
                    const newLayer = {
                        ...active,
                        id: crypto.randomUUID(),
                        name: `${active.name} (Copy)`,
                        x_pct: Math.min(0.9, active.x_pct + 0.05),
                        y_pct: Math.min(0.9, active.y_pct + 0.05)
                    };
                    setTextLayers(prev => [...prev, newLayer]);
                    setActiveLayerId(newLayer.id);
                    addToast(`Duplicated layer: ${active.name}`, 'success');
                }
            }

            // Delete key
            if (e.key === 'Delete' || e.key === 'Backspace') {
                if (textLayers.length > 1) {
                    e.preventDefault();
                    setTextLayers(prev => prev.filter(l => l.id !== activeLayerId));
                    setActiveLayerId(textLayers.find(l => l.id !== activeLayerId)?.id);
                    addToast('Deleted text layer', 'success');
                }
            }
        }
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [textLayers, activeLayerId]);

    // ── Preview debounce ───────────────────────────────────
    useEffect(() => {
        if (!activeImageId) return;
        if (isDragging || isResizing || isRotating) return; // Don't preview while interacting
        if (previewTimeoutRef.current) clearTimeout(previewTimeoutRef.current);
        previewTimeoutRef.current = setTimeout(() => {
            requestPreview();
        }, 300);
        return () => clearTimeout(previewTimeoutRef.current);
    }, [activeImageId, textLayers, showMaskView, isDragging, isResizing, isRotating, stages, globalIntensity]);

    async function requestPreview() {
        if (!activeImageId) return;
        setIsLoadingPreview(true);
        try {
            const hasFilterStages = stages.some(s => s.type === 'filter');
            const usePipeline = hasFilterStages || textLayers.length > 1;

            // Route through pipeline when filter stages exist or multiple layers exist
            if (usePipeline) {
                const signings = textLayers.map(l => ({
                    hidden: !l.visible,
                    text: l.text,
                    font: { family: 'Arial', path: l.fontPath },
                    layout: {
                        mode: 'relative',
                        size_rel_width: l.size_rel_width,
                        position: { x_pct: l.x_pct, y_pct: l.y_pct, anchor: l.anchor },
                        rotation_deg: l.rotation_deg,
                        tracking: l.tracking,
                        feather_px: l.feather_px,
                        skew_x: l.skew_x || 0,
                        skew_y: l.skew_y || 0,
                        perspective_x: l.perspective_x || 0,
                        perspective_y: l.perspective_y || 0,
                        vertical: l.vertical || false,
                        mirror_x: l.mirror_x || false,
                        mirror_y: l.mirror_y || false,
                    },
                    effect: {
                        type: l.effect_type,
                        params: l.effect_params,
                        blend_mode: l.blend_mode,
                        strength: l.strength,
                    },
                    base_color_rgb: l.base_color_rgb || [255, 255, 255],
                    ...(l.perLetterMode ? { per_letter_effects: l.perLetterEffects.slice(0, Math.max(l.text.length, 1)) } : {}),
                }));

                const pipelineParams = {
                    image_id: activeImageId,
                    stages: stages,
                    signings: signings,
                    global_intensity: globalIntensity,
                };
                const res = await pipelinePreview(pipelineParams);
                setPreviewSrc(res.preview);
                setMaskViewSrc(null);
            } else {
                // Legacy path: signing-only preview using the active layer
                const activeCfg = textLayers.find(l => l.visible && l.id === activeLayerId) || textLayers.find(l => l.visible) || textLayers[0];
                const params = {
                    image_id: activeImageId,
                    text: activeCfg.text,
                    font_path: activeCfg.fontPath,
                    size_rel_width: activeCfg.size_rel_width,
                    x_pct: activeCfg.x_pct,
                    y_pct: activeCfg.y_pct,
                    anchor: activeCfg.anchor,
                    rotation_deg: activeCfg.rotation_deg,
                    tracking: activeCfg.tracking,
                    feather_px: activeCfg.feather_px,
                    skew_x: activeCfg.skew_x,
                    skew_y: activeCfg.skew_y,
                    perspective_x: activeCfg.perspective_x,
                    perspective_y: activeCfg.perspective_y,
                    vertical: activeCfg.vertical,
                    mirror_x: activeCfg.mirror_x,
                    mirror_y: activeCfg.mirror_y,
                    effect_type: activeCfg.effect_type,
                    effect_params: activeCfg.effect_params,
                    strength: activeCfg.strength,
                    blend_mode: activeCfg.blend_mode,
                    base_color_rgb: activeCfg.base_color_rgb || [255, 255, 255],
                    ...(activeCfg.perLetterMode ? { per_letter_effects: activeCfg.perLetterEffects.slice(0, Math.max(activeCfg.text.length, 1)) } : {}),
                };

                if (showMaskView) {
                    const res = await generateMaskPreview(params);
                    setMaskViewSrc(res.preview);
                } else {
                    const res = await generatePreview(params);
                    setPreviewSrc(res.preview);
                    setMaskViewSrc(null);
                }
            }
        } catch (e) {
            console.error('Preview failed:', e);
        }
        setIsLoadingPreview(false);
    }

    // ── File handling ──────────────────────────────────────
    async function handleFiles(fileList) {
        const imageFiles = Array.from(fileList).filter(f =>
            /\.(jpg|jpeg|png|webp|tiff?|avif)$/i.test(f.name)
        );
        const fontFiles = Array.from(fileList).filter(f =>
            /\.(ttf|otf)$/i.test(f.name)
        );

        if (fontFiles.length > 0) {
            for (const f of fontFiles) {
                try {
                    const res = await uploadFont(f);
                    addToast(`Font "${res.name}" uploaded`, 'success');
                    setSelectedFont(res.path);
                } catch (e) {
                    addToast(`Font upload failed`, 'error');
                }
            }
            const fontsRes = await getCustomFonts();
            setFonts(fontsRes.fonts || []);
        }

        if (imageFiles.length > 0) {
            try {
                const res = await uploadImages(imageFiles);
                const newImages = res.images.filter(i => !i.error);
                setImages(prev => [...prev, ...newImages]);
                if (newImages.length > 0) {
                    setActiveImageId(newImages[0].id);
                    setActiveImageProxy(newImages[0].proxy);
                    setActiveImageDims({ w: newImages[0].width, h: newImages[0].height });
                    setPreviewSrc(null);
                }
            } catch (e) {
                addToast('Upload failed', 'error');
            }
        }
    }

    function handleDrop(e) {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
    }

    // ── Image management ───────────────────────────────────
    async function handleDeleteImage(id, e) {
        e?.stopPropagation();
        try {
            await deleteImage(id);
            // Clean up per-image settings
            delete perImageSettingsRef.current[id];

            setImages(prev => prev.filter(i => i.id !== id));
            if (activeImageId === id) {
                const remaining = images.filter(i => i.id !== id);
                if (remaining.length > 0) {
                    setActiveImageId(remaining[0].id);
                    setActiveImageProxy(remaining[0].proxy);
                    setActiveImageDims({ w: remaining[0].width, h: remaining[0].height });
                    // Restore the next image's settings
                    if (perImageSettingsRef.current[remaining[0].id]) {
                        setTextLayers(perImageSettingsRef.current[remaining[0].id].textLayers);
                        setActiveLayerId(perImageSettingsRef.current[remaining[0].id].activeLayerId);
                    } else {
                        const newDef = [defaultLayer()];
                        setTextLayers(newDef);
                        setActiveLayerId(newDef[0].id);
                    }
                } else {
                    setActiveImageId(null);
                    setActiveImageProxy(null);
                    setPreviewSrc(null);
                    setMaskViewSrc(null);
                    const newDef = [defaultLayer()];
                    setTextLayers(newDef);
                    setActiveLayerId(newDef[0].id);
                }
            }
            addToast('Image removed', 'success');
        } catch (e) {
            addToast('Delete failed', 'error');
        }
    }

    async function handleReplaceImage(id, file) {
        try {
            const res = await replaceImage(id, file);
            setImages(prev => prev.map(i => i.id === id ? { ...i, ...res } : i));
            if (activeImageId === id) {
                setActiveImageProxy(res.proxy);
                setActiveImageDims({ w: res.width, h: res.height });
                setPreviewSrc(null);
            }
            addToast('Image replaced', 'success');
        } catch (e) {
            addToast('Replace failed', 'error');
        }
    }

    function selectImage(img) {
        // Save current image's settings before switching
        if (activeImageId) {
            perImageSettingsRef.current[activeImageId] = { textLayers, activeLayerId };
        }

        setActiveImageId(img.id);
        setActiveImageProxy(img.proxy);
        setActiveImageDims({ w: img.width, h: img.height });
        setPreviewSrc(null);
        setMaskViewSrc(null);

        // Restore the new image's settings, or use defaults
        if (perImageSettingsRef.current[img.id]) {
            setTextLayers(perImageSettingsRef.current[img.id].textLayers);
            setActiveLayerId(perImageSettingsRef.current[img.id].activeLayerId);
        } else {
            const newDef = [defaultLayer()];
            setTextLayers(newDef);
            setActiveLayerId(newDef[0].id);
            perImageSettingsRef.current[img.id] = { textLayers: newDef, activeLayerId: newDef[0].id };
        }
    }

    // ── Preset selection ───────────────────────────────
    async function handlePresetSelect(preset) {
        try {
            const name = preset.filename.replace('.json', '');
            const data = await getPreset(name);
            setSelectedPreset(name);
            // Only apply effect settings — preserve the user's current layout/position
            setSettings(prev => ({
                ...prev,
                effect_type: data.effect?.type ?? prev.effect_type,
                effect_params: data.effect?.params ?? prev.effect_params,
                strength: data.effect?.strength ?? prev.strength,
                blend_mode: data.effect?.blend_mode ?? prev.blend_mode,
            }));
            setPreviewSrc(null); // Force refresh
        } catch (e) {
            console.error('Preset load failed:', e);
        }
    }

    // ── Export ─────────────────────────────────────────────
    async function handleExport() {
        if (!activeImageId) return;
        setIsExporting(true);
        try {
            const usePipeline = stages.some(s => s.type === 'filter') || textLayers.length > 1;
            let res;
            if (usePipeline) {
                const signings = textLayers.map(l => ({
                    hidden: !l.visible,
                    text: l.text,
                    font: { family: 'Arial', path: l.fontPath },
                    layout: {
                        mode: 'relative',
                        size_rel_width: l.size_rel_width,
                        position: { x_pct: l.x_pct, y_pct: l.y_pct, anchor: l.anchor },
                        rotation_deg: l.rotation_deg,
                        tracking: l.tracking,
                        feather_px: l.feather_px,
                        skew_x: l.skew_x || 0,
                        skew_y: l.skew_y || 0,
                        perspective_x: l.perspective_x || 0,
                        perspective_y: l.perspective_y || 0,
                        vertical: l.vertical || false,
                        mirror_x: l.mirror_x || false,
                        mirror_y: l.mirror_y || false,
                    },
                    effect: {
                        type: l.effect_type,
                        params: l.effect_params,
                        blend_mode: l.blend_mode,
                        strength: l.strength,
                    },
                    base_color_rgb: l.base_color_rgb || [255, 255, 255],
                    ...(l.perLetterMode ? { per_letter_effects: l.perLetterEffects.slice(0, Math.max(l.text.length, 1)) } : {}),
                }));

                res = await pipelineExport({
                    image_id: activeImageId,
                    stages: stages,
                    signings: signings,
                    global_intensity: globalIntensity,
                    suffix: `__signed__${settings.effect_type}`,
                });
            } else {
                res = await exportImage({
                    image_id: activeImageId,
                    ...settings,
                    font_path: selectedFont,
                    suffix: `__signed__${settings.effect_type}`,
                    ...(perLetterMode ? { per_letter_effects: perLetterEffects.slice(0, settings.text.length) } : {}),
                });
            }
            addToast(`Exported: ${res.filename}`, 'success');
        } catch (e) {
            addToast('Export failed', 'error');
        }
        setIsExporting(false);
    }

    async function handleBatchExport() {
        if (images.length === 0) return;
        setIsExporting(true);
        setExportProgress(0);

        try {
            const signings = textLayers.map(l => ({
                hidden: !l.visible,
                text: l.text,
                font: { family: 'Arial', path: l.fontPath },
                layout: {
                    mode: 'relative',
                    size_rel_width: l.size_rel_width,
                    position: { x_pct: l.x_pct, y_pct: l.y_pct, anchor: l.anchor },
                    rotation_deg: l.rotation_deg,
                    tracking: l.tracking,
                    feather_px: l.feather_px,
                    skew_x: l.skew_x || 0,
                    skew_y: l.skew_y || 0,
                    perspective_x: l.perspective_x || 0,
                    perspective_y: l.perspective_y || 0,
                    vertical: l.vertical || false,
                    mirror_x: l.mirror_x || false,
                    mirror_y: l.mirror_y || false,
                },
                effect: {
                    type: l.effect_type,
                    params: l.effect_params,
                    blend_mode: l.blend_mode,
                    strength: l.strength,
                },
                base_color_rgb: l.base_color_rgb || [255, 255, 255],
                ...(l.perLetterMode ? { per_letter_effects: l.perLetterEffects.slice(0, Math.max(l.text.length, 1)) } : {}),
            }));

            const preset = {
                version: 1,
                name: 'batch_export',
                signings: signings,
                random: { seed: 12345 },
                export: { keep_format: true, suffix: `__signed__${settings.effect_type}`, include_timestamp: false },
            };

            const res = await batchExport({
                image_ids: images.map(i => i.id),
                preset,
            });

            const successCount = res.results.filter(r => r.status === 'success').length;
            addToast(`Batch complete: ${successCount}/${res.results.length} exported`, 'success');
        } catch (e) {
            addToast('Batch export failed', 'error');
        }
        setIsExporting(false);
    }

    // ── Toast ──────────────────────────────────────────────
    function addToast(text, type = 'success') {
        const id = Date.now();
        setToasts(prev => [...prev, { id, text, type }]);
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
    }

    // ── Setting update helpers ─────────────────────────────
    // Keep per-image settings in sync whenever layers change
    useEffect(() => {
        if (activeImageId) {
            perImageSettingsRef.current[activeImageId] = { textLayers, activeLayerId };
        }
    }, [textLayers, activeLayerId, activeImageId]);

    function updateEffectParam(key, value) {
        setSettings(prev => ({
            ...prev,
            effect_params: { ...prev.effect_params, [key]: value },
        }));
    }

    // ══════════════════════════════════════════════════════
    // INTERACTIVE TEXT BOX — drag, resize, rotate on canvas
    // ══════════════════════════════════════════════════════
    function getImageRect() {
        if (!imageRef.current) return { left: 0, top: 0, width: 0, height: 0 };
        const rect = imageRef.current.getBoundingClientRect();
        return rect;
    }

    // Text box position in pixels on the displayed image
    function getTextBoxPixels(layer) {
        if (!layer) return { cx: 0, cy: 0, textW: 0, textH: 0, displayW: 0, displayH: 0 };
        const rect = getImageRect();
        const displayW = rect.width;
        const displayH = rect.height;
        const textW = displayW * layer.size_rel_width;
        const textH = textW * 0.35; // Approximate aspect ratio for text
        const cx = displayW * layer.x_pct;
        const cy = displayH * layer.y_pct;
        return { cx, cy, textW, textH, displayW, displayH };
    }

    function handleTextMouseDown(e, action, layerId) {
        e.preventDefault();
        e.stopPropagation();

        if (layerId && layerId !== activeLayerId) {
            setActiveLayerId(layerId);
        }

        const targetLayer = textLayers.find(l => l.id === layerId) || activeLayer;
        const rect = getImageRect();
        const px = e.clientX - rect.left;
        const py = e.clientY - rect.top;

        if (action === 'drag') {
            setIsDragging(true);
            if (transformMode === 'skew') {
                setDragStart({ x: px, y: py, startSkewX: targetLayer.skew_x || 0, startSkewY: targetLayer.skew_y || 0, layerId: targetLayer.id });
            } else if (transformMode === 'perspective') {
                setDragStart({ x: px, y: py, startPerspX: targetLayer.perspective_x || 0, startPerspY: targetLayer.perspective_y || 0, layerId: targetLayer.id });
            } else {
                setDragStart({ x: px - rect.width * targetLayer.x_pct, y: py - rect.height * targetLayer.y_pct, layerId: targetLayer.id });
            }
        } else if (action === 'resize') {
            setIsResizing(true);
            setDragStart({ x: px, y: py, startSize: targetLayer.size_rel_width, layerId: targetLayer.id });
        } else if (action === 'rotate') {
            setIsRotating(true);
            const { cx, cy } = getTextBoxPixels(targetLayer);
            const startAngle = Math.atan2(py - cy, px - cx) * (180 / Math.PI);
            setDragStart({ startAngle, startRot: targetLayer.rotation_deg, layerId: targetLayer.id });
        }
    }

    useEffect(() => {
        function handleMouseMove(e) {
            if (!isDragging && !isResizing && !isRotating) return;
            const rect = getImageRect();
            const px = e.clientX - rect.left;
            const py = e.clientY - rect.top;
            const lid = dragStart.layerId;

            // Helper to update specific layer directly
            const updateLayer = (updates) => {
                setTextLayers(prev => prev.map(l => l.id === lid ? { ...l, ...updates } : l));
            };

            if (isDragging) {
                if (transformMode === 'skew') {
                    // Horizontal = skew_x, vertical = skew_y
                    const dx = (px - dragStart.x) / rect.width;
                    const dy = (py - dragStart.y) / rect.height;
                    const newSkewX = Math.max(-45, Math.min(45, dragStart.startSkewX + dx * 60));
                    const newSkewY = Math.max(-45, Math.min(45, dragStart.startSkewY + dy * 60));
                    updateLayer({ skew_x: Math.round(newSkewX * 10) / 10, skew_y: Math.round(newSkewY * 10) / 10 });
                } else if (transformMode === 'perspective') {
                    // Horizontal = perspective_y (rotateY), vertical = perspective_x (rotateX)
                    const dx = (px - dragStart.x) / rect.width;
                    const dy = (py - dragStart.y) / rect.height;
                    const newPerspX = Math.max(-30, Math.min(30, dragStart.startPerspX + dy * 45));
                    const newPerspY = Math.max(-30, Math.min(30, dragStart.startPerspY + dx * 45));
                    updateLayer({ perspective_x: Math.round(newPerspX * 10) / 10, perspective_y: Math.round(newPerspY * 10) / 10 });
                } else {
                    const newX = Math.max(0, Math.min(1, (px - dragStart.x) / rect.width));
                    const newY = Math.max(0, Math.min(1, (py - dragStart.y) / rect.height));
                    updateLayer({ x_pct: newX, y_pct: newY });
                }
            } else if (isResizing) {
                const dx = px - dragStart.x;
                const newSize = Math.max(0.03, Math.min(0.9, dragStart.startSize + dx / rect.width));
                updateLayer({ size_rel_width: newSize });
            } else if (isRotating) {
                const targetLayer = textLayers.find(l => l.id === lid);
                const { cx, cy } = getTextBoxPixels(targetLayer);
                const currentAngle = Math.atan2(py - cy, px - cx) * (180 / Math.PI);
                const delta = currentAngle - dragStart.startAngle;
                let newRot = dragStart.startRot + delta;
                // Snap to 0, 90, -90, 180 if within 5 degrees
                for (const snap of [0, 90, -90, 180, -180, -8]) {
                    if (Math.abs(newRot - snap) < 5) { newRot = snap; break; }
                }
                updateLayer({ rotation_deg: Math.round(newRot) });
            }
        }

        function handleMouseUp() {
            if (isDragging || isResizing || isRotating) {
                setIsDragging(false);
                setIsResizing(false);
                setIsRotating(false);
            }
        }

        if (isDragging || isResizing || isRotating) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
            return () => {
                window.removeEventListener('mousemove', handleMouseMove);
                window.removeEventListener('mouseup', handleMouseUp);
            };
        }
    }, [isDragging, isResizing, isRotating, dragStart, transformMode, textLayers]);

    // ── Render text overlay box ────────────────────────────
    function renderTextOverlay() {
        if (!showOverlay || !activeImageId || !imageRef.current) return null;

        return textLayers.map(layer => {
            if (!layer.visible) return null;
            const { cx, cy, textW, textH } = getTextBoxPixels(layer);
            const halfW = textW / 2;
            const halfH = textH / 2;
            const isTargetActive = activeLayerId === layer.id;
            const isTargetActing = isTargetActive && (isDragging || isResizing || isRotating || (textBoxHover === layer.id));

            return (
                <div
                    key={layer.id}
                    style={{
                        position: 'absolute',
                        left: cx - halfW,
                        top: cy - halfH,
                        width: textW,
                        height: textH,
                        transform: `rotate(${-layer.rotation_deg}deg) skew(${layer.skew_x || 0}deg, ${layer.skew_y || 0}deg)`,
                        perspective: (layer.perspective_x || layer.perspective_y) ? '600px' : 'none',
                        transformOrigin: 'center center',
                        border: `2px ${isTargetActive ? (isTargetActing ? 'solid' : 'dashed') : 'dotted'} ${isTargetActive ? 'var(--accent-ember)' : 'rgba(255,255,255,0.1)'}`,
                        borderRadius: '4px',
                        cursor: isDragging ? 'grabbing' : 'grab',
                        userSelect: 'none',
                        pointerEvents: layer.locked ? 'none' : 'auto',
                        transition: isTargetActing ? 'none' : 'all 0.2s',
                        background: isTargetActive ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
                        zIndex: isTargetActive ? 15 : 10,
                        opacity: isTargetActive ? 1 : 0.4,
                    }}
                    onMouseDown={e => {
                        if (layer.locked) return;
                        handleTextMouseDown(e, 'drag', layer.id);
                    }}
                    onMouseEnter={() => setTextBoxHover(layer.id)}
                    onMouseLeave={() => setTextBoxHover(null)}
                >
                    {isTargetActive && (
                        <>
                            {/* Resize handle — bottom-right */}
                            <div
                                style={{
                                    position: 'absolute', right: -6, bottom: -6, width: 12, height: 12,
                                    background: 'var(--accent-ember)', borderRadius: '2px', cursor: 'nwse-resize',
                                    boxShadow: '0 0 6px rgba(255,69,0,0.5)', zIndex: 20
                                }}
                                onMouseDown={e => handleTextMouseDown(e, 'resize', layer.id)}
                            />

                            {/* Resize handle — bottom-left */}
                            <div
                                style={{
                                    position: 'absolute', left: -6, bottom: -6, width: 12, height: 12,
                                    background: 'var(--accent-ember)', borderRadius: '2px', cursor: 'nesw-resize',
                                    boxShadow: '0 0 6px rgba(255,69,0,0.5)', zIndex: 20
                                }}
                                onMouseDown={e => handleTextMouseDown(e, 'resize', layer.id)}
                            />

                            {/* Rotate handle — top-center */}
                            <div
                                style={{
                                    position: 'absolute', top: -24, left: '50%', transform: 'translateX(-50%)',
                                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0, zIndex: 20
                                }}
                            >
                                <div
                                    style={{
                                        width: 16, height: 16, background: 'var(--accent-cyan)', borderRadius: '50%',
                                        cursor: 'crosshair', boxShadow: '0 0 8px rgba(0,229,255,0.5)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontSize: '9px', color: '#000', fontWeight: 700,
                                    }}
                                    onMouseDown={e => handleTextMouseDown(e, 'rotate', layer.id)}
                                >↻</div>
                                <div style={{ width: 1, height: 6, background: 'rgba(0,229,255,0.4)' }} />
                            </div>

                            {/* Corner dots */}
                            <div style={{ position: 'absolute', left: -4, top: -4, width: 8, height: 8, border: '2px solid var(--accent-ember)', borderRadius: '1px', background: 'var(--bg-base)' }} />
                            <div style={{ position: 'absolute', right: -4, top: -4, width: 8, height: 8, border: '2px solid var(--accent-ember)', borderRadius: '1px', background: 'var(--bg-base)' }} />
                        </>
                    )}
                </div>
            );
        });
    }

    // ── Get current effect info ────────────────────────────
    const currentEffect = effects.find(e => e.key === settings.effect_type);

    // ── Filtered fonts ─────────────────────────────────────
    const filteredSystemFonts = fontSearch
        ? systemFonts.filter(f => f.name.toLowerCase().includes(fontSearch.toLowerCase()))
        : systemFonts;

    // ── Render ─────────────────────────────────────────────
    return (
        <div className={zenMode ? 'zen-mode' : ''} style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
            {/* ── Floating Zen Exit ───────────────────────────── */}
            {zenMode && (
                <button
                    onClick={() => setZenMode(false)}
                    style={{
                        position: 'fixed', top: 16, right: 16, zIndex: 9999,
                        background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(10px)',
                        border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8,
                        color: '#fff', padding: '8px 16px', fontSize: '0.82rem',
                        cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
                        transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => { e.target.style.background = 'rgba(255,69,0,0.6)'; e.target.style.borderColor = 'var(--accent-ember)'; }}
                    onMouseLeave={e => { e.target.style.background = 'rgba(0,0,0,0.75)'; e.target.style.borderColor = 'rgba(255,255,255,0.15)'; }}
                >
                    ✕ Exit Zen
                </button>
            )}

            {/* ── HEADER ──────────────────────────────────────── */}
            <header className="app-header">
                <div className="app-logo">
                    <h1>LAZART</h1>
                    <span className="subtitle">{appMode === 'signing' ? 'Signing Engine' : 'Print Analysis'}</span>
                </div>

                {/* ── Mode Switcher ────────────────────────────── */}
                <div className="mode-switcher">
                    <button
                        className={`mode-tab ${appMode === 'signing' ? 'active' : ''}`}
                        onClick={() => setAppMode('signing')}
                    >
                        🖊 Signing Engine
                    </button>
                    <button
                        className={`mode-tab ${appMode === 'analysis' ? 'active' : ''}`}
                        onClick={() => setAppMode('analysis')}
                    >
                        📐 Print Analysis
                    </button>
                </div>

                <div className="header-controls">
                    {appMode === 'signing' && (
                        <>
                            <button className="btn btn-sm" onClick={() => setCompareMode(!compareMode)}
                                title="Side-by-side before/after comparison"
                                style={compareMode ? { borderColor: 'var(--accent-ember)', color: 'var(--accent-ember)' } : {}}>
                                {compareMode ? '◧ Compare On' : '◧ Compare'}
                            </button>
                            <button className="btn btn-sm" onClick={() => setShowMaskView(!showMaskView)}
                                title="Shows the text mask overlay in red — useful for precise placement"
                                style={showMaskView ? { borderColor: 'var(--accent-cyan)', color: 'var(--accent-cyan)' } : {}}>
                                {showMaskView ? '◉ Mask View On' : '◉ Mask View'}
                            </button>
                            <button className="btn btn-sm" onClick={() => setZenMode(!zenMode)}
                                title="Hide all panels, show only the canvas">
                                {zenMode ? '⊞ Exit Zen' : '⊡ Zen'}
                            </button>
                        </>
                    )}
                    <select value={theme} onChange={e => setTheme(e.target.value)}
                        style={{ padding: '4px 8px', background: 'var(--bg-base)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-sm)', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                        {THEMES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                    </select>
                </div>
            </header>

            {/* ── MAIN AREA ───────────────────────────────────── */}
            {appMode === 'analysis' ? (
                <AnalysisMode />
            ) : (
                <>
                    <div className="app-main">
                        {/* ── LEFT PANEL: Presets ─────────────────────────── */}
                        <aside className={`panel-left ${zenMode ? 'hidden' : ''}`}>
                            <div className="panel-header">
                                <h2>Effects</h2>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{presets.length} available</span>
                            </div>
                            <div className="panel-body">
                                <div className="preset-grid">
                                    {presets.map((preset, idx) => {
                                        const letters = 'LAZART';
                                        const letter = letters[idx % letters.length];

                                        const effectStyles = {
                                            difference: { filter: 'invert(1)', color: '#fff', background: 'linear-gradient(135deg, #1a1a2e, #3a3a5e)' },
                                            luma_invert: { filter: 'invert(1) saturate(0)', color: '#ddd', background: 'linear-gradient(135deg, #2a2a2a, #555)' },
                                            channel_invert: { filter: 'invert(1) hue-rotate(180deg)', color: '#ff6b6b', background: 'linear-gradient(135deg, #1a0a0a, #3a1a1a)' },
                                            solarize: { filter: 'contrast(1.8) saturate(1.5)', color: '#ffaa00', background: 'linear-gradient(135deg, #1a1a00, #3a3a1a)' },
                                            frosted_glass: { filter: 'blur(0.5px) brightness(1.2)', color: 'rgba(255,255,255,0.7)', background: 'linear-gradient(135deg, #1a2a3a, #2a4a5a)' },
                                            duotone: { color: '#ffc864', background: 'linear-gradient(135deg, #141450, #ffc864)' },
                                            high_contrast_burn: { filter: 'contrast(2.5) brightness(0.8)', color: '#ff4400', background: 'linear-gradient(135deg, #0a0a0a, #1a0a0a)' },
                                        };
                                        const es = effectStyles[preset.effect_type] || { color: '#aaa', background: '#222' };

                                        return (
                                            <div key={preset.filename}
                                                className={`preset-cube ${selectedPreset === preset.filename.replace('.json', '') ? 'selected' : ''}`}
                                                style={{ background: es.background }}
                                                onClick={() => handlePresetSelect(preset)}>
                                                <span className="cube-letter" style={{
                                                    color: es.color,
                                                    filter: es.filter || 'none',
                                                    textShadow: es.textShadow || 'none',
                                                }}>{letter}</span>
                                                <span className="cube-name">{preset.name}</span>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </aside>

                        {/* ── CENTER: Canvas ─────────────────────────────── */}
                        <main className="canvas-area"
                            ref={canvasAreaRef}
                            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                            onDragLeave={() => setDragOver(false)}
                            onDrop={handleDrop}>
                            {!activeImageId ? (
                                <div className={`dropzone ${dragOver ? 'active' : ''}`}
                                    onClick={() => fileInputRef.current?.click()}>
                                    <div className="dropzone-icon">🖼</div>
                                    <h3>Drop your artwork here</h3>
                                    <p>JPG, PNG, WEBP, TIFF — single or multiple files</p>
                                    <p style={{ marginTop: 8, color: 'var(--accent-cyan)', fontSize: '0.75rem' }}>
                                        You can also drop .ttf/.otf font files
                                    </p>
                                    <input ref={fileInputRef} type="file" multiple accept="image/*,.ttf,.otf"
                                        style={{ display: 'none' }}
                                        onChange={e => handleFiles(e.target.files)} />
                                </div>
                            ) : (
                                <div className="canvas-container">
                                    {compareMode ? (
                                        <div style={{ display: 'flex', position: 'relative', maxHeight: 'calc(100vh - 260px)', gap: 2 }}>
                                            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                <img src={activeImageProxy} alt="Before"
                                                    style={{ maxWidth: '100%', maxHeight: 'calc(100vh - 280px)', objectFit: 'contain' }} />
                                                <span className="compare-label before">BEFORE</span>
                                            </div>
                                            <div style={{ width: 2, background: 'var(--accent-ember)', flexShrink: 0 }} />
                                            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                <img src={showMaskView ? maskViewSrc : previewSrc || activeImageProxy} alt="After"
                                                    style={{ maxWidth: '100%', maxHeight: 'calc(100vh - 280px)', objectFit: 'contain' }} />
                                                <span className="compare-label after">AFTER</span>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="canvas-wrapper animate-in"
                                            style={{
                                                position: 'relative', overflow: 'hidden',
                                                cursor: zoom > 1 ? (isPanning ? 'grabbing' : 'grab') : 'default',
                                            }}
                                            onWheel={e => {
                                                e.preventDefault();
                                                const delta = e.deltaY > 0 ? -0.15 : 0.15;
                                                setZoom(prev => {
                                                    const next = Math.max(0.25, Math.min(8, prev + delta * prev));
                                                    if (next <= 1) setPanOffset({ x: 0, y: 0 });
                                                    return next;
                                                });
                                            }}
                                            onMouseDown={e => {
                                                if (zoom > 1 && !textBoxHover && !isDragging && !isResizing && !isRotating) {
                                                    setIsPanning(true);
                                                    setPanStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
                                                }
                                            }}
                                            onMouseMove={e => {
                                                if (isPanning) {
                                                    setPanOffset({
                                                        x: e.clientX - panStart.x,
                                                        y: e.clientY - panStart.y,
                                                    });
                                                }
                                            }}
                                            onMouseUp={() => setIsPanning(false)}
                                            onMouseLeave={() => setIsPanning(false)}
                                            onDoubleClick={() => { setZoom(1); setPanOffset({ x: 0, y: 0 }); }}
                                        >
                                            <div style={{
                                                transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoom})`,
                                                transformOrigin: 'center center',
                                                transition: isPanning ? 'none' : 'transform 0.15s ease-out',
                                                position: 'relative',
                                                display: 'inline-block',
                                            }}>
                                                <img
                                                    ref={imageRef}
                                                    src={showMaskView ? (maskViewSrc || activeImageProxy) : (previewSrc || activeImageProxy)}
                                                    alt="Preview"
                                                    style={{ maxWidth: '100%', maxHeight: 'calc(100vh - 260px)', objectFit: 'contain', display: 'block' }}
                                                    draggable={false}
                                                />
                                                {/* Interactive text overlay */}
                                                {renderTextOverlay()}
                                            </div>

                                            {/* Loading indicator */}
                                            {isLoadingPreview && (
                                                <div style={{
                                                    position: 'absolute', top: 8, left: 8,
                                                    background: 'rgba(0,0,0,0.7)', borderRadius: 'var(--radius-sm)',
                                                    padding: '4px 10px', fontSize: '0.7rem', color: 'var(--accent-ember)',
                                                    zIndex: 20,
                                                }}>
                                                    Rendering...
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Floating actions */}
                                    <div style={{ position: 'absolute', top: 12, right: 12, display: 'flex', gap: 6, zIndex: 20 }}>
                                        <button
                                            className="btn btn-sm"
                                            onClick={() => setShowOverlay(!showOverlay)}
                                            title={showOverlay ? 'Hide text overlay controls' : 'Show text overlay controls'}
                                            style={showOverlay ? {} : { borderColor: 'var(--accent-cyan)', color: 'var(--accent-cyan)' }}
                                        >
                                            {showOverlay ? '👁 Hide Box' : '👁‍🗨 Show Box'}
                                        </button>
                                        {zoom !== 1 && (
                                            <button className="btn btn-sm" onClick={() => { setZoom(1); setPanOffset({ x: 0, y: 0 }); }}
                                                title="Reset zoom to fit">
                                                🔍 Fit
                                            </button>
                                        )}
                                        <button className="btn btn-sm" onClick={() => addImagesInputRef.current?.click()}>
                                            + Add Images
                                        </button>
                                        <input ref={addImagesInputRef} type="file" multiple accept="image/*,.ttf,.otf"
                                            style={{ display: 'none' }}
                                            onChange={e => handleFiles(e.target.files)} />
                                    </div>

                                    {/* Image info bar */}
                                    <div style={{
                                        position: 'absolute', bottom: 8, left: 8,
                                        background: 'rgba(0,0,0,0.7)', borderRadius: 'var(--radius-sm)',
                                        padding: '4px 10px', fontSize: '0.7rem', color: 'var(--text-muted)',
                                        fontFamily: 'var(--font-mono)', zIndex: 20,
                                        display: 'flex', gap: 10, alignItems: 'center',
                                    }}>
                                        <span>{activeImageDims.w}×{activeImageDims.h}</span>
                                        <span style={{ color: zoom !== 1 ? 'var(--accent-ember)' : 'var(--text-muted)' }}>
                                            {Math.round(zoom * 100)}%
                                        </span>
                                    </div>
                                </div>
                            )}
                        </main>

                        {/* ── RIGHT PANEL: Inspector ─────────────────────── */}
                        <aside className={`panel-right ${zenMode ? 'hidden' : ''}`}>
                            <div className="panel-header">
                                <h2>Inspector</h2>
                            </div>
                            <div className="panel-body">
                                {/* ── Layers Panel ────────────────────────────── */}
                                <div className="section-title" style={{ marginTop: 0 }}>Text Layers</div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 12 }}>
                                    {textLayers.map((layer, i) => (
                                        <div key={layer.id}
                                            style={{
                                                display: 'flex', alignItems: 'center', gap: 8,
                                                padding: '6px 8px', borderRadius: '4px',
                                                background: layer.id === activeLayerId ? 'var(--accent-ember-soft)' : 'var(--bg-base)',
                                                border: `1px solid ${layer.id === activeLayerId ? 'var(--accent-ember)' : 'var(--border-medium)'}`,
                                                cursor: 'pointer'
                                            }}
                                            onClick={() => setActiveLayerId(layer.id)}
                                        >
                                            <button className="btn btn-sm" style={{ padding: '2px 4px', background: 'transparent', border: 'none', color: layer.visible ? 'var(--accent-cyan)' : 'var(--text-muted)' }}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setTextLayers(prev => prev.map(l => l.id === layer.id ? { ...l, visible: !l.visible } : l));
                                                }}>
                                                {layer.visible ? '👁' : '—'}
                                            </button>
                                            <span style={{ flex: 1, fontSize: '0.8rem', color: layer.id === activeLayerId ? '#fff' : 'var(--text-secondary)' }}>
                                                {layer.name || `Layer ${i + 1}`}
                                            </span>
                                            <button className="btn btn-sm btn-danger" style={{ padding: '2px 4px' }}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    if (textLayers.length > 1) {
                                                        setTextLayers(prev => prev.filter(l => l.id !== layer.id));
                                                        if (activeLayerId === layer.id) {
                                                            setActiveLayerId(textLayers.find(l => l.id !== layer.id)?.id);
                                                        }
                                                    }
                                                }}
                                                disabled={textLayers.length === 1}
                                            >✕</button>
                                        </div>
                                    ))}
                                    <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                                        <button className="btn btn-sm" style={{ flex: 1 }}
                                            onClick={() => {
                                                const newLayer = { ...defaultLayer(), id: crypto.randomUUID(), name: `Layer ${textLayers.length + 1}` };
                                                setTextLayers(prev => [...prev, newLayer]);
                                                setActiveLayerId(newLayer.id);
                                            }}
                                        >+ Add Layer</button>
                                        <button className="btn btn-sm" style={{ flex: 1 }}
                                            onClick={() => {
                                                const active = textLayers.find(l => l.id === activeLayerId);
                                                if (active) {
                                                    const newLayer = {
                                                        ...active,
                                                        id: crypto.randomUUID(),
                                                        name: `${active.name} (Copy)`,
                                                        x_pct: Math.min(0.9, active.x_pct + 0.05),
                                                        y_pct: Math.min(0.9, active.y_pct + 0.05)
                                                    };
                                                    setTextLayers(prev => [...prev, newLayer]);
                                                    setActiveLayerId(newLayer.id);
                                                }
                                            }}
                                        >⧉ Duplicate</button>
                                    </div>
                                </div>
                                <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 12, marginTop: -6 }}>
                                    <em>Tips: Click a layer to edit it. You can also press Ctrl+C or Ctrl+V to copy the active layer, and Delete to remove it.</em>
                                </p>
                                <div className="section-divider" />

                                {/* ── Pipeline Stage Stack ──────────────────── */}
                                <StageStackPanel
                                    stages={stages}
                                    setStages={setStages}
                                    globalIntensity={globalIntensity}
                                    setGlobalIntensity={setGlobalIntensity}
                                    filterEngineEnabled={filterEngineEnabled}
                                    setFilterEngineEnabled={setFilterEngineEnabled}
                                    signingEnabled={signingEnabled}
                                    setSigningEnabled={setSigningEnabled}
                                    availableFilters={availableFilters}
                                    onPreviewRequested={() => requestPreview()}
                                />

                                <div className="section-divider" />

                                {/* ── Text & Color ──────────────────────────────── */}
                                <div className="section-title">Signature Settings</div>
                                <div className="input-group">
                                    <label>Text</label>
                                    <input type="text" value={settings.text}
                                        onChange={e => updateSetting('text', e.target.value)} />
                                </div>
                                <div className="color-input-group" style={{ marginBottom: 12 }}>
                                    <label>Base Color</label>
                                    <div className="color-swatch-row">
                                        <input type="color"
                                            value={`#${(settings.base_color_rgb || [255, 255, 255]).map(c => c.toString(16).padStart(2, '0')).join('')}`}
                                            onChange={e => {
                                                const hex = e.target.value;
                                                const r = parseInt(hex.slice(1, 3), 16);
                                                const g = parseInt(hex.slice(3, 5), 16);
                                                const b = parseInt(hex.slice(5, 7), 16);
                                                updateSetting('base_color_rgb', [r, g, b]);
                                            }} />
                                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                                            {(settings.base_color_rgb || [255, 255, 255]).join(', ')}
                                        </span>
                                    </div>
                                    <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.3 }}>
                                        Used as the primary color for the typography. Some effects (like Duotone) may override this.
                                    </p>
                                </div>

                                {/* ── Font ──────────────────────────────────── */}
                                <div
                                    style={{
                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                        cursor: 'pointer', marginBottom: fontsExpanded ? 6 : 10
                                    }}
                                    onClick={() => setFontsExpanded(!fontsExpanded)}
                                >
                                    <div className="section-title" style={{ marginBottom: 0 }}>Font</div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                        {!fontsExpanded && (
                                            <span style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', fontStyle: 'italic', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {selectedFont ? (fonts.find(f => f.path === selectedFont)?.name || systemFonts.find(f => f.path === selectedFont)?.name || 'Custom') : 'System Default'}
                                            </span>
                                        )}
                                        <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                                            {fontsExpanded ? '▲ Collapse' : '▼ Expand'}
                                        </span>
                                    </div>
                                </div>

                                {fontsExpanded && (
                                    <>
                                        <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 6 }}>
                                            <input
                                                type="text"
                                                placeholder="Search fonts..."
                                                value={fontSearch}
                                                onChange={e => setFontSearch(e.target.value)}
                                                style={{
                                                    flex: 1, padding: '6px 10px', fontSize: '0.78rem',
                                                    background: 'var(--bg-base)', border: '1px solid var(--border-medium)',
                                                    borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
                                                    fontFamily: 'var(--font-sans)', outline: 'none',
                                                }}
                                            />
                                            <button
                                                className="btn btn-sm"
                                                onClick={() => fontInputRef.current?.click()}
                                                title="Upload a .ttf or .otf font file"
                                                style={{ padding: '6px 8px' }}
                                            >
                                                📁
                                            </button>
                                            <input ref={fontInputRef} type="file" accept=".ttf,.otf" style={{ display: 'none' }}
                                                onChange={e => handleFiles(e.target.files)} />
                                        </div>

                                        {/* Embedded scrollable font list */}
                                        <div style={{
                                            maxHeight: 200, overflowY: 'auto', overflowX: 'hidden',
                                            background: 'var(--bg-base)', border: '1px solid var(--border-subtle)',
                                            borderRadius: 'var(--radius-sm)', marginBottom: 8,
                                        }}>
                                            {/* System Default */}
                                            <div
                                                onClick={() => setSelectedFont(null)}
                                                style={{
                                                    padding: '7px 12px', cursor: 'pointer', fontSize: '0.82rem',
                                                    display: 'flex', alignItems: 'center',
                                                    background: selectedFont === null ? 'var(--accent-ember-soft)' : 'transparent',
                                                    borderLeft: selectedFont === null ? '3px solid var(--accent-ember)' : '3px solid transparent',
                                                    color: 'var(--text-secondary)', fontStyle: 'italic',
                                                    transition: 'background 0.12s',
                                                }}
                                                onMouseEnter={e => { if (selectedFont !== null) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                                                onMouseLeave={e => { if (selectedFont !== null) e.currentTarget.style.background = 'transparent'; }}
                                            >
                                                System Default
                                            </div>

                                            {/* Favorites */}
                                            {favoriteFonts.length > 0 && (() => {
                                                const favFonts = [...fonts, ...systemFonts].filter(f => favoriteFonts.includes(f.path));
                                                const filtered = fontSearch
                                                    ? favFonts.filter(f => f.name.toLowerCase().includes(fontSearch.toLowerCase()))
                                                    : favFonts;
                                                if (filtered.length === 0) return null;
                                                return (
                                                    <>
                                                        <div style={{
                                                            padding: '6px 12px 3px', fontSize: '0.62rem', fontWeight: 700,
                                                            color: '#FFD700', textTransform: 'uppercase', letterSpacing: '0.08em',
                                                        }}>★ Favorites</div>
                                                        {filtered.map(f => (
                                                            <div key={'ef-' + f.path}
                                                                onClick={() => setSelectedFont(f.path)}
                                                                style={{
                                                                    padding: '6px 12px', cursor: 'pointer', fontSize: '0.82rem',
                                                                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                                    background: selectedFont === f.path ? 'var(--accent-ember-soft)' : 'transparent',
                                                                    borderLeft: selectedFont === f.path ? '3px solid var(--accent-ember)' : '3px solid transparent',
                                                                    transition: 'background 0.12s',
                                                                }}
                                                                onMouseEnter={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                                                                onMouseLeave={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'transparent'; }}
                                                            >
                                                                <span style={{ flex: 1 }}>{f.name}</span>
                                                                <span
                                                                    onClick={e => { e.stopPropagation(); toggleFontFavorite(f.path); }}
                                                                    style={{ cursor: 'pointer', fontSize: '0.9rem', color: '#FFD700' }}
                                                                >★</span>
                                                            </div>
                                                        ))}
                                                    </>
                                                );
                                            })()}

                                            {/* Custom fonts */}
                                            {(() => {
                                                const filtered = fontSearch
                                                    ? fonts.filter(f => f.name.toLowerCase().includes(fontSearch.toLowerCase()))
                                                    : fonts;
                                                if (filtered.length === 0) return null;
                                                return (
                                                    <>
                                                        <div style={{
                                                            padding: '6px 12px 3px', fontSize: '0.62rem', fontWeight: 700,
                                                            color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.08em',
                                                        }}>Custom ({filtered.length})</div>
                                                        {filtered.map(f => (
                                                            <div key={'ec-' + f.path}
                                                                onClick={() => setSelectedFont(f.path)}
                                                                style={{
                                                                    padding: '6px 12px', cursor: 'pointer', fontSize: '0.82rem',
                                                                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                                    background: selectedFont === f.path ? 'var(--accent-ember-soft)' : 'transparent',
                                                                    borderLeft: selectedFont === f.path ? '3px solid var(--accent-ember)' : '3px solid transparent',
                                                                    transition: 'background 0.12s',
                                                                }}
                                                                onMouseEnter={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                                                                onMouseLeave={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'transparent'; }}
                                                            >
                                                                <span style={{ flex: 1 }}>{f.name}</span>
                                                                <span
                                                                    onClick={e => { e.stopPropagation(); toggleFontFavorite(f.path); }}
                                                                    style={{ cursor: 'pointer', fontSize: '0.9rem', color: favoriteFonts.includes(f.path) ? '#FFD700' : 'var(--text-muted)' }}
                                                                >{favoriteFonts.includes(f.path) ? '★' : '☆'}</span>
                                                            </div>
                                                        ))}
                                                    </>
                                                );
                                            })()}

                                            {/* System fonts */}
                                            <div style={{
                                                padding: '6px 12px 3px', fontSize: '0.62rem', fontWeight: 700,
                                                color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em',
                                            }}>System ({filteredSystemFonts.length})</div>
                                            {filteredSystemFonts.map(f => (
                                                <div key={'es-' + f.path}
                                                    onClick={() => setSelectedFont(f.path)}
                                                    style={{
                                                        padding: '6px 12px', cursor: 'pointer', fontSize: '0.82rem',
                                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                        background: selectedFont === f.path ? 'var(--accent-ember-soft)' : 'transparent',
                                                        borderLeft: selectedFont === f.path ? '3px solid var(--accent-ember)' : '3px solid transparent',
                                                        transition: 'background 0.12s',
                                                    }}
                                                    onMouseEnter={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                                                    onMouseLeave={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'transparent'; }}
                                                >
                                                    <span style={{ flex: 1 }}>{f.name}</span>
                                                    <span
                                                        onClick={e => { e.stopPropagation(); toggleFontFavorite(f.path); }}
                                                        style={{ cursor: 'pointer', fontSize: '0.9rem', color: favoriteFonts.includes(f.path) ? '#FFD700' : 'var(--text-muted)' }}
                                                    >{favoriteFonts.includes(f.path) ? '★' : '☆'}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </>
                                )}

                                <div className="section-divider" />

                                {/* ── Layout ────────────────────────────────── */}
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div className="section-title" style={{ marginBottom: 0 }}>Layout</div>
                                    <button className="btn btn-sm" style={{ fontSize: '0.65rem', padding: '3px 8px', color: 'var(--text-muted)' }}
                                        onClick={() => {
                                            setSettings(prev => ({
                                                ...prev,
                                                size_rel_width: 0.22,
                                                rotation_deg: 0,
                                                tracking: 0.02,
                                                feather_px: 2.0,
                                                base_color_rgb: [255, 255, 255],
                                            }));
                                            setPreviewSrc(null);
                                        }}>
                                        ↺ Reset
                                    </button>
                                </div>
                                <p style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: 8, lineHeight: 1.4 }}>
                                    💡 Drag the text on the canvas to position. Use corner handles to resize, top handle to rotate.
                                </p>

                                <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
                                    <button className={`btn btn-sm ${settings.vertical ? 'btn-primary' : ''}`} style={{ flex: 1, padding: '4px', fontSize: '0.7rem' }}
                                        onClick={() => updateSetting('vertical', !settings.vertical)}>
                                        {settings.vertical ? '⇡ Vertical' : '⇢ Horizontal'}
                                    </button>
                                    <button className={`btn btn-sm ${settings.mirror_x ? 'btn-primary' : ''}`} style={{ flex: 1, padding: '4px', fontSize: '0.7rem' }}
                                        onClick={() => updateSetting('mirror_x', !settings.mirror_x)}>
                                        ◐ Flip X
                                    </button>
                                    <button className={`btn btn-sm ${settings.mirror_y ? 'btn-primary' : ''}`} style={{ flex: 1, padding: '4px', fontSize: '0.7rem' }}
                                        onClick={() => updateSetting('mirror_y', !settings.mirror_y)}>
                                        ◓ Flip Y
                                    </button>
                                </div>

                                {/* ── Quick Place ────────────────────────────── */}
                                <div style={{
                                    background: 'linear-gradient(135deg, rgba(255,69,0,0.08), rgba(255,140,0,0.06))',
                                    border: '1px solid rgba(255,69,0,0.2)',
                                    borderRadius: 'var(--radius-sm)',
                                    padding: '10px 12px',
                                    marginBottom: 10,
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                                        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent-ember)', letterSpacing: '0.03em' }}>
                                            📐 Quick Place
                                        </span>
                                        <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                            one-click logo positioning
                                        </span>
                                    </div>
                                    <button
                                        className="btn btn-sm"
                                        style={{
                                            width: '100%', padding: '8px 12px', fontSize: '0.78rem',
                                            background: 'linear-gradient(135deg, rgba(255,69,0,0.15), rgba(255,140,0,0.1))',
                                            borderColor: 'var(--accent-ember)',
                                            color: 'var(--accent-ember)',
                                            fontWeight: 600,
                                            transition: 'all 0.2s',
                                        }}
                                        onMouseEnter={e => {
                                            e.currentTarget.style.background = 'linear-gradient(135deg, rgba(255,69,0,0.3), rgba(255,140,0,0.2))';
                                            e.currentTarget.style.color = '#fff';
                                        }}
                                        onMouseLeave={e => {
                                            e.currentTarget.style.background = 'linear-gradient(135deg, rgba(255,69,0,0.15), rgba(255,140,0,0.1))';
                                            e.currentTarget.style.color = 'var(--accent-ember)';
                                        }}
                                        onClick={() => {
                                            const margin = settings.quick_place_margin ?? 0.05;
                                            setSettings(prev => ({
                                                ...prev,
                                                x_pct: 1.0 - margin - (0.15 / 2),
                                                y_pct: 1.0 - margin - 0.04,
                                                size_rel_width: 0.15,
                                                rotation_deg: -12,
                                            }));
                                            addToast('Logo placed — bottom-right corner', 'success');
                                        }}
                                    >
                                        ⬇ Place at Bottom-Right Corner
                                    </button>
                                    <div className="slider-group" style={{ marginTop: 8, marginBottom: 0 }}>
                                        <div className="slider-label">
                                            <span style={{ fontSize: '0.72rem' }}>Edge Margin</span>
                                            <span className="slider-value">{Math.round((settings.quick_place_margin ?? 0.05) * 100)}%</span>
                                        </div>
                                        <input type="range" min="0.02" max="0.20" step="0.01"
                                            value={settings.quick_place_margin ?? 0.05}
                                            onChange={e => updateSetting('quick_place_margin', parseFloat(e.target.value))} />
                                    </div>
                                </div>

                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Size</span>
                                        <span className="slider-value">{Math.round(settings.size_rel_width * 100)}%</span>
                                    </div>
                                    <input type="range" min="0.02" max="0.80" step="0.01"
                                        value={settings.size_rel_width}
                                        onChange={e => updateSetting('size_rel_width', parseFloat(e.target.value))} />
                                </div>


                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Rotation</span>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <button className="btn btn-sm"
                                                style={{ padding: '2px 6px', fontSize: '0.65rem', background: 'var(--bg-elevated)', border: '1px solid var(--border-color)', color: 'var(--text-muted)' }}
                                                title="Reset Rotation to 0"
                                                onClick={() => updateSetting('rotation_deg', 0)}>
                                                0°
                                            </button>
                                            <span className="slider-value">{settings.rotation_deg}°</span>
                                        </div>
                                    </div>
                                    <input type="range" min="-180" max="180" step="1"
                                        value={settings.rotation_deg}
                                        onChange={e => updateSetting('rotation_deg', parseFloat(e.target.value))} />
                                </div>

                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Tracking</span>
                                        <span className="slider-value">{settings.tracking.toFixed(2)}</span>
                                    </div>
                                    <input type="range" min="-0.1" max="0.5" step="0.01"
                                        value={settings.tracking}
                                        onChange={e => updateSetting('tracking', parseFloat(e.target.value))} />
                                </div>

                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Feather</span>
                                        <span className="slider-value">{settings.feather_px}px</span>
                                    </div>
                                    <input type="range" min="0" max="20" step="0.5"
                                        value={settings.feather_px}
                                        onChange={e => updateSetting('feather_px', parseFloat(e.target.value))} />
                                </div>

                                <div className="section-divider" />

                                {/* ── Transform Modes ────────────────────────── */}
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div className="section-title" style={{ marginBottom: 0 }}>Transform</div>
                                    <button className="btn btn-sm" style={{ fontSize: '0.65rem', padding: '3px 8px', color: 'var(--text-muted)' }}
                                        onClick={() => {
                                            setSettings(prev => ({
                                                ...prev,
                                                skew_x: 0, skew_y: 0,
                                                perspective_x: 0, perspective_y: 0,
                                            }));
                                            setTransformMode('normal');
                                            setPreviewSrc(null);
                                        }}>
                                        ↺ Reset
                                    </button>
                                </div>
                                <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
                                    <button
                                        className="btn btn-sm"
                                        onClick={() => setTransformMode(transformMode === 'skew' ? 'normal' : 'skew')}
                                        style={{
                                            flex: 1, fontSize: '0.75rem', padding: '6px 8px',
                                            borderColor: transformMode === 'skew' ? 'var(--accent-cyan)' : 'var(--border-medium)',
                                            background: transformMode === 'skew' ? 'rgba(0,229,255,0.12)' : 'transparent',
                                            color: transformMode === 'skew' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                                        }}
                                    >
                                        ⬠ Skew {transformMode === 'skew' ? '(active)' : ''}
                                    </button>
                                    <button
                                        className="btn btn-sm"
                                        onClick={() => setTransformMode(transformMode === 'perspective' ? 'normal' : 'perspective')}
                                        style={{
                                            flex: 1, fontSize: '0.75rem', padding: '6px 8px',
                                            borderColor: transformMode === 'perspective' ? 'var(--accent-cyan)' : 'var(--border-medium)',
                                            background: transformMode === 'perspective' ? 'rgba(0,229,255,0.12)' : 'transparent',
                                            color: transformMode === 'perspective' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                                        }}
                                    >
                                        ◇ Perspective {transformMode === 'perspective' ? '(active)' : ''}
                                    </button>
                                </div>
                                {transformMode !== 'normal' && (
                                    <p style={{ fontSize: '0.66rem', color: 'var(--accent-cyan)', marginBottom: 8, lineHeight: 1.4, fontStyle: 'italic' }}>
                                        🎯 Drag the text box on the canvas to apply {transformMode}
                                    </p>
                                )}

                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Skew X</span>
                                        <span className="slider-value">{settings.skew_x}°</span>
                                    </div>
                                    <input type="range" min="-45" max="45" step="0.5"
                                        value={settings.skew_x}
                                        onChange={e => updateSetting('skew_x', parseFloat(e.target.value))} />
                                </div>

                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Skew Y</span>
                                        <span className="slider-value">{settings.skew_y}°</span>
                                    </div>
                                    <input type="range" min="-45" max="45" step="0.5"
                                        value={settings.skew_y}
                                        onChange={e => updateSetting('skew_y', parseFloat(e.target.value))} />
                                </div>

                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Perspective X</span>
                                        <span className="slider-value">{settings.perspective_x}°</span>
                                    </div>
                                    <input type="range" min="-30" max="30" step="0.5"
                                        value={settings.perspective_x}
                                        onChange={e => updateSetting('perspective_x', parseFloat(e.target.value))} />
                                </div>

                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Perspective Y</span>
                                        <span className="slider-value">{settings.perspective_y}°</span>
                                    </div>
                                    <input type="range" min="-30" max="30" step="0.5"
                                        value={settings.perspective_y}
                                        onChange={e => updateSetting('perspective_y', parseFloat(e.target.value))} />
                                </div>

                                <div className="section-divider" />

                                {/* ── Effect ────────────────────────────────── */}
                                <div className="section-title">Effect</div>

                                {/* Uniform / Per-Letter mode toggle */}
                                <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
                                    <button className={`btn btn-sm ${!perLetterMode ? 'btn-primary' : ''}`}
                                        style={{ flex: 1, fontSize: '0.72rem' }}
                                        onClick={() => setPerLetterMode(false)}>
                                        Uniform
                                    </button>
                                    <button className={`btn btn-sm ${perLetterMode ? 'btn-primary' : ''}`}
                                        style={{ flex: 1, fontSize: '0.72rem' }}
                                        onClick={() => setPerLetterMode(true)}>
                                        Per-Letter
                                    </button>
                                </div>

                                {perLetterMode && (
                                    <>
                                        {/* Letter tabs */}
                                        <div style={{
                                            display: 'flex', gap: 4, marginBottom: 10,
                                            background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)', padding: 4,
                                        }}>
                                            {(settings.text || 'LAZART').split('').map((char, idx) => (
                                                <button key={idx}
                                                    style={{
                                                        flex: 1, padding: '8px 2px', border: 'none', borderRadius: 'var(--radius-sm)',
                                                        background: selectedLetterIdx === idx
                                                            ? 'var(--accent-ember)' : 'transparent',
                                                        color: selectedLetterIdx === idx ? '#fff' : 'var(--text-muted)',
                                                        fontWeight: 800, fontSize: '0.9rem', cursor: 'pointer',
                                                        fontFamily: 'var(--font-sans)',
                                                        transition: 'all 0.15s',
                                                    }}
                                                    onClick={() => setSelectedLetterIdx(idx)}>
                                                    {char}
                                                </button>
                                            ))}
                                        </div>

                                        <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 8, lineHeight: 1.3 }}>
                                            🎨 Editing letter <strong style={{ color: 'var(--accent-ember)' }}>'{(settings.text || 'LAZART')[selectedLetterIdx] || '?'}'</strong> — select an effect below
                                        </p>

                                        {/* Effect selector for current letter */}
                                        <div className="select-group">
                                            <label>Effect for '{(settings.text || 'LAZART')[selectedLetterIdx] || '?'}'</label>
                                            <select
                                                value={perLetterEffects[selectedLetterIdx]?.effect_type || 'difference'}
                                                onChange={e => {
                                                    const newType = e.target.value;
                                                    const eff = effects.find(ef => ef.key === newType);
                                                    setPerLetterEffects(prev => {
                                                        const updated = [...prev];
                                                        // Ensure array is long enough
                                                        while (updated.length <= selectedLetterIdx) {
                                                            updated.push({ effect_type: 'difference', effect_params: {}, strength: 0.85, blend_mode: 'normal' });
                                                        }
                                                        updated[selectedLetterIdx] = {
                                                            ...updated[selectedLetterIdx],
                                                            effect_type: newType,
                                                            effect_params: eff ? { ...eff.default_params } : {},
                                                        };
                                                        return updated;
                                                    });
                                                    setPreviewSrc(null);
                                                }}>
                                                {effects.map(e => (
                                                    <option key={e.key} value={e.key}>
                                                        {EFFECT_ICONS[e.key] || '◎'} {e.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    </>
                                )}

                                {!perLetterMode && (
                                    <div className="select-group">
                                        <label>Effect Type</label>
                                        <select value={settings.effect_type} onChange={e => {
                                            const newType = e.target.value;
                                            const eff = effects.find(ef => ef.key === newType);
                                            if (eff) {
                                                setSettings(prev => ({ ...prev, effect_type: newType, effect_params: { ...eff.default_params } }));
                                            } else {
                                                updateSetting('effect_type', newType);
                                            }
                                            setPreviewSrc(null);
                                        }}>
                                            {effects.map(e => (
                                                <option key={e.key} value={e.key}>
                                                    {EFFECT_ICONS[e.key] || '◎'} {e.name}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                )}

                                {/* Helper to get/set params based on mode */}
                                {(() => {
                                    const activeStrength = perLetterMode ? (perLetterEffects[selectedLetterIdx]?.strength ?? settings.strength) : settings.strength;
                                    const activeBlendMode = perLetterMode ? (perLetterEffects[selectedLetterIdx]?.blend_mode ?? settings.blend_mode) : settings.blend_mode;
                                    const activeEffectType = perLetterMode ? (perLetterEffects[selectedLetterIdx]?.effect_type ?? settings.effect_type) : settings.effect_type;
                                    const activeEffectParams = perLetterMode ? (perLetterEffects[selectedLetterIdx]?.effect_params ?? settings.effect_params) : settings.effect_params;

                                    const handleStrengthChange = (val) => {
                                        if (perLetterMode) {
                                            setPerLetterEffects(prev => {
                                                const updated = [...prev];
                                                if (updated[selectedLetterIdx]) updated[selectedLetterIdx].strength = val;
                                                return updated;
                                            });
                                        } else {
                                            updateSetting('strength', val);
                                        }
                                    };

                                    const handleBlendModeChange = (val) => {
                                        if (perLetterMode) {
                                            setPerLetterEffects(prev => {
                                                const updated = [...prev];
                                                if (updated[selectedLetterIdx]) updated[selectedLetterIdx].blend_mode = val;
                                                return updated;
                                            });
                                        } else {
                                            updateSetting('blend_mode', val);
                                        }
                                    };

                                    const handleParamChange = (key, val) => {
                                        if (perLetterMode) {
                                            setPerLetterEffects(prev => {
                                                const updated = [...prev];
                                                if (updated[selectedLetterIdx]) {
                                                    updated[selectedLetterIdx].effect_params = { ...updated[selectedLetterIdx].effect_params, [key]: val };
                                                }
                                                return updated;
                                            });
                                            setPreviewSrc(null);
                                        } else {
                                            updateEffectParam(key, val);
                                        }
                                    };

                                    return (
                                        <>
                                            {currentEffect && (
                                                <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 10, lineHeight: 1.4 }}>
                                                    {currentEffect.description}
                                                </p>
                                            )}

                                            <div className="slider-group">
                                                <div className="slider-label">
                                                    <span>Strength</span>
                                                    <span className="slider-value">{Math.round(activeStrength * 100)}%</span>
                                                </div>
                                                <input type="range" min="0" max="1" step="0.01"
                                                    value={activeStrength}
                                                    onChange={e => handleStrengthChange(parseFloat(e.target.value))} />
                                            </div>

                                            <div className="select-group">
                                                <label>Blend Mode</label>
                                                <select value={activeBlendMode} onChange={e => handleBlendModeChange(e.target.value)}>
                                                    {BLEND_MODES.map(b => <option key={b.value} value={b.value}>{b.label}</option>)}
                                                </select>
                                            </div>

                                            {/* ── Effect-specific params ─────────────────── */}
                                            {activeEffectType === 'difference' && (
                                                <div className="color-input-group">
                                                    <label>Tint Color</label>
                                                    <div className="color-swatch-row">
                                                        <input type="color"
                                                            value={`#${(activeEffectParams.color_rgb || [255, 255, 255]).map(c => c.toString(16).padStart(2, '0')).join('')}`}
                                                            onChange={e => {
                                                                const hex = e.target.value;
                                                                const r = parseInt(hex.slice(1, 3), 16);
                                                                const g = parseInt(hex.slice(3, 5), 16);
                                                                const b = parseInt(hex.slice(5, 7), 16);
                                                                handleParamChange('color_rgb', [r, g, b]);
                                                            }} />
                                                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                                                            {(activeEffectParams.color_rgb || [255, 255, 255]).join(', ')}
                                                        </span>
                                                    </div>
                                                </div>
                                            )}

                                            {activeEffectType === 'channel_invert' && (
                                                <div className="select-group">
                                                    <label>Channel</label>
                                                    <select value={activeEffectParams.channel || 'r'} onChange={e => handleParamChange('channel', e.target.value)}>
                                                        <option value="r">Red</option>
                                                        <option value="g">Green</option>
                                                        <option value="b">Blue</option>
                                                    </select>
                                                </div>
                                            )}

                                            {activeEffectType === 'solarize' && (
                                                <div className="slider-group">
                                                    <div className="slider-label">
                                                        <span>Threshold</span>
                                                        <span className="slider-value">{((activeEffectParams.threshold || 0.5) * 100).toFixed(0)}%</span>
                                                    </div>
                                                    <input type="range" min="0" max="1" step="0.01"
                                                        value={activeEffectParams.threshold || 0.5}
                                                        onChange={e => handleParamChange('threshold', parseFloat(e.target.value))} />
                                                </div>
                                            )}

                                            {activeEffectType === 'frosted_glass' && (
                                                <>
                                                    <div className="slider-group">
                                                        <div className="slider-label">
                                                            <span>Blur Radius</span>
                                                            <span className="slider-value">{activeEffectParams.blur_radius || 15}px</span>
                                                        </div>
                                                        <input type="range" min="1" max="50" step="1"
                                                            value={activeEffectParams.blur_radius || 15}
                                                            onChange={e => handleParamChange('blur_radius', parseInt(e.target.value))} />
                                                    </div>
                                                    <div className="slider-group">
                                                        <div className="slider-label">
                                                            <span>Brightness</span>
                                                            <span className="slider-value">{(activeEffectParams.brightness_boost || 1.15).toFixed(2)}</span>
                                                        </div>
                                                        <input type="range" min="0.8" max="1.5" step="0.01"
                                                            value={activeEffectParams.brightness_boost || 1.15}
                                                            onChange={e => handleParamChange('brightness_boost', parseFloat(e.target.value))} />
                                                    </div>
                                                </>
                                            )}
                                        </>
                                    );
                                })()}



                                {settings.effect_type === 'duotone' && (
                                    <>
                                        <div className="color-input-group">
                                            <label>Shadow Color</label>
                                            <input type="color"
                                                value={`#${(settings.effect_params.color_a || [20, 20, 80]).map(c => c.toString(16).padStart(2, '0')).join('')}`}
                                                onChange={e => {
                                                    const hex = e.target.value;
                                                    updateEffectParam('color_a', [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)]);
                                                }} />
                                        </div>
                                        <div className="color-input-group">
                                            <label>Highlight Color</label>
                                            <input type="color"
                                                value={`#${(settings.effect_params.color_b || [255, 200, 100]).map(c => c.toString(16).padStart(2, '0')).join('')}`}
                                                onChange={e => {
                                                    const hex = e.target.value;
                                                    updateEffectParam('color_b', [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)]);
                                                }} />
                                        </div>
                                    </>
                                )}

                                {settings.effect_type === 'high_contrast_burn' && (
                                    <>
                                        <div className="slider-group">
                                            <div className="slider-label">
                                                <span>Shadow Gamma</span>
                                                <span className="slider-value">{(settings.effect_params.shadow_gamma || 0.4).toFixed(1)}</span>
                                            </div>
                                            <input type="range" min="0.1" max="1" step="0.05"
                                                value={settings.effect_params.shadow_gamma || 0.4}
                                                onChange={e => updateEffectParam('shadow_gamma', parseFloat(e.target.value))} />
                                        </div>
                                        <div className="slider-group">
                                            <div className="slider-label">
                                                <span>Highlight Gamma</span>
                                                <span className="slider-value">{(settings.effect_params.highlight_gamma || 1.8).toFixed(1)}</span>
                                            </div>
                                            <input type="range" min="1" max="3" step="0.1"
                                                value={settings.effect_params.highlight_gamma || 1.8}
                                                onChange={e => updateEffectParam('highlight_gamma', parseFloat(e.target.value))} />
                                        </div>
                                    </>
                                )}







                                {settings.effect_type === 'luma_invert' && (
                                    <div className="slider-group">
                                        <div className="slider-label">
                                            <span>Gray Shift</span>
                                            <span className="slider-value">{settings.effect_params.mid_gray_shift || 25}%</span>
                                        </div>
                                        <input type="range" min="0" max="50" step="1"
                                            value={settings.effect_params.mid_gray_shift || 25}
                                            onChange={e => updateEffectParam('mid_gray_shift', parseInt(e.target.value))} />
                                    </div>
                                )}
                            </div>
                        </aside>
                    </div>

                    {/* ── BOTTOM STRIP ────────────────────────────────── */}
                    <div className={`bottom-strip ${zenMode ? 'hidden' : ''}`}>
                        {/* Image thumbnails */}
                        <div style={{ display: 'flex', gap: 8, flex: 1, overflow: 'auto', alignItems: 'center' }}>
                            {images.map(img => (
                                <div key={img.id} style={{ position: 'relative', flexShrink: 0 }}>
                                    <div className={`batch-thumb ${activeImageId === img.id ? 'active' : ''}`}
                                        onClick={() => selectImage(img)}>
                                        <img src={img.proxy} alt={img.filename} draggable={false} />
                                    </div>
                                    <div style={{ display: 'flex', gap: 2, marginTop: 4, justifyContent: 'center' }}>
                                        <button className="btn btn-sm" style={{ padding: '1px 5px', fontSize: '0.6rem' }}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                replaceInputRef.current?.setAttribute('data-replace-id', img.id);
                                                replaceInputRef.current?.click();
                                            }} title="Re-import this image">↻</button>
                                        <button className="btn btn-sm btn-danger" style={{ padding: '1px 5px', fontSize: '0.6rem' }}
                                            onClick={(e) => handleDeleteImage(img.id, e)} title="Remove from workflow">✕</button>
                                    </div>
                                </div>
                            ))}
                            <input ref={replaceInputRef} type="file" accept="image/*" style={{ display: 'none' }}
                                onChange={e => {
                                    const id = e.target.getAttribute('data-replace-id');
                                    if (id && e.target.files[0]) handleReplaceImage(id, e.target.files[0]);
                                }} />
                            {images.length === 0 && (
                                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                                    No images loaded — drop files on the canvas
                                </span>
                            )}
                        </div>

                        {/* Export controls */}
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
                            {isExporting && (
                                <div style={{ width: 120 }}>
                                    <div className="progress-bar">
                                        <div className="progress-fill" style={{ width: `${exportProgress}%` }} />
                                    </div>
                                </div>
                            )}

                            {images.length > 1 && (
                                <button className="btn btn-sm" onClick={handleBatchExport} disabled={isExporting}>
                                    Batch ({images.length})
                                </button>
                            )}

                            <button
                                className={`btn-ignite ${isExporting ? 'igniting' : ''}`}
                                onClick={handleExport}
                                disabled={!activeImageId || isExporting}>
                                {isExporting ? '⚡ PROCESSING...' : '🔥 IGNITE'}
                            </button>
                        </div>
                    </div>

                    {/* ── Font Browser Modal ───────────────────────── */}
                    {showFontModal && (
                        <div style={{
                            position: 'fixed', inset: 0, zIndex: 10000,
                            background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}
                            onClick={() => setShowFontModal(false)}
                        >
                            <div style={{
                                background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)',
                                borderRadius: 'var(--radius-lg)', width: '480px', maxHeight: '80vh',
                                display: 'flex', flexDirection: 'column', overflow: 'hidden',
                                boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
                            }}
                                onClick={e => e.stopPropagation()}
                            >
                                {/* Modal header */}
                                <div style={{
                                    padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                }}>
                                    <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>🔤 Font Browser</h3>
                                    <button onClick={() => setShowFontModal(false)} style={{
                                        background: 'transparent', border: 'none', color: 'var(--text-muted)',
                                        fontSize: '1.2rem', cursor: 'pointer', padding: '4px 8px',
                                    }}>✕</button>
                                </div>

                                {/* Search */}
                                <div style={{ padding: '12px 20px 8px' }}>
                                    <input
                                        type="text"
                                        placeholder="Search fonts..."
                                        value={fontSearch}
                                        onChange={e => setFontSearch(e.target.value)}
                                        autoFocus
                                        style={{
                                            width: '100%', padding: '10px 14px', fontSize: '0.92rem',
                                            background: 'var(--bg-base)', border: '1px solid var(--border-medium)',
                                            borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
                                            fontFamily: 'var(--font-sans)', outline: 'none',
                                        }}
                                    />
                                </div>

                                {/* Font list */}
                                <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px 12px' }}>
                                    {/* System Default */}
                                    <div
                                        onClick={() => { setSelectedFont(null); setShowFontModal(false); }}
                                        style={{
                                            padding: '10px 14px', cursor: 'pointer', fontSize: '0.88rem', margin: '4px 0',
                                            borderRadius: 'var(--radius-sm)',
                                            background: selectedFont === null ? 'var(--accent-ember-soft)' : 'transparent',
                                            borderLeft: selectedFont === null ? '3px solid var(--accent-ember)' : '3px solid transparent',
                                            color: 'var(--text-secondary)', fontStyle: 'italic',
                                            transition: 'background 0.15s',
                                        }}
                                        onMouseEnter={e => { if (selectedFont !== null) e.target.style.background = 'rgba(255,255,255,0.04)'; }}
                                        onMouseLeave={e => { if (selectedFont !== null) e.target.style.background = 'transparent'; }}
                                    >
                                        System Default
                                    </div>

                                    {/* Favorites section */}
                                    {favoriteFonts.length > 0 && (() => {
                                        const favFonts = [...fonts, ...systemFonts].filter(f => favoriteFonts.includes(f.path));
                                        const filtered = fontSearch
                                            ? favFonts.filter(f => f.name.toLowerCase().includes(fontSearch.toLowerCase()))
                                            : favFonts;
                                        if (filtered.length === 0) return null;
                                        return (
                                            <>
                                                <div style={{
                                                    padding: '8px 14px 4px', fontSize: '0.7rem', fontWeight: 700,
                                                    color: '#FFD700', textTransform: 'uppercase', letterSpacing: '0.1em',
                                                }}>★ Favorites ({filtered.length})</div>
                                                {filtered.map(f => (
                                                    <div key={'mfav-' + f.path} style={{
                                                        padding: '8px 14px', cursor: 'pointer', fontSize: '0.88rem',
                                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                        borderRadius: 'var(--radius-sm)', margin: '1px 0',
                                                        background: selectedFont === f.path ? 'var(--accent-ember-soft)' : 'transparent',
                                                        borderLeft: selectedFont === f.path ? '3px solid var(--accent-ember)' : '3px solid transparent',
                                                        transition: 'background 0.15s',
                                                    }}
                                                        onMouseEnter={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                                                        onMouseLeave={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'transparent'; }}
                                                    >
                                                        <span onClick={() => { setSelectedFont(f.path); setShowFontModal(false); }} style={{ flex: 1 }}>{f.name}</span>
                                                        <span
                                                            onClick={e => { e.stopPropagation(); toggleFontFavorite(f.path); }}
                                                            style={{ cursor: 'pointer', fontSize: '1rem', color: '#FFD700' }}
                                                        >★</span>
                                                    </div>
                                                ))}
                                            </>
                                        );
                                    })()}

                                    {/* Custom fonts */}
                                    {fonts.length > 0 && (() => {
                                        const filtered = fontSearch
                                            ? fonts.filter(f => f.name.toLowerCase().includes(fontSearch.toLowerCase()))
                                            : fonts;
                                        if (filtered.length === 0) return null;
                                        return (
                                            <>
                                                <div style={{
                                                    padding: '8px 14px 4px', fontSize: '0.7rem', fontWeight: 700,
                                                    color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.1em',
                                                }}>Custom Fonts ({filtered.length})</div>
                                                {filtered.map(f => (
                                                    <div key={'mcust-' + f.path} style={{
                                                        padding: '8px 14px', cursor: 'pointer', fontSize: '0.88rem',
                                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                                        borderRadius: 'var(--radius-sm)', margin: '1px 0',
                                                        background: selectedFont === f.path ? 'var(--accent-ember-soft)' : 'transparent',
                                                        borderLeft: selectedFont === f.path ? '3px solid var(--accent-ember)' : '3px solid transparent',
                                                        transition: 'background 0.15s',
                                                    }}
                                                        onMouseEnter={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                                                        onMouseLeave={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'transparent'; }}
                                                    >
                                                        <span onClick={() => { setSelectedFont(f.path); setShowFontModal(false); }} style={{ flex: 1 }}>{f.name}</span>
                                                        <span
                                                            onClick={e => { e.stopPropagation(); toggleFontFavorite(f.path); }}
                                                            style={{ cursor: 'pointer', fontSize: '1rem', color: favoriteFonts.includes(f.path) ? '#FFD700' : 'var(--text-muted)' }}
                                                        >{favoriteFonts.includes(f.path) ? '★' : '☆'}</span>
                                                    </div>
                                                ))}
                                            </>
                                        );
                                    })()}

                                    {/* System fonts */}
                                    <div style={{
                                        padding: '8px 14px 4px', fontSize: '0.7rem', fontWeight: 700,
                                        color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em',
                                    }}>System Fonts ({filteredSystemFonts.length})</div>
                                    {filteredSystemFonts.map(f => (
                                        <div key={'msys-' + f.path} style={{
                                            padding: '8px 14px', cursor: 'pointer', fontSize: '0.88rem',
                                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                            borderRadius: 'var(--radius-sm)', margin: '1px 0',
                                            background: selectedFont === f.path ? 'var(--accent-ember-soft)' : 'transparent',
                                            borderLeft: selectedFont === f.path ? '3px solid var(--accent-ember)' : '3px solid transparent',
                                            transition: 'background 0.15s',
                                        }}
                                            onMouseEnter={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                                            onMouseLeave={e => { if (selectedFont !== f.path) e.currentTarget.style.background = 'transparent'; }}
                                        >
                                            <span onClick={() => { setSelectedFont(f.path); setShowFontModal(false); }} style={{ flex: 1 }}>{f.name}</span>
                                            <span
                                                onClick={e => { e.stopPropagation(); toggleFontFavorite(f.path); }}
                                                style={{ cursor: 'pointer', fontSize: '1rem', color: favoriteFonts.includes(f.path) ? '#FFD700' : 'var(--text-muted)' }}
                                            >{favoriteFonts.includes(f.path) ? '★' : '☆'}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                </>
            )}

            {/* ── Toasts ──────────────────────────────────────── */}
            <div className="toast-container">
                {toasts.map(t => (
                    <div key={t.id} className={`toast ${t.type}`}>
                        <span className="toast-icon">{t.type === 'success' ? '✓' : '✗'}</span>
                        <span className="toast-text">{t.text}</span>
                    </div>
                ))}
            </div>
        </div >
    );
}

export default App;
