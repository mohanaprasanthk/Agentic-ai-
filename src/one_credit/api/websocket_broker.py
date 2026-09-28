from __future__ import annotations

import asyncio
import json
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class WebSocketEventBroker:
    """Tracks live simulation subscriptions and broadcasts structured events."""

    def __init__(self) -> None:
        self._clients: defaultdict[str, set[WebSocket]] = defaultdict(set)
        self._known_simulations: set[str] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def set_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop

    def register_simulation(self, simulation_id: str) -> None:
        if not simulation_id:
            return
        with self._lock:
            self._known_simulations.add(simulation_id)

    def is_known_simulation(self, simulation_id: str) -> bool:
        return bool(simulation_id) and (simulation_id in self._known_simulations)

    def subscribe(self, simulation_id: str, websocket: WebSocket) -> None:
        self.register_simulation(simulation_id)
        self._clients[simulation_id].add(websocket)

    def unsubscribe(self, simulation_id: str, websocket: WebSocket) -> None:
        clients = self._clients.get(simulation_id)
        if clients is None:
            return
        clients.discard(websocket)
        if not clients:
            self._clients.pop(simulation_id, None)

    @staticmethod
    def _event_type_for(raw_event: dict[str, Any]) -> str:
        candidates = [
            raw_event.get("event_type"),
            raw_event.get("type"),
            raw_event.get("step"),
            raw_event.get("stage"),
            raw_event.get("status"),
        ]
        for candidate in candidates:
            if candidate is None:
                continue
            normalized = str(candidate).upper()
            if normalized in {"REQUEST", "PROPOSAL", "COUNTEROFFER", "ACCEPT", "REJECT", "AGREEMENT", "SIMULATION_STARTED", "SIMULATION_COMPLETED", "SIMULATION_FAILED"}:
                return normalized
            if normalized in {"REQUEST_VALIDATION", "REQUEST_VALIDATION", "NEGOTIATION"}:
                return "REQUEST" if normalized == "REQUEST_VALIDATION" else "PROPOSAL"
            if normalized in {"PROPOSAL", "AGREEMENT", "REJECTION", "ACCEPTED", "COUNTEROFFER"}:
                return {
                    "PROPOSAL": "PROPOSAL",
                    "AGREEMENT": "AGREEMENT",
                    "REJECTION": "REJECT",
                    "ACCEPTED": "ACCEPT",
                    "COUNTEROFFER": "COUNTEROFFER",
                }[normalized]
        return "PROPOSAL"

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(key): WebSocketEventBroker._serialize_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [WebSocketEventBroker._serialize_value(item) for item in value]
        if hasattr(value, "model_dump"):
            return WebSocketEventBroker._serialize_value(value.model_dump())
        if isinstance(value, (datetime,)):
            return value.isoformat()
        if isinstance(value, (type,)):
            return str(value)
        return str(value)

    @classmethod
    def normalize_event(cls, simulation_id: str, raw_event: dict[str, Any]) -> dict[str, Any]:
        raw_payload = raw_event.copy() if isinstance(raw_event, dict) else {}
        payload = {k: cls._serialize_value(v) for k, v in raw_payload.items() if k not in {"event_type", "type", "step", "stage"}}
        event_type = cls._event_type_for(raw_event)
        return {
            "event_type": event_type,
            "simulation_id": simulation_id,
            "timestamp": payload.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "agent_id": payload.get("agent_id") or payload.get("actor_id") or payload.get("requester_id"),
            "resource_id": payload.get("resource_id") or payload.get("resource_name") or payload.get("resource_id"),
            "message": payload.get("message") or payload.get("content") or payload.get("reason") or payload.get("status"),
            "payload": payload,
        }

    def publish_event_sync(self, simulation_id: str, event: dict[str, Any]) -> None:
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.publish_event(simulation_id, event), self._loop)
            try:
                future.result(timeout=2)
            except Exception:
                pass
            return
        try:
            asyncio.run(self.publish_event(simulation_id, event))
        except RuntimeError:
            pass

    async def publish_event(self, simulation_id: str, event: dict[str, Any]) -> None:
        self.register_simulation(simulation_id)
        if not event:
            return
        try:
            normalized = self.normalize_event(simulation_id, event)
            json.dumps(normalized)
        except Exception:
            return
        clients = list(self._clients.get(simulation_id, set()))
        for websocket in clients:
            try:
                await websocket.send_json(normalized)
            except Exception:
                self.unsubscribe(simulation_id, websocket)


__all__ = ["WebSocketEventBroker"]
