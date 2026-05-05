"""
Wrapper around the Scan draughts engine (Hub protocol v2).
Falls back gracefully to None if the binary is not available.
"""
from __future__ import annotations

import logging
import os
import queue
import re
import threading
import time
from typing import Optional

from game_engine import (
    GameState, Move, get_legal_moves,
    EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
)

logger = logging.getLogger(__name__)

SCAN_PATH = os.environ.get("SCAN_PATH", "/usr/local/bin/scan")

# Thinking time per level (seconds) — Scan at 500 ms is already master-level
TIME_LIMITS = {
    1: 0.02, 2: 0.05, 3: 0.1, 4: 0.15,
    5: 0.2,  6: 0.3,  7: 0.4, 8: 0.5,
}

_PIECE_CHAR = {
    EMPTY: 'e',
    WHITE_MAN: 'w',
    WHITE_KING: 'W',
    BLACK_MAN: 'b',
    BLACK_KING: 'B',
}


def _build_pos(state: GameState) -> str:
    """Build the 51-char Hub position string (turn + 50 square chars)."""
    turn_char = 'W' if state.turn == 'white' else 'B'
    return turn_char + ''.join(_PIECE_CHAR[state.board[sq]] for sq in range(1, 51))


class ScanEngine:
    """Long-running Scan subprocess communicating via Hub protocol v2."""

    def __init__(self, path: str) -> None:
        import subprocess
        # CWD must be the backend dir so Scan finds data/eval relative to itself
        cwd = os.path.dirname(os.path.abspath(__file__))
        self._proc = subprocess.Popen(
            [path, "hub"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            cwd=cwd,
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
                line = self._q.get(timeout=min(0.02, remaining))
                if line.startswith(prefix):
                    return line
            except queue.Empty:
                pass

    def _init(self) -> None:
        self._send("hub")
        # Quick crash detection — if the binary is broken it exits immediately
        time.sleep(0.3)
        if self._proc.poll() is not None:
            raise RuntimeError(f"Scan process exited (code {self._proc.returncode})")
        result = self._wait_for("wait", timeout=5.0)
        if result is None:
            raise RuntimeError("Scan did not send 'wait' during handshake")
        self._send("set-param name=variant value=normal")
        self._send("set-param name=book value=false")
        self._send("set-param name=bb-size value=0")
        self._send("init")
        result = self._wait_for("ready", timeout=10.0)
        if result is None:
            raise RuntimeError("Scan did not send 'ready' after init")

    def best_move(self, pos: str, movetime_s: float) -> Optional[str]:
        with self._lock:
            # Drain any stale output from a previous search
            while True:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break

            self._send(f"pos pos={pos}")
            self._send(f"level move-time={movetime_s}")
            self._send("go think")

            resp = self._wait_for("done ", timeout=movetime_s + 10.0)
            if resp:
                m = re.search(r'move=(\S+)', resp)
                if m:
                    return m.group(1)
        return None

    def evaluate_pos(self, pos: str, movetime_s: float) -> Optional[dict]:
        """Evaluate one position; returns {"score": int, "bestMove": str|None} or None."""
        with self._lock:
            while True:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break
            self._send(f"pos pos={pos}")
            self._send(f"level move-time={movetime_s}")
            self._send("go think")
            resp = self._wait_for("done ", timeout=movetime_s + 10.0)
            if resp:
                move_m = re.search(r'move=(\S+)', resp)
                score_m = re.search(r'score=([+-]?\d+)', resp)
                return {
                    "bestMove": move_m.group(1) if move_m else None,
                    "score": int(score_m.group(1)) if score_m else 0,
                }
        return None

    def alive(self) -> bool:
        return self._proc.poll() is None


# ── Singleton ──────────────────────────────────────────────────────────────

_engine: Optional[ScanEngine] = None
_engine_unavailable = False  # set after first failure to avoid retrying every move
_engine_lock = threading.Lock()


def _get_engine() -> Optional[ScanEngine]:
    global _engine, _engine_unavailable
    if _engine_unavailable:
        return None
    if not os.path.isfile(SCAN_PATH) or os.path.getsize(SCAN_PATH) < 1000:
        return None
    with _engine_lock:
        if _engine is None or not _engine.alive():
            try:
                _engine = ScanEngine(SCAN_PATH)
                logger.info("Scan engine started at %s", SCAN_PATH)
            except Exception as exc:
                logger.warning("Could not start Scan engine: %s", exc)
                _engine = None
                _engine_unavailable = True  # don't block future moves with retries
        return _engine


# ── Move parsing ───────────────────────────────────────────────────────────

def _parse_move(notation: str, state: GameState) -> Optional[Move]:
    """
    Convert Scan Hub notation to a Move object.

    Quiet:   '37-32'
    Capture: '26x17' or '26x17x8' — x-separated values are the landing squares
             (from, intermediate landings..., final landing).
    """
    legal = get_legal_moves(state)

    if "x" in notation:
        try:
            squares = [int(p) for p in notation.split("x")]
        except ValueError:
            return None

        start, end = squares[0], squares[-1]

        # Exact path match (Scan outputs the full sequence of landing squares)
        for m in legal:
            if m.path == squares:
                return m

        # Abbreviated notation — match by start and end squares only
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

    movetime_s = TIME_LIMITS.get(depth, 5.0)
    pos = _build_pos(state)

    try:
        notation = engine.best_move(pos, movetime_s)
        if notation:
            move = _parse_move(notation, state)
            if move:
                logger.debug("Scan played %s", notation)
                return move
            logger.warning("Could not parse Scan move: %r", notation)
    except Exception as exc:
        logger.warning("Scan engine error: %s", exc)

    return None
