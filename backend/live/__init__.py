"""Live PvP module — challenges + (later) WebSocket transport for
real-time games between Draught Master users.

J1 surface: REST endpoints for the challenge queue. WebSocket layer +
in-flight game state machine land on subsequent days. See
``docs/PVP_LIVE.md`` for the full cadrage.
"""

from .api import router

__all__ = ["router"]
