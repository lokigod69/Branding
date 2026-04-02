"""
LAZART Signing Engine (LSE) — Main Entry Point
Serves the React frontend + FastAPI backend on localhost:8001
"""

import os
import sys
import webbrowser
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ── Paths ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"
FONTS_DIR = BASE_DIR / "fonts"
PRESETS_DIR = BASE_DIR / "presets"
UPLOAD_DIR = BASE_DIR / "uploads"

# Ensure runtime directories exist
for d in [OUTPUT_DIR, FONTS_DIR, PRESETS_DIR, UPLOAD_DIR, STATIC_DIR]:
    d.mkdir(exist_ok=True)

PORT = int(os.environ.get("LSE_PORT", 5555))


# ── Lifespan ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open browser on startup."""
    url = f"http://localhost:{PORT}"
    print(f"\n  🔥 LAZART Signing Engine running at {url}\n")
    if not os.environ.get("LSE_DEV"):
        webbrowser.open(url)
    yield


# ── App ────────────────────────────────────────────────────
app = FastAPI(
    title="LAZART Signing Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", f"http://localhost:{PORT}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ─────────────────────────────────────────────
from api.routes import router as api_router
app.include_router(api_router, prefix="/api")

# ── WebSocket ──────────────────────────────────────────────
from api.websocket import router as ws_router
app.include_router(ws_router)

# ── Serve frontend (static build) ─────────────────────────
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback — serve index.html for all non-API routes."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def dev_placeholder():
        return {
            "message": "LAZART Signing Engine API is running.",
            "docs": f"http://localhost:{PORT}/docs",
            "note": "Run the Vite dev server (cd frontend && npm run dev) for the UI.",
        }


# ── Entry point ────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        reload_dirs=[str(BASE_DIR / "engine"), str(BASE_DIR / "api")],
    )
