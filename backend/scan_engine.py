"""
Wrapper around the Scan draughts engine (Hub protocol).
Falls back gracefully to None if the binary is not available.

Hub protocol reference: https://github.com/rhalbersma/scan
"""
from __future__ import annotations

import logging
import os
import queue
import threading
import time
from typing import Optional

from game_engine import GameState, Move, board_to_fen, get_legal_moves

logger = logging.getLogger(__name__)

SCAN_PATH = os.environ.get("SCAN_PATH", "/usr/local/bin/scan")

# Thinking time per level (ms) — mirrors ai_engine TIME_LIMITS
TIME_LIMITS_MS = {
    1: 300, 2: 600, 3: 1200, 4: 2000,
    5: 3500, 6: 5500, 7: 8000, 8: 10000,
}


class ScanEngine:
    """Long-running Scan subprocess communicating via Hub protocol."""

    def __init__(self, path: str) -> None:
        self._proc = __import__("subprocess").Popen(
            [path, "hub"],
            stdin=__import__("subprocess").PIPE,
            stdout=__import__("subprocess").PIPE,
            stderr=__import__("subprocess").DEVNULL,
            text=True,
            bufsize=1,
        )
        self._q: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        t = threading.Thread(target=self._read_loop, daemon=True)
        t.start()
        self._init()

    def _read_loop(self) -> None:
        assert self._proc.stdout
        for raw in self._proc.stdout:
            line = raw.strip()
            if line:
                self._q.put(line)

    def _send(self, cmd: str) -> None:
        assert self._proc.stdin
        self._proc.stdin.write(cmd + "\n")
        self._proc.stdin.flush()

    def _wait_for(self, prefix: str, timeout: float) -> Optional[str]:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                line = self._q.get(timeout=min(0.15, remaining))
                if line.startswith(prefix):
                    return line
            except queue.Empty:
                pass

    def _init(self) -> None:
        self._send("init")
        self._wait_for("done", timeout=10.0)
        # Disable book and endgame bitbases (not available on server)
        self._send("setoption name variant value normal")
        self._send("setoption name book value false")
        self._send("setoption name bb-size value 0")

    def best_move(self, fen: str, movetime_ms: int) -> Optional[str]:
        with self._lock:
            # Drain any stale output
            while True:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break

            self._send("newgame")
            self._send(f"pos {fen}")
            self._send(f"go movetime {movetime_ms}")

            resp = self._wait_for("move ", timeout=movetime_ms / 1000 + 5.0)
            if resp and resp.startswith("move "):
                return resp[5:].strip()
            return None

    def alive(self) -> bool:
        return self._proc.poll() is None


# ── Singleton ──────────────────────────────────────────────────────────────

_engine: Optional[ScanEngine] = None
_engine_lock = threading.Lock()


def _get_engine() -> Optional[ScanEngine]:
    global _engine
    if not os.path.isfile(SCAN_PATH):
        return None
    with _engine_lock:
        if _engine is None or not _engine.alive():
            try:
                _engine = ScanEngine(SCAN_PATH)
                logger.info("Scan engine started at %s", SCAN_PATH)
            except Exception as exc:
                logger.warning("Could not start Scan engine: %s", exc)
                _engine = None
        return _engine


# ── Move parsing ───────────────────────────────────────────────────────────

def _parse_move(notation: str, state: GameState) -> Optional[Move]:
    """
    Convert Scan Hub notation to a Move object.

    Scan can output:
      quiet:    '37-32'
      capture:  '26x17'  or  '26x17x8'  (full path or abbreviated)
    """
    legal = get_legal_moves(state)

    if "x" in notation:
        try:
            squares = [int(p) for p in notation.split("x")]
        except ValueError:
            return None

        start, end = squares[0], squares[-1]

        # 1. Exact path match (full path notation)
        for m in legal:
            if m.path == squares:
                return m

        # 2. Start + end match (abbreviated notation, e.g. '26x8')
        candidates = [
            m for m in legal
            if m.path[0] == start and m.path[-1] == end and m.captures
        ]
        return candidates[0] if candidates else None

    elif "-" in notation:
        try:
            parts = notation.split("-")
            frm, to = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return None
        for m in legal:
            if m.path[0] == frm and m.path[-1] == to and not m.captures:
                return m

    return None


# ── Public API ─────────────────────────────────────────────────────────────

def get_scan_move(state: GameState, depth: int) -> Optional[Move]:
    """
    Ask Scan for the best move.  Returns None if Scan is unavailable
    or fails, so the caller can fall back to the Python minimax.
    """
    engine = _get_engine()
    if engine is None:
        return None

    movetime_ms = TIME_LIMITS_MS.get(depth, 5000)
    fen = board_to_fen(state)

    try:
        notation = engine.best_move(fen, movetime_ms)
        if notation:
            move = _parse_move(notation, state)
            if move:
                logger.debug("Scan played %s", notation)
                return move
            logger.warning("Could not parse Scan move: %r", notation)
    except Exception as exc:
        logger.warning("Scan engine error: %s", exc)

    return None
