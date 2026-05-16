"""Regression tests for backend.lidraughts_fetcher.split_pdn_games.

The previous implementation split on every ``[Tag "..."]`` occurrence,
shredding every PDN game into one fragment per tag line. These tests
encode the post-fix expectations: each lidraughts-style game must round
trip as a single string, regardless of formatting quirks.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lidraughts_fetcher import split_pdn_games


_SAMPLE_TWO_GAMES = """\
[Event "Lidraughts game"]
[Site "https://lidraughts.org/abc12345"]
[White "alice"]
[Black "bob"]
[Result "1-0"]

1. 32-28 19-23 *

[Event "Lidraughts game"]
[Site "https://lidraughts.org/zzz99999"]
[White "carol"]
[Black "alice"]
[Result "0-1"]

1. 33-29 20-24 *
"""


def test_split_returns_empty_for_empty_input() -> None:
    assert split_pdn_games("") == []
    assert split_pdn_games("   \n  \n") == []


def test_split_returns_one_for_single_game() -> None:
    pdn = (
        '[Event "Lidraughts game"]\n'
        '[White "alice"]\n'
        '[Black "bob"]\n'
        '[Result "1-0"]\n\n'
        '1. 32-28 19-23 *\n'
    )
    games = split_pdn_games(pdn)
    assert len(games) == 1
    assert games[0].startswith('[Event "Lidraughts game"]')
    assert "32-28" in games[0]
    assert "19-23" in games[0]


def test_split_returns_two_for_two_back_to_back_games() -> None:
    games = split_pdn_games(_SAMPLE_TWO_GAMES)
    assert len(games) == 2
    assert '[Site "https://lidraughts.org/abc12345"]' in games[0]
    assert '[Site "https://lidraughts.org/zzz99999"]' in games[1]
    # Each chunk keeps its full tag block + moves together.
    assert games[0].count("[White") == 1
    assert games[1].count("[White") == 1


def test_split_handles_consecutive_tag_lines_inside_a_game() -> None:
    """The old impl broke 5 consecutive tag lines into 5 'games'."""
    pdn = (
        '[Event "X"]\n[Site "Y"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n\n'
        '1. 32-28 *\n'
    )
    assert len(split_pdn_games(pdn)) == 1


def test_split_skips_pre_first_tag_garbage() -> None:
    pdn = "; some PDN header comment\nrandom text\n" + _SAMPLE_TWO_GAMES
    assert len(split_pdn_games(pdn)) == 2


def test_split_handles_games_without_trailing_blank_line() -> None:
    """A real lidraughts dump occasionally concatenates the next [Event]
    immediately after the previous result with no separating blank line."""
    pdn = (
        '[Event "G1"]\n[Result "1-0"]\n\n1. 32-28 *\n'
        '[Event "G2"]\n[Result "0-1"]\n\n1. 33-29 *\n'
    )
    games = split_pdn_games(pdn)
    assert len(games) == 2
    assert '[Event "G1"]' in games[0]
    assert '[Event "G2"]' in games[1]


def test_split_preserves_movetext_with_internal_blank_lines() -> None:
    """A blank line within movetext should not split a single game in two."""
    pdn = (
        '[Event "X"]\n[Result "*"]\n\n'
        '1. 32-28 19-23\n'
        '\n'
        '2. 33-29 20-24 *\n'
    )
    games = split_pdn_games(pdn)
    assert len(games) == 1
    assert "32-28" in games[0]
    assert "33-29" in games[0]


def test_split_strips_surrounding_whitespace_per_game() -> None:
    games = split_pdn_games(_SAMPLE_TWO_GAMES)
    for g in games:
        assert g == g.strip()
        assert not g.startswith("\n")
        assert not g.endswith("\n")
