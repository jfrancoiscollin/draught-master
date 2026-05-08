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
    """Long-running Scan subprocess communicating via Hub protocol v2.

    Spawns a single persistent process and keeps it alive for the lifetime
    of the application. All communication is line-delimited text over stdin/
    stdout; a background thread drains stdout into a thread-safe queue so the
    main thread never blocks on I/O.

    Two singletons are maintained at module level:
      - _engine       (use_book=True)  — used for best_move() calls
      - _eval_engine  (use_book=False) — used for evaluate_pos() calls

    The book cannot be disabled at runtime via set-param once Scan has loaded
    it, so the two instances must be separate processes.
    """

    def __init__(self, path: str, use_book: bool = True) -> None:
        """Launch the Scan subprocess and complete the Hub v2 handshake.

        Sends: hub → set-param variant=normal → set-param book → set-param bb-size=0 → init
        Waits for: 'wait' (after hub) and 'ready' (after init).

        Args:
            path: Absolute path to the Scan binary.
            use_book: Whether to enable the built-in opening book.

        Raises:
            RuntimeError: If the process exits immediately or the handshake times out.
        """
        import subprocess
        self._use_book = use_book
        # CWD must be the backend dir so Scan finds data/eval relative to itself
        cwd = os.path.dirname(os.path.abspath(__file__))

        # Log the data/eval file size to diagnose LFS pointer issues
        data_dir = os.path.join(cwd, "data")
        if os.path.isdir(data_dir):
            files = os.listdir(data_dir)
            logger.info("Scan data dir %s: %s", data_dir, files)
            for f in files:
                fp = os.path.join(data_dir, f)
                logger.info("  %s: %d bytes", f, os.path.getsize(fp))
        else:
            logger.warning("Scan data dir not found: %s", data_dir)

        self._stderr_lines: list[str] = []
        self._proc = subprocess.Popen(
            [path, "hub"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=cwd,
        )
        self._q: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        t = threading.Thread(target=self._read_loop, daemon=True)
        t.start()
        t2 = threading.Thread(target=self._stderr_loop, daemon=True)
        t2.start()
        self._init()

    def _read_loop(self) -> None:
        assert self._proc.stdout
        for raw in self._proc.stdout:
            line = raw.strip()
            if line:
                self._q.put(line)

    def _stderr_loop(self) -> None:
        assert self._proc.stderr
        for raw in self._proc.stderr:
            line = raw.strip()
            if line:
                logger.warning("Scan stderr: %s", line)

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
        # The book must be set BEFORE init — set-param after init does NOT unload
        # an already-loaded book, so book positions still return score=0.
        self._send(f"set-param name=book value={'true' if self._use_book else 'false'}")
        self._send("set-param name=bb-size value=0")
        self._send("init")
        result = self._wait_for("ready", timeout=10.0)
        if result is None:
            raise RuntimeError("Scan did not send 'ready' after init")
        logger.info("Scan ready (use_book=%s)", self._use_book)

    def best_move(self, pos: str, movetime_s: float) -> Optional[str]:
        """Ask Scan for the best move and return the Hub notation string.

        Sends: pos pos=<pos> → level move-time=<t> → go think
        Waits for a 'done move=...' response.

        Args:
            pos: 51-char Hub position string (turn char + 50 piece chars).
            movetime_s: Maximum thinking time in seconds.

        Returns:
            Hub move notation such as '37-32' or '26x17x8', or None on timeout.
        """
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
        """Evaluate a position using 'go think'.
        'go think' forces a real neural-network search unlike 'go analyze' which
        returns score=0 for book positions. The score comes from 'info' lines;
        the best move comes from the final 'done' line.
        Returns {"score": int, "bestMove": str|None}."""
        with self._lock:
            while True:
                try:
                    self._q.get_nowait()
                except queue.Empty:
                    break

            self._send(f"pos pos={pos}")
            self._send(f"level move-time={movetime_s}")
            self._send("go think")

            last_score: float = 0.0
            last_best: Optional[str] = None
            had_info_score = False
            deadline = time.monotonic() + movetime_s + 10.0
            raw_lines: list[str] = []

            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    line = self._q.get(timeout=min(0.05, remaining))
                    raw_lines.append(line)
                    if line.startswith("info "):
                        s = re.search(r'\bscore=\s*([+-]?\d+(?:\.\d+)?)', line)
                        p = re.search(r'\bpv="([^"]*)"', line)
                        if s:
                            last_score = float(s.group(1))
                            had_info_score = True
                        if p:
                            words = p.group(1).strip().split()
                            if words:
                                last_best = words[0]
                        elif not p:
                            # pv without quotes = forced move (no score emitted)
                            pf = re.search(r'\bpv=(\S+)', line)
                            if pf and not last_best:
                                last_best = pf.group(1).split()[0]
                    elif line.startswith("done") and (len(line) == 4 or line[4] == ' '):
                        move_m = re.search(r'\bmove=(\S+)', line)
                        score_m = re.search(r'\bscore=\s*([+-]?\d+(?:\.\d+)?)', line)
                        best = (move_m.group(1) if move_m else None) or last_best
                        score = float(score_m.group(1)) if score_m else last_score
                        # forced=True when no info line had a score (Scan returned
                        # the move immediately without searching — forced capture)
                        forced = not had_info_score and score == 0.0
                        logger.debug("evaluate_pos done: score=%.3f best=%s forced=%s", score, best, forced)
                        return {"bestMove": best, "score": score, "forced": forced}
                except queue.Empty:
                    pass

        logger.warning("evaluate_pos: timeout, no done.")
        return None

    def alive(self) -> bool:
        return self._proc.poll() is None


# ── Singletons ─────────────────────────────────────────────────────────────

_engine: Optional[ScanEngine] = None          # with book  — used for best_move()
_eval_engine: Optional[ScanEngine] = None     # no book    — used for evaluate_pos()
_engine_unavailable = False
_engine_lock = threading.Lock()


def _get_engine(use_book: bool = True) -> Optional[ScanEngine]:
    """Return the appropriate engine singleton, creating it if necessary.

    Returns None when Scan is unavailable (binary missing, too small, or
    previously crashed). The _engine_unavailable flag prevents repeated
    startup attempts after a confirmed failure.
    """
    global _engine, _eval_engine, _engine_unavailable
    if _engine_unavailable:
        return None
    if not os.path.isfile(SCAN_PATH) or os.path.getsize(SCAN_PATH) < 1000:
        return None
    with _engine_lock:
        if use_book:
            if _engine is None or not _engine.alive():
                try:
                    _engine = ScanEngine(SCAN_PATH, use_book=True)
                    logger.info("Scan engine (with book) started at %s", SCAN_PATH)
                except Exception as exc:
                    logger.warning("Could not start Scan engine: %s", exc)
                    _engine = None
                    _engine_unavailable = True
            return _engine
        else:
            if _eval_engine is None or not _eval_engine.alive():
                try:
                    _eval_engine = ScanEngine(SCAN_PATH, use_book=False)
                    logger.info("Scan eval engine (no book) started at %s", SCAN_PATH)
                except Exception as exc:
                    logger.warning("Could not start Scan eval engine: %s", exc)
                    _eval_engine = None
                    _engine_unavailable = True
            return _eval_engine


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
