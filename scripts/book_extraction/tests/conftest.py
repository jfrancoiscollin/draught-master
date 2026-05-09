"""Shared pytest configuration: add the parent package to sys.path."""
import sys
import os

# Make 'scripts/book_extraction' importable as a flat package
_here = os.path.dirname(os.path.abspath(__file__))
_pkg = os.path.dirname(_here)
if _pkg not in sys.path:
    sys.path.insert(0, _pkg)
