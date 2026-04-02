// API utility functions
const API_BASE = '/api';

export async function uploadImages(files) {
    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }
    const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
    return res.json();
}

export async function listImages() {
    const res = await fetch(`${API_BASE}/images`);
    return res.json();
}

export async function deleteImage(id) {
    const res = await fetch(`${API_BASE}/images/${id}`, { method: 'DELETE' });
    return res.json();
}

export async function replaceImage(id, file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/images/${id}/replace`, { method: 'POST', body: formData });
    return res.json();
}

export async function generatePreview(params) {
    const res = await fetch(`${API_BASE}/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    });
    return res.json();
}

export async function generateMaskPreview(params) {
    const res = await fetch(`${API_BASE}/preview/mask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    });
    return res.json();
}

export async function exportImage(params) {
    const res = await fetch(`${API_BASE}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    });
    return res.json();
}

export async function batchExport(params) {
    const res = await fetch(`${API_BASE}/batch/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    });
    return res.json();
}

export async function getPresets() {
    const res = await fetch(`${API_BASE}/presets`);
    return res.json();
}

export async function getPreset(name) {
    const res = await fetch(`${API_BASE}/presets/${name}`);
    return res.json();
}

export async function savePreset(data) {
    const res = await fetch(`${API_BASE}/presets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    return res.json();
}

export async function getCustomFonts() {
    const res = await fetch(`${API_BASE}/fonts`);
    return res.json();
}

export async function uploadFont(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/fonts`, { method: 'POST', body: formData });
    return res.json();
}

export async function getSystemFonts() {
    const res = await fetch(`${API_BASE}/system-fonts`);
    return res.json();
}

export async function getEffects() {
    const res = await fetch(`${API_BASE}/effects`);
    return res.json();
}

// ── Pipeline (v2) ─────────────────────────────────────────

export async function pipelinePreview(params) {
    const res = await fetch(`${API_BASE}/pipeline/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    });
    return res.json();
}

export async function pipelineExport(params) {
    const res = await fetch(`${API_BASE}/pipeline/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
    });
    return res.json();
}

export async function getFilters() {
    const res = await fetch(`${API_BASE}/filters`);
    return res.json();
}
