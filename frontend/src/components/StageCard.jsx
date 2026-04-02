/**
 * StageCard.jsx — A single filter stage card in the pipeline stack
 *
 * Features:
 *   - Drag handle (☰ only) for reordering — sliders/controls won't trigger drag
 *   - On/off toggle
 *   - Intensity slider
 *   - Blend mode selector
 *   - Mask source selector
 *   - Expand/collapse for filter-specific params
 *   - Duplicate & delete buttons
 *   - Dynamic param rendering from get_param_schema()
 */

import React, { useState, useRef } from 'react';
import { BLEND_MODES, MASK_SOURCES, FILTER_FAMILIES } from '../utils/constants.js';

export default function StageCard({
    stage,
    filterMeta,
    index,
    onUpdate,
    onRemove,
    onDuplicate,
    onDragStart,
    onDragOver,
    onDragEnd,
    onDrop,
}) {
    const [expanded, setExpanded] = useState(false);
    const handleRef = useRef(null);

    const isFilter = stage.type === 'filter';
    const isSigning = stage.type === 'signing';

    const meta = isFilter && filterMeta ? filterMeta[stage.filter_key] : null;
    const familyInfo = meta ? FILTER_FAMILIES[meta.family] || {} : {};
    const displayName = isSigning ? '✍ Signing' : (meta?.name || stage.filter_key || 'Filter');
    const familyColor = familyInfo.color || 'var(--accent-cyan)';

    const updateField = (field, value) => {
        onUpdate(stage.id, { ...stage, [field]: value });
    };

    const updateParam = (key, value) => {
        onUpdate(stage.id, {
            ...stage,
            params: { ...stage.params, [key]: value },
        });
    };

    const paramSchema = meta?.param_schema || [];

    const handleRandomize = (e) => {
        e.stopPropagation();
        if (!paramSchema || paramSchema.length === 0) return;

        const newParams = { ...stage.params };
        paramSchema.forEach(p => {
            if (p.type === 'slider' || p.type === 'number') {
                const min = p.min ?? 0;
                const max = p.max ?? 1;
                let val = min + Math.random() * (max - min);
                if (p.step && Number.isInteger(p.step)) {
                    val = Math.round(val / p.step) * p.step;
                } else if (p.step && p.step >= 0.01) {
                    val = Math.round(val * 100) / 100; // Keep some precision
                }
                newParams[p.name] = val;
            } else if (p.type === 'select' && p.options) {
                const idx = Math.floor(Math.random() * p.options.length);
                newParams[p.name] = p.options[idx].value;
            } else if (p.type === 'color') {
                newParams[p.name] = [Math.floor(Math.random() * 256), Math.floor(Math.random() * 256), Math.floor(Math.random() * 256)];
            } else if (p.type === 'toggle') {
                newParams[p.name] = Math.random() > 0.5;
            }
        });

        onUpdate(stage.id, {
            ...stage,
            params: newParams,
        });
    };

    return (
        <div
            className={`stage-card ${!stage.enabled ? 'stage-card--disabled' : ''}`}
            onDragOver={(e) => { e.preventDefault(); onDragOver?.(e, index); }}
            onDrop={(e) => onDrop?.(e, index)}
            style={{ borderLeftColor: isSigning ? 'var(--accent-ember)' : familyColor }}
        >
            {/* Header row */}
            <div className="stage-card__header">
                <span
                    className="stage-drag-handle"
                    title="Drag to reorder"
                    ref={handleRef}
                    draggable
                    onDragStart={(e) => {
                        e.stopPropagation();
                        onDragStart?.(e, index);
                    }}
                    onDragEnd={(e) => {
                        e.stopPropagation();
                        onDragEnd?.();
                    }}
                >☰</span>

                <span
                    className="stage-card__name"
                    style={{ color: stage.enabled ? 'var(--text-primary)' : 'var(--text-muted)' }}
                >
                    {displayName}
                </span>

                {isFilter && meta && (
                    <span className="stage-card__family" style={{ color: familyColor }}>
                        {familyInfo.icon}
                    </span>
                )}

                <span style={{ flex: 1 }} />

                {/* Randomize */}
                {isFilter && paramSchema.length > 0 && (
                    <button
                        className="stage-card__btn"
                        onClick={handleRandomize}
                        title="Randomize parameters"
                    >
                        🎲
                    </button>
                )}

                {/* Expand/collapse for filters */}
                {isFilter && paramSchema.length > 0 && (
                    <button
                        className="stage-card__btn"
                        onClick={() => setExpanded(!expanded)}
                        title={expanded ? 'Collapse' : 'Expand params'}
                    >
                        {expanded ? '▾' : '▸'}
                    </button>
                )}

                {/* Duplicate */}
                <button
                    className="stage-card__btn"
                    onClick={() => onDuplicate?.(stage)}
                    title="Duplicate stage"
                >⧉</button>

                {/* Delete — not for signing */}
                {!isSigning && (
                    <button
                        className="stage-card__btn stage-card__btn--danger"
                        onClick={() => onRemove?.(stage.id)}
                        title="Remove stage"
                    >✕</button>
                )}

                {/* Toggle */}
                <label className="stage-toggle" title={stage.enabled ? 'Disable' : 'Enable'}>
                    <input
                        type="checkbox"
                        checked={stage.enabled}
                        onChange={(e) => updateField('enabled', e.target.checked)}
                    />
                    <span className="stage-toggle__track" />
                </label>
            </div>

            {/* Controls row — visible when enabled */}
            {stage.enabled && isFilter && (
                <div className="stage-card__controls">
                    {/* Intensity */}
                    <div className="stage-card__control-row">
                        <label>Intensity</label>
                        <input
                            type="range" min="0" max="1" step="0.01"
                            value={stage.intensity ?? 1}
                            onChange={(e) => updateField('intensity', parseFloat(e.target.value))}
                        />
                        <span className="stage-card__value">{Math.round((stage.intensity ?? 1) * 100)}%</span>
                    </div>

                    {/* Blend mode */}
                    <div className="stage-card__control-row">
                        <label>Blend</label>
                        <select
                            value={stage.blend_mode || 'normal'}
                            onChange={(e) => updateField('blend_mode', e.target.value)}
                        >
                            {BLEND_MODES.map(m => (
                                <option key={m.value} value={m.value}>{m.label}</option>
                            ))}
                        </select>
                    </div>

                    {/* Mask source */}
                    <div className="stage-card__control-row">
                        <label>Mask</label>
                        <select
                            value={stage.mask_source || 'global'}
                            onChange={(e) => updateField('mask_source', e.target.value)}
                        >
                            {MASK_SOURCES.map(m => (
                                <option key={m.value} value={m.value}>{m.label}</option>
                            ))}
                        </select>
                    </div>
                </div>
            )}

            {/* Expanded params */}
            {expanded && stage.enabled && isFilter && paramSchema.length > 0 && (
                <div className="stage-card__params">
                    {paramSchema.map(p => (
                        <div key={p.key} className="stage-card__control-row">
                            <label>{p.label}</label>
                            {p.type === 'slider' && (
                                <>
                                    <input
                                        type="range"
                                        min={p.min} max={p.max} step={p.step}
                                        value={stage.params?.[p.key] ?? p.default}
                                        onChange={(e) => updateParam(p.key, parseFloat(e.target.value))}
                                    />
                                    <span className="stage-card__value">
                                        {(stage.params?.[p.key] ?? p.default).toFixed?.(2) ?? stage.params?.[p.key] ?? p.default}
                                    </span>
                                </>
                            )}
                            {p.type === 'number' && (
                                <input
                                    type="number"
                                    min={p.min} max={p.max}
                                    value={stage.params?.[p.key] ?? p.default}
                                    onChange={(e) => updateParam(p.key, parseFloat(e.target.value))}
                                    className="stage-card__number-input"
                                />
                            )}
                            {p.type === 'select' && (
                                <select
                                    value={stage.params?.[p.key] ?? p.default}
                                    onChange={(e) => {
                                        const raw = e.target.value;
                                        const val = isNaN(raw) ? raw : Number(raw);
                                        updateParam(p.key, val);
                                    }}
                                >
                                    {(p.options || []).map(opt => {
                                        const val = typeof opt === 'object' ? opt.value : opt;
                                        const lbl = typeof opt === 'object' ? opt.label : opt;
                                        return <option key={val} value={val}>{lbl}</option>;
                                    })}
                                </select>
                            )}
                            {p.type === 'toggle' && (
                                <label className="stage-toggle stage-toggle--mini">
                                    <input
                                        type="checkbox"
                                        checked={stage.params?.[p.key] ?? p.default}
                                        onChange={(e) => updateParam(p.key, e.target.checked)}
                                    />
                                    <span className="stage-toggle__track" />
                                </label>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
