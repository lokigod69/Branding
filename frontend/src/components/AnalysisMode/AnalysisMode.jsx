import React, { useState, useRef, useCallback, useEffect } from 'react';
import './AnalysisMode.css';

// ── Constants ──────────────────────────────────────────────
const A4_MM = { w: 210, h: 297 };
const MM_PER_INCH = 25.4;
const TARGET_DPI = 300;

function getA4Px(orientation) {
    const wMM = orientation === 'portrait' ? A4_MM.w : A4_MM.h;
    const hMM = orientation === 'portrait' ? A4_MM.h : A4_MM.w;
    return {
        w: Math.round((wMM / MM_PER_INCH) * TARGET_DPI),
        h: Math.round((hMM / MM_PER_INCH) * TARGET_DPI),
        wInch: wMM / MM_PER_INCH,
        hInch: hMM / MM_PER_INCH,
    };
}

function gcd(a, b) {
    a = Math.abs(Math.round(a));
    b = Math.abs(Math.round(b));
    while (b) { [a, b] = [b, a % b]; }
    return a;
}

function aspectLabel(w, h) {
    const g = gcd(w, h);
    const rw = w / g;
    const rh = h / g;
    // Simplify large ratios to decimal
    if (rw > 50 || rh > 50) return `${(w / h).toFixed(2)}:1`;
    return `${rw}:${rh}`;
}

