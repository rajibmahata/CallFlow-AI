"""
WebSocket connection manager for live call feed broadcasts.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

import structlog

log = structlog.get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active.append(ws)
        log.info("ws.connected", total=len(self._active))

    def disconnect(self, ws: WebSocket) -> None:
        self._active = [c for c in self._active if c is not ws]
        log.info("ws.disconnected", total=len(self._active))

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        """Send a JSON message to all connected clients."""
        message = json.dumps({"event": event_type, "data": payload})
        dead: list[WebSocket] = []
        for ws in self._active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_to(self, ws: WebSocket, event_type: str, payload: dict[str, Any]) -> None:
        try:
            await ws.send_text(json.dumps({"event": event_type, "data": payload}))
        except Exception:
            self.disconnect(ws)


# Singleton instance shared across the app
ws_manager = ConnectionManager()
