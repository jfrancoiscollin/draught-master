"""Pedagogy package — extends dilf's installed `pedagogy` namespace.

dilf installs a `pedagogy` package in site-packages. Our local
`backend/pedagogy/` would shadow it when `backend/` is on sys.path.
This __init__.py merges both paths so `from pedagogy.types import ...`
resolves to dilf's module while `from pedagogy.storage import ...`
resolves to our local module.
"""
from __future__ import annotations
import pathlib
import sys

# Prepend dilf's installed pedagogy/ to our __path__ so its submodules
# (types, game, motifs, …) are importable under the same `pedagogy` namespace.
_here = pathlib.Path(__file__).parent.resolve()
for _entry in list(sys.path):
    _candidate = pathlib.Path(_entry) / "pedagogy"
    if _candidate.resolve() == _here:
        continue  # skip ourselves
    if (_candidate / "__init__.py").exists():
        __path__.insert(0, str(_candidate))  # type: ignore[name-defined]
        break
