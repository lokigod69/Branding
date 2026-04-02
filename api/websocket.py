"""
websocket.py — WebSocket endpoint for batch export progress

Provides real-time progress updates during batch processing.
"""

import asyncio
import json
from typing import Dict, Any, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Active WebSocket connections
_connections: list[WebSocket] = []


@router.websocket("/ws/progress")
async def progress_websocket(websocket: WebSocket):
    """WebSocket endpoint for progress updates."""
    await websocket.accept()
    _connections.append(websocket)

    try:
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Client can send ping/keep-alive messages
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        _connections.remove(websocket)
    except Exception:
        if websocket in _connections:
            _connections.remove(websocket)


async def broadcast_progress(
    current: int, total: int, image_name: str, status: str
):
    """Broadcast progress to all connected WebSocket clients."""
    message = json.dumps({
        "type": "progress",
        "current": current,
        "total": total,
        "image": image_name,
        "status": status,
        "percent": round((current / total) * 100) if total > 0 else 0,
    })

    disconnected = []
    for ws in _connections:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        _connections.remove(ws)
