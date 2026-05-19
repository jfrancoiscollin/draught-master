"""In-process WebSocket presence and broadcast for live PvP.

The :class:`ConnectionManager` holds one :class:`WebSocket` per
``user_id`` and pushes messages to the right socket. It's deliberately
in-memory: the v1 cadrage (see ``docs/PVP_LIVE.md``) targets a single
Railway dyno and accepts that a redeploy drops live sessions. Moving
to Redis pub/sub for horizontal scaling is documented as a v2 risk.

Concurrency model: all mutations of the ``_connections`` dict go
through a single :class:`asyncio.Lock` — connection churn is low (a
handful per minute even at peak), the lock is held microseconds, and
the alternative (per-key sharding) buys nothing at this scale.

The module exports a single ``manager`` singleton; do not instantiate
:class:`ConnectionManager` elsewhere. Tests reset it via
:meth:`ConnectionManager.reset`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from fastapi import WebSocket

_log = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, ws: WebSocket) -> Optional[WebSocket]:
        """Register ``ws`` as the current connection for ``user_id``.

        Returns the previously-registered socket if any — caller should
        close it with a ``kicked_by_other_session`` frame. Single
        connection per user is enforced (matches the cadrage's
        "mobile or desktop, not both at once" rule).
        """
        async with self._lock:
            old = self._connections.get(user_id)
            self._connections[user_id] = ws
            return old

    async def disconnect(self, user_id: int, ws: WebSocket) -> None:
        """Remove ``ws`` from the registry, but only if it's still the
        active one. This avoids a race where a fresh tab connects
        between the previous tab's last frame and its cleanup.
        """
        async with self._lock:
            current = self._connections.get(user_id)
            if current is ws:
                del self._connections[user_id]

    async def send_to(self, user_id: int, msg: dict[str, Any]) -> bool:
        """Push ``msg`` (any JSON-serialisable dict) to ``user_id``.

        Returns True if the message was queued on a live socket, False
        if the user isn't connected or the send raised. Callers
        treating notifications as best-effort (e.g. challenge pushes)
        can ignore the return value; the receiving end will refetch
        via REST on next connection if needed.
        """
        ws = self._connections.get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_json(msg)
            return True
        except Exception as exc:  # noqa: BLE001
            _log.warning("send_to user_id=%s failed: %s", user_id, exc)
            return False

    def is_online(self, user_id: int) -> bool:
        return user_id in self._connections

    def online_count(self) -> int:
        return len(self._connections)

    async def reset(self) -> None:
        """Drop every registered socket without sending anything.
        Test-only helper — not exposed via the public surface."""
        async with self._lock:
            self._connections.clear()


# Module-level singleton. Importers use this, not a fresh instance.
manager = ConnectionManager()
