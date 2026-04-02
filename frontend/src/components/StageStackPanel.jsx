/**
 * StageStackPanel.jsx — The unified pipeline stage stack
 *
 * Shows all pipeline stages in processing order:
 *   - Filter stages (pre-signing)
 *   - Signing stage
 *   - Filter stages (post-signing / final finish)
 *
 * Features:
 *   - Global stack intensity slider
 *   - Add filter stage button
 *   - Drag-and-drop reorder
 *   - Stage duplication
 *   - Basic undo/redo
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import StageCard from './StageCard.jsx';
import { DEFAULT_FILTER_STAGE, DEFAULT_SIGNING_STAGE, FILTER_FAMILIES } from '../utils/constants.js';

let _nextStageId = 1;
function genId() { return `stg_${_nextStageId++}_${Date.now().toString(36)}`; }

export default function StageStackPanel({
    stages,
    setStages,
    globalIntensity,
    setGlobalIntensity,
    filterEngineEnabled,
    setFilterEngineEnabled,
    signingEnabled,
    setSigningEnabled,
    availableFilters,
    onPreviewRequested,
}) {
    // ── Undo/Redo ──────────────────────────────────────────
    const [undoStack, setUndoStack] = useState([]);
    const [redoStack, setRedoStack] = useState([]);
    const [showFilterPicker, setShowFilterPicker] = useState(false);

    const pushUndo = useCallback((currentStages) => {
        setUndoStack(prev => [...prev.slice(-20), JSON.parse(JSON.stringify(currentStages))]);
        setRedoStack([]);
    }, []);

    const undo = useCallback(() => {
        if (undoStack.length === 0) return;
        const prev = undoStack[undoStack.length - 1];
        setUndoStack(s => s.slice(0, -1));
        setRedoStack(s => [...s, JSON.parse(JSON.stringify(stages))]);
        setStages(prev);
    }, [undoStack, stages, setStages]);

    const redo = useCallback(() => {
        if (redoStack.length === 0) return;
        const next = redoStack[redoStack.length - 1];
        setRedoStack(s => s.slice(0, -1));
        setUndoStack(s => [...s, JSON.parse(JSON.stringify(stages))]);
        setStages(next);
    }, [redoStack, stages, setStages]);

    // ── Stage Operations ───────────────────────────────────
    const addFilterStage = useCallback((filterKey) => {
        pushUndo(stages);
        const filterInfo = availableFilters.find(f => f.key === filterKey);
        const newStage = {
            ...JSON.parse(JSON.stringify(DEFAULT_FILTER_STAGE)),
            id: genId(),
            filter_key: filterKey,
            params: filterInfo?.default_params || {},
        };

        // Insert before the last signing stage, if one exists
        const signingIdx = stages.findIndex(s => s.type === 'signing');
        if (signingIdx >= 0) {
            const updated = [...stages];
            updated.splice(signingIdx, 0, newStage);
            setStages(updated);
        } else {
            setStages([...stages, newStage]);
        }
        setShowFilterPicker(false);
    }, [stages, setStages, pushUndo, availableFilters]);

    const removeStage = useCallback((stageId) => {
        pushUndo(stages);
        setStages(stages.filter(s => s.id !== stageId));
    }, [stages, setStages, pushUndo]);

    const duplicateStage = useCallback((stage) => {
        pushUndo(stages);
        const clone = {
            ...JSON.parse(JSON.stringify(stage)),
            id: genId(),
        };
        const idx = stages.findIndex(s => s.id === stage.id);
        const updated = [...stages];
        updated.splice(idx + 1, 0, clone);
        setStages(updated);
    }, [stages, setStages, pushUndo]);

    const updateStage = useCallback((stageId, newStage) => {
        setStages(stages.map(s => s.id === stageId ? newStage : s));
    }, [stages, setStages]);

    // ── Drag-and-drop ──────────────────────────────────────
    const dragIdx = useRef(null);

    const onDragStart = (e, index) => {
        dragIdx.current = index;
        e.dataTransfer.effectAllowed = 'move';
    };

    const onDragOver = (e, index) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    };

    const onDrop = (e, dropIndex) => {
        e.preventDefault();
        const fromIndex = dragIdx.current;
        if (fromIndex === null || fromIndex === dropIndex) return;

        pushUndo(stages);
        const updated = [...stages];
        const [moved] = updated.splice(fromIndex, 1);
        updated.splice(dropIndex, 0, moved);
        setStages(updated);
        dragIdx.current = null;
    };

    const onDragEnd = () => {
        dragIdx.current = null;
    };

    // Build filter metadata lookup from available filters
    const filterMeta = {};
    (availableFilters || []).forEach(f => {
        filterMeta[f.key] = f;
    });

    // Ensure signing stage exists
    useEffect(() => {
        if (!stages.find(s => s.type === 'signing')) {
            setStages([...stages, { ...DEFAULT_SIGNING_STAGE, id: genId() }]);
        }
    }, []);

    const hasFilters = stages.some(s => s.type === 'filter');

    return (
        <div className="stage-stack">
            {/* ── Header + Global Controls ──────────────────── */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <div className="section-title" style={{ marginBottom: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span>⚡ Pipeline</span>
                    {hasFilters && (
                        <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                            {stages.filter(s => s.type === 'filter' && s.enabled).length} active
                        </span>
                    )}
                </div>
                <div style={{ display: 'flex', gap: 4 }}>
                    <button
                        className="btn btn-sm"
                        onClick={undo}
                        disabled={undoStack.length === 0}
                        title="Undo (Ctrl+Z)"
                        style={{ padding: '3px 6px', fontSize: '0.7rem', opacity: undoStack.length === 0 ? 0.3 : 1 }}
                    >↶</button>
                    <button
                        className="btn btn-sm"
                        onClick={redo}
                        disabled={redoStack.length === 0}
                        title="Redo (Ctrl+Y)"
                        style={{ padding: '3px 6px', fontSize: '0.7rem', opacity: redoStack.length === 0 ? 0.3 : 1 }}
                    >↷</button>
                </div>
            </div>

            {/* Global intensity */}
            {hasFilters && (
                <div className="stage-card__control-row" style={{ marginBottom: 8, padding: '6px 8px', background: 'rgba(255,255,255,0.03)', borderRadius: 'var(--radius-sm)' }}>
                    <label style={{ fontSize: '0.7rem', fontWeight: 600 }}>Stack Amount</label>
                    <input
                        type="range" min="0" max="1" step="0.01"
                        value={globalIntensity}
                        onChange={(e) => setGlobalIntensity(parseFloat(e.target.value))}
                    />
                    <span className="stage-card__value">{Math.round(globalIntensity * 100)}%</span>
                </div>
            )}

            {/* ── Stage Cards ──────────────────────────────── */}
            <div className="stage-stack__cards">
                {stages.map((stage, idx) => (
                    <React.Fragment key={stage.id}>
                        {/* Pipeline divider before signing */}
                        {stage.type === 'signing' && idx > 0 && stages[idx - 1]?.type === 'filter' && (
                            <div className="pipeline-divider">
                                <span>─── · ─── · ───</span>
                            </div>
                        )}

                        <StageCard
                            stage={stage}
                            filterMeta={filterMeta}
                            index={idx}
                            onUpdate={updateStage}
                            onRemove={removeStage}
                            onDuplicate={duplicateStage}
                            onDragStart={onDragStart}
                            onDragOver={onDragOver}
                            onDragEnd={onDragEnd}
                            onDrop={onDrop}
                        />

                        {/* Pipeline divider after signing */}
                        {stage.type === 'signing' && idx < stages.length - 1 && stages[idx + 1]?.type === 'filter' && (
                            <div className="pipeline-divider">
                                <span>─── · ─── · ───</span>
                            </div>
                        )}
                    </React.Fragment>
                ))}
            </div>

            {/* ── Add Filter ───────────────────────────────── */}
            <div style={{ marginTop: 8 }}>
                {!showFilterPicker ? (
                    <button
                        className="btn btn-sm"
                        onClick={() => setShowFilterPicker(true)}
                        style={{
                            width: '100%', padding: '7px 12px', fontSize: '0.75rem',
                            borderStyle: 'dashed', color: 'var(--accent-cyan)',
                            borderColor: 'var(--accent-cyan)', background: 'transparent',
                        }}
                    >
                        + Add Filter Stage
                    </button>
                ) : (
                    <div className="stage-filter-picker">
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                            <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                Choose Filter
                            </span>
                            <button
                                className="stage-card__btn"
                                onClick={() => setShowFilterPicker(false)}
                            >✕</button>
                        </div>
                        {Object.entries(FILTER_FAMILIES).map(([familyKey, familyInfo]) => {
                            const familyFilters = (availableFilters || []).filter(f => f.family === familyKey);
                            if (familyFilters.length === 0) return null;
                            return (
                                <div key={familyKey} style={{ marginBottom: 6 }}>
                                    <div style={{
                                        fontSize: '0.62rem', fontWeight: 700, color: familyInfo.color,
                                        textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3,
                                    }}>
                                        {familyInfo.icon} {familyInfo.label}
                                    </div>
                                    {familyFilters.map(f => (
                                        <button
                                            key={f.key}
                                            className="btn btn-sm"
                                            onClick={() => addFilterStage(f.key)}
                                            style={{
                                                display: 'block', width: '100%', textAlign: 'left',
                                                marginBottom: 2, padding: '5px 10px', fontSize: '0.72rem',
                                            }}
                                        >
                                            {f.name}
                                            {f.description && (
                                                <span style={{ color: 'var(--text-muted)', fontSize: '0.62rem', marginLeft: 6 }}>
                                                    — {f.description.slice(0, 50)}
                                                </span>
                                            )}
                                        </button>
                                    ))}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
