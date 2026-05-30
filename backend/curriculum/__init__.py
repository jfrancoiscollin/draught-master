"""Curriculum layer — the curated pedagogical spine of the learning platform.

`curriculum.json` is hand-authored (levels -> modules -> lessons, with order,
prerequisites and learning goals). It owns no content data: each lesson
declares deterministic `attach` rules that `build_curriculum.py` resolves
against the real material (manuel_debutant exercises, strategy positions and
exercises, knowledge_base tips). `loader.py` is the cached runtime accessor.
"""