// ── Main Component ─────────────────────────────────────────
export default function AnalysisMode() {
    // Image state
    const [imageSrc, setImageSrc] = useState(null);
    const [imageDims, setImageDims] = useState(null); // { w, h }
    const [fileName, setFileName] = useState('');
    const [fileSize, setFileSize] = useState(0);

    // A4 orientation
    const [orientation, setOrientation] = useState('portrait');

    // Drag the image inside A4 frame
    const [imgOffset, setImgOffset] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

    // Copy toast
    const [showCopyToast, setShowCopyToast] = useState(false);

    // Drag-over for drop zone
    const [dragOver, setDragOver] = useState(false);

    // Show overflow edges toggle
    const [showOverflow, setShowOverflow] = useState(true);

    // Margins toggle
    const [includeMargins, setIncludeMargins] = useState(false);
    const [marginMM, setMarginMM] = useState(3);

    const fileInputRef = useRef(null);
    const canvasRef = useRef(null); // for crop export
    const originalImgRef = useRef(null); // hidden full-res image for cropping

    // ── Handle file drop / select ──────────────────────────
    const loadImage = useCallback((file) => {
        if (!file || !file.type.startsWith('image/')) return;
        setFileName(file.name);
        setFileSize(file.size);

        const url = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => {
            setImageDims({ w: img.naturalWidth, h: img.naturalHeight });
            setImageSrc(url);
            setImgOffset({ x: 0, y: 0 });
            // Store for cropping
            if (originalImgRef.current) {
                originalImgRef.current.src = url;
            }
        };
        img.src = url;
    }, []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer?.files?.[0];
        if (file) loadImage(file);
    }, [loadImage]);

    const handleFileSelect = useCallback((e) => {
        const file = e.target.files?.[0];
        if (file) loadImage(file);
    }, [loadImage]);

    // ── Calculations ───────────────────────────────────────
    const a4 = getA4Px(orientation);

    // Calculate inner printable area
    const marginPx = includeMargins ? Math.round((marginMM / MM_PER_INCH) * TARGET_DPI) : 0;
    const innerA4 = {
        w: Math.max(1, a4.w - (marginPx * 2)),
        h: Math.max(1, a4.h - (marginPx * 2)),
        wInch: Math.max(0.1, a4.wInch - ((marginMM * 2) / MM_PER_INCH)),
        hInch: Math.max(0.1, a4.hInch - ((marginMM * 2) / MM_PER_INCH))
    };

    let analysis = null;
    if (imageDims) {
        const imgW = imageDims.w;
        const imgH = imageDims.h;
        const imgAspect = imgW / imgH;
        const a4Aspect = innerA4.w / innerA4.h; // Fit to PRINTABLE area

        // How does the image fit to cover A4?
        let fitW, fitH, cropW, cropH;

        if (imgAspect > a4Aspect) {
            // Image is wider than A4 → height-limited, crop sides
            fitH = imgH;
            fitW = Math.round(imgH * a4Aspect);
            cropW = imgW - fitW;
            cropH = 0;
        } else {
            // Image is taller than A4 → width-limited, crop top/bottom
            fitW = imgW;
            fitH = Math.round(imgW / a4Aspect);
            cropW = 0;
            cropH = imgH - fitH;
        }

        // Effective DPI of the fitted region at inner A4 physical size
        const effectiveDPI = Math.round(fitW / innerA4.wInch);

        // Upscale factor to reach 300 DPI
        const upscaleFactor = effectiveDPI >= TARGET_DPI
            ? 1
            : TARGET_DPI / effectiveDPI;

        // Target dimensions (upscale the FULL original, then crop)
        const targetW = Math.ceil(imgW * upscaleFactor);
        const targetH = Math.ceil(imgH * upscaleFactor);

        // After upscaling, the fitted region at Inner A4:
        const finalFitW = Math.round(fitW * upscaleFactor);
        const finalFitH = Math.round(fitH * upscaleFactor);

        const needsCrop = cropW > 0 || cropH > 0;
        const cropPercent = needsCrop
            ? (((cropW * imgH) + (cropH * imgW)) / (imgW * imgH) * 100).toFixed(1)
            : 0;

        const dpiStatus = effectiveDPI >= 300 ? 'good' : effectiveDPI >= 150 ? 'warn' : 'bad';

        analysis = {
            imgW, imgH, imgAspect,
            a4Aspect,
            fitW, fitH,
            cropW, cropH, needsCrop, cropPercent,
            effectiveDPI, dpiStatus,
            upscaleFactor,
            targetW, targetH,
            finalFitW, finalFitH,
            alreadySufficient: effectiveDPI >= TARGET_DPI,
        };
    }

    // ── A4 frame display sizing ────────────────────────────
    // Scale A4 frame to fit within the canvas area
    const FRAME_MAX_H = typeof window !== 'undefined' ? window.innerHeight - 200 : 600;
    const FRAME_MAX_W = typeof window !== 'undefined' ? window.innerWidth - 450 : 600;
    let frameScale = 1;
    if (a4.h > 0) {
        frameScale = Math.min(FRAME_MAX_H / a4.h, FRAME_MAX_W / a4.w, 1);
    }
    // Ensure frame is at least 200px tall
    if (a4.h * frameScale < 200) frameScale = 200 / a4.h;

    const frameW = Math.round(a4.w * frameScale);
    const frameH = Math.round(a4.h * frameScale);

    // The inner printable area on the screen
    const innerFrameW = Math.round(innerA4.w * frameScale);
    const innerFrameH = Math.round(innerA4.h * frameScale);

    // Image display size within frame (cover the inner frame layout)
    let imgDisplayW = 0, imgDisplayH = 0;
    if (imageDims) {
        const imgAspect = imageDims.w / imageDims.h;
        const frameAspect = innerFrameW / innerFrameH;
        if (imgAspect > frameAspect) {
            // Image wider → fit height, overflow width
            imgDisplayH = innerFrameH;
            imgDisplayW = Math.round(innerFrameH * imgAspect);
        } else {
            // Image taller → fit width, overflow height
            imgDisplayW = innerFrameW;
            imgDisplayH = Math.round(innerFrameW / imgAspect);
        }
    }

    // ── Drag handling ──────────────────────────────────────
    const handleMouseDown = (e) => {
        if (!imageSrc) return;
        e.preventDefault();
        setIsDragging(true);
        setDragStart({ x: e.clientX - imgOffset.x, y: e.clientY - imgOffset.y });
    };

    useEffect(() => {
        if (!isDragging) return;

        const handleMove = (e) => {
            const newX = e.clientX - dragStart.x;
            const newY = e.clientY - dragStart.y;

            // Clamp so image doesn't leave the inner frame
            const maxX = Math.max(0, (imgDisplayW - innerFrameW) / 2);
            const maxY = Math.max(0, (imgDisplayH - innerFrameH) / 2);
            setImgOffset({
                x: Math.max(-maxX, Math.min(maxX, newX)),
                y: Math.max(-maxY, Math.min(maxY, newY)),
            });
        };

        const handleUp = () => setIsDragging(false);

        window.addEventListener('mousemove', handleMove);
        window.addEventListener('mouseup', handleUp);
        return () => {
            window.removeEventListener('mousemove', handleMove);
            window.removeEventListener('mouseup', handleUp);
        };
    }, [isDragging, dragStart, imgDisplayW, imgDisplayH, innerFrameW, innerFrameH]);

    // Reset offset when orientation changes
    useEffect(() => {
        setImgOffset({ x: 0, y: 0 });
    }, [orientation]);

    // ── Crop & Download ────────────────────────────────────
    const handleCrop = useCallback(() => {
        if (!originalImgRef.current || !imageDims || !analysis) return;

        const canvas = canvasRef.current || document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = originalImgRef.current;

        // The crop region in original image pixels
        // Calculate based on image offset (drag position)
        const scaleOrigToDisplay = imageDims.w / imgDisplayW;

        const overflowX = (imgDisplayW - innerFrameW) / 2;
        const overflowY = (imgDisplayH - innerFrameH) / 2;

        // Source region in original pixels
        const sx = (overflowX - imgOffset.x) * scaleOrigToDisplay;
        const sy = (overflowY - imgOffset.y) * scaleOrigToDisplay;
        const sw = innerFrameW * scaleOrigToDisplay;
        const sh = innerFrameH * scaleOrigToDisplay;

        // The canvas should be the FULL A4 size
        canvas.width = Math.round(a4.w);
        canvas.height = Math.round(a4.h);

        // Fill white background for borders
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw the image exclusively in the inner printable region
        ctx.drawImage(img,
            Math.round(sx), Math.round(sy), Math.round(sw), Math.round(sh),
            Math.round(marginPx), Math.round(marginPx), Math.round(innerA4.w), Math.round(innerA4.h)
        );

        canvas.toBlob((blob) => {
            if (!blob) return;
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const baseName = fileName ? fileName.replace(/\.[^.]+$/, '') : 'image';
            a.download = `${baseName}_A4_crop.png`;
            a.click();
            URL.revokeObjectURL(url);
        }, 'image/png');
    }, [imageDims, imgDisplayW, imgDisplayH, innerFrameW, innerFrameH, imgOffset, fileName, analysis, a4, innerA4, marginPx]);

    // ── Copy dimensions ────────────────────────────────────
    const handleCopyDimensions = useCallback(() => {
        if (!analysis) return;
        const text = `${analysis.targetW} × ${analysis.targetH}`;
        navigator.clipboard.writeText(text).then(() => {
            setShowCopyToast(true);
            setTimeout(() => setShowCopyToast(false), 2000);
        });
    }, [analysis]);

    // ── Clear image ────────────────────────────────────────
    const handleClear = () => {
        if (imageSrc) URL.revokeObjectURL(imageSrc);
        setImageSrc(null);
        setImageDims(null);
        setFileName('');
        setFileSize(0);
        setImgOffset({ x: 0, y: 0 });
    };

    // ── Format file size ───────────────────────────────────
    const formatSize = (bytes) => {
        if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
        if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(0)} KB`;
        return `${bytes} B`;
    };

    // ── Render ─────────────────────────────────────────────
    return (
        <div className="analysis-mode">
            {/* Hidden elements for cropping */}
            <img ref={originalImgRef} style={{ display: 'none' }} crossOrigin="anonymous" />
            <canvas ref={canvasRef} style={{ display: 'none' }} />

            {/* ── Canvas Area ─────────────────────────────────── */}
            <div
                className="analysis-canvas-area"
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
            >
                {!imageSrc ? (
                    <div
                        className={`analysis-dropzone ${dragOver ? 'active' : ''}`}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <div className="dropzone-icon">📐</div>
                        <h3>Drop an image to analyze</h3>
                        <p>Calculate upscale dimensions for 300 DPI A4 print</p>
                        <p style={{ color: 'var(--accent-cyan)', fontSize: '0.72rem', marginTop: 4 }}>
                            JPG, PNG, WEBP, TIFF
                        </p>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            style={{ display: 'none' }}
                            onChange={handleFileSelect}
                        />
                    </div>
                ) : (
                    <>
                        <div className="analysis-frame-container">
                            {/* Ghost overflow image — shows cropped edges at low opacity */}
                            {showOverflow && (imgDisplayW > innerFrameW || imgDisplayH > innerFrameH) && (
                                <img
                                    src={imageSrc}
                                    alt=""
                                    className="analysis-overflow-ghost"
                                    style={{
                                        width: imgDisplayW,
                                        height: imgDisplayH,
                                        transform: `translate(${imgOffset.x}px, ${imgOffset.y}px)`,
                                    }}
                                    draggable={false}
                                />
                            )}

                            <div
                                className="analysis-a4-frame"
                                style={{
                                    width: frameW,
                                    height: frameH,
                                    boxShadow: showOverflow
                                        ? '0 0 0 3000px rgba(0, 0, 0, 0.35), 0 0 20px rgba(0, 229, 255, 0.15)'
                                        : undefined,
                                }}
                            >
                                <div className="a4-label">
                                    A4 {orientation} — {a4.w} × {a4.h} px @ 300 DPI
                                </div>

                                {/* Padding Visualizer */}
                                {includeMargins && marginMM > 0 && (
                                    <div style={{
                                        position: 'absolute',
                                        top: 0, left: 0, right: 0, bottom: 0,
                                        border: `${Math.round(marginPx * frameScale)}px solid white`,
                                        zIndex: 5,
                                        pointerEvents: 'none',
                                        opacity: 0.95
                                    }} />
                                )}

                                {/* Image inside A4 frame Printable Area */}
                                <div style={{
                                    position: 'absolute',
                                    top: (frameH - innerFrameH) / 2,
                                    left: (frameW - innerFrameW) / 2,
                                    width: innerFrameW,
                                    height: innerFrameH,
                                    overflow: 'hidden'
                                }}>
                                    <img
                                        src={imageSrc}
                                        alt="Analysis"
                                        className={`analysis-image ${isDragging ? 'dragging' : ''}`}
                                        style={{
                                            position: 'absolute',
                                            width: imgDisplayW,
                                            height: imgDisplayH,
                                            left: (innerFrameW - imgDisplayW) / 2 + imgOffset.x,
                                            top: (innerFrameH - imgDisplayH) / 2 + imgOffset.y,
                                            maxWidth: 'none',
                                            maxHeight: 'none'
                                        }}
                                        onMouseDown={handleMouseDown}
                                        draggable={false}
                                    />
                                </div>

                                {/* Corner markers */}
                                <div className="corner-mark tl" />
                                <div className="corner-mark tr" />
                                <div className="corner-mark bl" />
                                <div className="corner-mark br" />
                            </div>
                        </div>

                        {/* Floating actions */}
                        <div className="analysis-floating-actions">
                            <button
                                onClick={() => setShowOverflow(!showOverflow)}
                                style={showOverflow ? { borderColor: 'var(--accent-cyan)', color: 'var(--accent-cyan)' } : {}}
                            >
                                {showOverflow ? '👁 Edges On' : '👁‍🗨 Show Edges'}
                            </button>
                            <button onClick={() => setImgOffset({ x: 0, y: 0 })}>↺ Reset Position</button>
                            <button onClick={handleClear}>✕ Clear</button>
                            <button onClick={() => fileInputRef.current?.click()}>📁 New Image</button>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                style={{ display: 'none' }}
                                onChange={handleFileSelect}
                            />
                        </div>

                        {/* Image info bar */}
                        <div style={{
                            position: 'absolute', bottom: 8, left: 8,
                            background: 'rgba(0,0,0,0.7)', borderRadius: 'var(--radius-sm)',
                            padding: '4px 10px', fontSize: '0.7rem', color: 'var(--text-muted)',
                            fontFamily: 'var(--font-mono)', zIndex: 20,
                            display: 'flex', gap: 10, alignItems: 'center',
                        }}>
                            <span>{imageDims?.w}×{imageDims?.h}</span>
                            <span style={{ color: 'var(--accent-cyan)' }}>
                                {aspectLabel(imageDims?.w || 1, imageDims?.h || 1)}
                            </span>
                            {analysis && (
                                <span style={{
                                    color: analysis.dpiStatus === 'good' ? '#4caf50'
                                        : analysis.dpiStatus === 'warn' ? '#ff9800' : '#f44336'
                                }}>
                                    {analysis.effectiveDPI} DPI
                                </span>
                            )}
                            <span>💡 Drag image to reposition</span>
                        </div>
                    </>
                )}
            </div>

            {/* ── Info Panel ──────────────────────────────────── */}
            <aside className="analysis-panel">
                <div className="panel-header">
                    <span style={{ fontSize: '1.1rem' }}>📐</span>
                    <h2>Print Analysis</h2>
                </div>

                {!imageDims ? (
                    <div className="analysis-placeholder">
                        <div className="placeholder-icon">🖼</div>
                        <p>Drop an image on the canvas to begin analysis</p>
                    </div>
                ) : (
                    <div className="panel-body">
                        {/* ── Image Info ──────────────────────────── */}
                        <div className="analysis-section">
                            <div className="analysis-section-title">Source Image</div>
                            {fileName && (
                                <div className="analysis-info-row">
                                    <span className="info-label">File</span>
                                    <span className="info-value" style={{ fontSize: '0.72rem', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {fileName}
                                    </span>
                                </div>
                            )}
                            <div className="analysis-info-row">
                                <span className="info-label">Dimensions</span>
                                <span className="info-value">{imageDims.w} × {imageDims.h}</span>
                            </div>
                            <div className="analysis-info-row">
                                <span className="info-label">Aspect Ratio</span>
                                <span className="info-value">{aspectLabel(imageDims.w, imageDims.h)}</span>
                            </div>
                            {fileSize > 0 && (
                                <div className="analysis-info-row">
                                    <span className="info-label">File Size</span>
                                    <span className="info-value">{formatSize(fileSize)}</span>
                                </div>
                            )}
                            <div className="analysis-info-row">
                                <span className="info-label">Megapixels</span>
                                <span className="info-value">{((imageDims.w * imageDims.h) / 1e6).toFixed(1)} MP</span>
                            </div>
                        </div>

                        <div className="analysis-divider" />

                        {/* ── A4 Target ──────────────────────────── */}
                        <div className="analysis-section">
                            <div className="analysis-section-title">A4 Target</div>
                            <div className="orientation-toggle">
                                <button
                                    className={orientation === 'portrait' ? 'active' : ''}
                                    onClick={() => setOrientation('portrait')}
                                >
                                    ▯ Portrait
                                </button>
                                <button
                                    className={orientation === 'landscape' ? 'active' : ''}
                                    onClick={() => setOrientation('landscape')}
                                >
                                    ▭ Landscape
                                </button>
                            </div>
                            <div className="analysis-info-row" style={{ marginTop: 8 }}>
                                <span className="info-label">A4 @ 300 DPI</span>
                                <span className="info-value">{a4.w} × {a4.h}</span>
                            </div>
                            <div className="analysis-info-row">
                                <span className="info-label">A4 Aspect</span>
                                <span className="info-value">{orientation === 'portrait' ? '1:1.414' : '1.414:1'}</span>
                            </div>

                            {/* Printer Margins Toggle & Input */}
                            <div style={{ marginTop: 12, padding: '8px', background: 'rgba(255,255,255,0.03)', borderRadius: 'var(--radius-sm)' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', cursor: 'pointer', marginBottom: includeMargins ? 8 : 0 }}>
                                    <input
                                        type="checkbox"
                                        checked={includeMargins}
                                        onChange={(e) => setIncludeMargins(e.target.checked)}
                                        style={{ accentColor: 'var(--accent-cyan)' }}
                                    />
                                    <span>Account for Printer Margins</span>
                                </label>

                                {includeMargins && (
                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, paddingLeft: 22 }}>
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>White border width:</span>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                            <input
                                                type="number"
                                                value={marginMM}
                                                onChange={(e) => setMarginMM(Math.max(0, parseFloat(e.target.value) || 0))}
                                                step="0.5"
                                                min="0"
                                                style={{
                                                    width: 50,
                                                    background: 'rgba(0,0,0,0.3)',
                                                    border: '1px solid var(--border-color)',
                                                    color: 'white',
                                                    padding: '2px 4px',
                                                    borderRadius: '4px',
                                                    fontSize: '0.75rem',
                                                    textAlign: 'center'
                                                }}
                                            />
                                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>mm</span>
                                        </div>
                                    </div>
                                )}

                                {includeMargins && (
                                    <div className="analysis-info-row" style={{ marginTop: 6, paddingTop: 6, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                                        <span className="info-label">Printable Area</span>
                                        <span className="info-value" style={{ color: 'var(--accent-cyan)' }}>{innerA4.w} × {innerA4.h}</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="analysis-divider" />

                        {/* ── DPI Analysis ───────────────────────── */}
                        {analysis && (
                            <div className="analysis-section">
                                <div className="analysis-section-title">DPI Analysis</div>

                                <div className={`dpi-badge ${analysis.dpiStatus}`}>
                                    {analysis.dpiStatus === 'good' ? '✅' : analysis.dpiStatus === 'warn' ? '⚠️' : '❌'}
                                    {' '}{analysis.effectiveDPI} DPI
                                    <span style={{ fontSize: '0.72rem', fontWeight: 400, opacity: 0.7 }}>
                                        {analysis.dpiStatus === 'good' ? ' (Print ready!)' : analysis.dpiStatus === 'warn' ? ' (Acceptable)' : ' (Needs upscale)'}
                                    </span>
                                </div>

                                <div className="analysis-info-row">
                                    <span className="info-label">Usable Region</span>
                                    <span className="info-value">{analysis.fitW} × {analysis.fitH}</span>
                                </div>

                                {analysis.needsCrop && (
                                    <div className="crop-info-box" style={{ marginTop: 6 }}>
                                        <strong>Crop needed:</strong> ~{analysis.cropPercent}% trimmed
                                        {analysis.cropW > 0 && <span> ({analysis.cropW}px from sides)</span>}
                                        {analysis.cropH > 0 && <span> ({analysis.cropH}px from top/bottom)</span>}
                                    </div>
                                )}
                            </div>
                        )}

                        <div className="analysis-divider" />

                        {/* ── Upscale Target ────────────────────── */}
                        {analysis && (
                            <div className="analysis-section">
                                {analysis.alreadySufficient ? (
                                    <div className="upscale-result-box" style={{ borderColor: 'rgba(76,175,80,0.3)', background: 'rgba(76,175,80,0.06)' }}>
                                        <div className="result-title" style={{ color: '#66bb6a' }}>✅ No Upscaling Needed</div>
                                        <div className="result-value" style={{ fontSize: '1rem' }}>{imageDims.w} × {imageDims.h}</div>
                                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                            This image already meets 300 DPI for A4 print.
                                        </div>
                                    </div>
                                ) : (
                                    <div className="upscale-result-box">
                                        <div className="result-title">🎯 Upscale Target</div>
                                        <div className="result-value">{analysis.targetW} × {analysis.targetH}</div>
                                        <div className="result-factor">↑ {analysis.upscaleFactor.toFixed(2)}× upscale</div>
                                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.4 }}>
                                            Upscale your original to these dimensions, then crop to A4 ({a4.w}×{a4.h}).
                                        </div>
                                    </div>
                                )}

                                <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                                    <button className="analysis-btn secondary" onClick={handleCopyDimensions}>
                                        📋 Copy Dimensions
                                    </button>
                                </div>
                            </div>
                        )}

                        <div className="analysis-divider" />

                        {/* ── Actions ────────────────────────────── */}
                        {analysis && (
                            <div className="analysis-section">
                                <div className="analysis-section-title">Actions</div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                    <button className="analysis-btn primary" onClick={handleCrop}>
                                        ✂ Crop to A4 & Download
                                    </button>
                                    <p style={{ fontSize: '0.68rem', color: 'var(--text-muted)', margin: '2px 0 0', lineHeight: 1.4 }}>
                                        Crops the visible area. Drag the image to adjust position first.
                                    </p>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </aside>

            {/* Copy toast */}
            {showCopyToast && (
                <div className="copy-toast">📋 Dimensions copied to clipboard!</div>
            )}
        </div>
    );
}
