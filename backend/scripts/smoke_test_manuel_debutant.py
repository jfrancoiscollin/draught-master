"""Smoke test du manuel Débutant côté draught-master.

Vérifie que les 166 fixtures du manuel Débutant (préprocessées par
Claude via dilf, voir `dilf/docs/pre_process_corpus/`) sont
consommables par le backend draught-master, sans toucher à l'UI ni à
la base d'exercices.

Trois contrôles :

1. **Round-trip FEN** : `dilf.state_to_fen` → `game_engine.fen_to_board`
   → `game_engine.board_to_fen` doit produire la même FEN sur les 166.

2. **Légalité du `final_move`** : pour les 135 fixtures avec
   `final_move` non None, on rejoue `published_notation` via le module
   `pedagogy.notation.dubois` de dilf jusqu'à atteindre l'état pré-final,
   puis on convertit cet état en FEN, on le passe à
   `game_engine.fen_to_board`, et on vérifie que le `final_move` (Move
   dilf) apparaît bien dans `game_engine.get_legal_moves`. C'est le test
   qui démontre que draught-master accepte les rafles produites par le
   pipeline manuel.

3. **Statistiques** par chapitre et par source (CORPUS / GENERAL /
   INVENTED).

Lancer :

    cd backend && python -m scripts.smoke_test_manuel_debutant
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from pedagogy.game import GameState as DilfGameState  # noqa: E402
from pedagogy.game import state_to_fen as dilf_state_to_fen  # noqa: E402
from pedagogy.notation.dubois import (  # noqa: E402
    AmbiguousRafleError,
    NoSuchRafleError,
    NotAManError,
    enumerate_pawn_captures,
    reconstruct_pawn_capture,
)

from game_engine import (  # noqa: E402
    Move,
    board_to_fen,
    fen_to_board,
    get_legal_moves,
)
from manuels import fixtures_debutant as manuel  # noqa: E402


# ---------------------------------------------------------------------------
# Rejeu de `published_notation` (logique alignée avec
# dilf/docs/pre_process_corpus/validate_final_moves.py)
# ---------------------------------------------------------------------------


def apply_simple(state: DilfGameState, frm: int, to: int) -> DilfGameState:
    if frm in state.white_men:
        return DilfGameState(
            white_men=(state.white_men - {frm}) | {to},
            white_kings=state.white_kings,
            black_men=state.black_men,
            black_kings=state.black_kings,
            turn="black",
        )
    if frm in state.black_men:
        return DilfGameState(
            white_men=state.white_men,
            white_kings=state.white_kings,
            black_men=(state.black_men - {frm}) | {to},
            black_kings=state.black_kings,
            turn="white",
        )
    raise ValueError(f"Aucun pion en {frm}")


def apply_capture(state: DilfGameState, m) -> DilfGameState:
    captures = set(m.captures)
    if m.from_square in state.white_men:
        return DilfGameState(
            white_men=(state.white_men - {m.from_square}) | {m.to_square},
            white_kings=state.white_kings,
            black_men=state.black_men - captures,
            black_kings=state.black_kings - captures,
            turn="black",
        )
    return DilfGameState(
        white_men=state.white_men - captures,
        white_kings=state.white_kings - captures,
        black_men=(state.black_men - {m.from_square}) | {m.to_square},
        black_kings=state.black_kings,
        turn="white",
    )


def parse_tokens(notation: str) -> list[tuple[str, int | None, int | None]]:
    out: list[tuple[str, int | None, int | None]] = []
    tokens = re.findall(r"\([^)]+\)|\S+", notation)
    for tok in tokens:
        inside = tok.startswith("(") and tok.endswith(")")
        body = tok[1:-1] if inside else tok
        if "ad lib" in body.lower():
            out.append(("ad_lib", None, None))
            continue
        if "-" not in body and "x" not in body:
            continue
        if " " in body or any(c.isalpha() for c in body.replace("x", "").replace("-", "")):
            continue
        if "-" in body:
            f, t = body.split("-")
            out.append(("reply_simple" if inside else "simple", int(f), int(t)))
        elif "x" in body:
            parts = body.split("x")
            out.append(("reply_capture" if inside else "capture", int(parts[0]), int(parts[-1])))
    return out


def replay_until_final(pos) -> tuple[str, DilfGameState | None, str]:
    """Renvoie (status, pre_final_state, msg). status ∈ {OK, FAIL, KING_RAFLE}."""
    fm = pos.final_move
    state = pos.state
    initial_turn = state.turn
    tokens = parse_tokens(pos.published_notation)

    final_from, final_to = fm.from_square, fm.to_square
    final_idx = None
    for i, (kind, frm, to) in enumerate(tokens):
        if frm == final_from and to == final_to and "capture" in kind:
            is_active = (initial_turn == "white" and kind == "capture") or (
                initial_turn == "black" and kind == "reply_capture"
            )
            if is_active:
                final_idx = i
                break

    if final_idx is None:
        return "FAIL", None, f"final_move {final_from}x{final_to} non trouvé dans notation"

    for kind, frm, to in tokens[:final_idx]:
        try:
            if kind == "ad_lib":
                my = state.white_men if state.turn == "white" else state.black_men
                enemy = state.black_men if state.turn == "white" else state.white_men
                forced = None
                for sq in sorted(my):
                    for path, caps in enumerate_pawn_captures(sq, my, enemy):
                        if caps:
                            forced = (sq, path[-1])
                            break
                    if forced:
                        break
                if forced is None:
                    return "FAIL", None, "(ad lib) sans capture forcée disponible"
                m = reconstruct_pawn_capture(state, forced[0], forced[1])
                state = apply_capture(state, m)
            elif kind in ("simple", "reply_simple"):
                assert frm is not None and to is not None
                state = apply_simple(state, frm, to)
            else:
                assert frm is not None and to is not None
                m = reconstruct_pawn_capture(state, frm, to)
                state = apply_capture(state, m)
        except (NoSuchRafleError, AmbiguousRafleError, NotAManError, ValueError) as e:
            return "FAIL", None, f"erreur rejeu {kind} {frm}-{to}: {e}"

    if state.white_kings or state.black_kings:
        return "KING_RAFLE", None, "présence de dame, vérif draught-master non couverte par smoke test pion"

    return "OK", state, ""


def check_final_move_in_engine(state: DilfGameState, fm) -> tuple[bool, str]:
    fen = dilf_state_to_fen(state)
    state_dm = fen_to_board(fen)
    target_key = (tuple(fm.path), frozenset(fm.captures))
    legal = get_legal_moves(state_dm)
    legal_keys = {(tuple(m.path), frozenset(m.captures)) for m in legal}
    if target_key in legal_keys:
        return True, ""
    snippet = ", ".join(
        f"{m.path}/cap={sorted(m.captures)}" for m in legal[:5]
    ) + (f" ... (+{len(legal) - 5})" if len(legal) > 5 else "")
    return False, (
        f"final_move absent des coups légaux draught-master\n"
        f"      attendu : path={list(fm.path)} captures={sorted(fm.captures)}\n"
        f"      légaux  : {snippet}"
    )


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------


def collect_fixtures() -> list[manuel.BeginnerPosition]:
    return [v for v in vars(manuel).values() if isinstance(v, manuel.BeginnerPosition)]


def check_fen_roundtrip(pos) -> tuple[bool, str]:
    fen_dilf = dilf_state_to_fen(pos.state)
    state_dm = fen_to_board(fen_dilf)
    fen_back = board_to_fen(state_dm)
    if fen_dilf != fen_back:
        return False, f"dilf={fen_dilf!r} dm={fen_back!r}"
    return True, ""


def main() -> int:
    fixtures = collect_fixtures()
    n = len(fixtures)
    print(f"Manuel Débutant — {n} fixtures chargées\n")

    # [1] Round-trip FEN
    fen_errors: list[tuple[str, str]] = []
    for pos in fixtures:
        ok, detail = check_fen_roundtrip(pos)
        if not ok:
            fen_errors.append((pos.id, detail))

    print(f"[1] Round-trip FEN dilf ↔ draught-master : {n - len(fen_errors)}/{n}")
    for fid, err in fen_errors[:10]:
        print(f"    ✗ {fid}: {err}")

    # [2] Légalité final_move via le moteur draught-master
    with_fm = [p for p in fixtures if p.final_move is not None]
    fm_ok = 0
    fm_king = 0
    fm_replay_fail = 0
    fm_legality_fail = 0
    failures: list[tuple[str, str]] = []

    for pos in with_fm:
        status, pre_final, msg = replay_until_final(pos)
        if status == "KING_RAFLE":
            fm_king += 1
            continue
        if status == "FAIL":
            fm_replay_fail += 1
            failures.append((pos.id, f"REPLAY: {msg}"))
            continue
        assert pre_final is not None
        ok, detail = check_final_move_in_engine(pre_final, pos.final_move)
        if ok:
            fm_ok += 1
        else:
            fm_legality_fail += 1
            failures.append((pos.id, f"LEGALITY: {detail}"))

    print(
        f"\n[2] final_move légal sous moteur draught-master :"
        f"\n    OK              : {fm_ok}/{len(with_fm)}"
        f"\n    KING_RAFLE      : {fm_king} (rafle de dame, hors scope smoke test)"
        f"\n    Erreur rejeu    : {fm_replay_fail}"
        f"\n    Erreur légalité : {fm_legality_fail}"
        f"\n    Note : 31 fixtures sans final_move (envoi à dame ou gambit) ignorées."
    )
    for fid, err in failures[:10]:
        print(f"    ✗ {fid}:\n      {err}")
    if len(failures) > 10:
        print(f"    ... (+{len(failures) - 10} autres)")

    # [3] Stats
    by_chapter: dict[str, int] = defaultdict(int)
    by_source: Counter[str] = Counter()
    for p in fixtures:
        by_chapter[p.id.split("_")[1]] += 1
        by_source[p.source.value] += 1

    print(f"\n[3] Répartition par chapitre : "
          f"{', '.join(f'{ch}={by_chapter[ch]}' for ch in sorted(by_chapter))}")
    print(f"    Par source : {dict(by_source)}")

    failed = bool(fen_errors) or bool(failures)
    print(f"\n{'=' * 60}")
    if failed:
        print(f"SMOKE TEST FAILED — FEN errors: {len(fen_errors)}, "
              f"final_move errors: {len(failures)}")
        return 1
    print("SMOKE TEST OK — manuel Débutant intégralement consommable "
          "par draught-master.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
