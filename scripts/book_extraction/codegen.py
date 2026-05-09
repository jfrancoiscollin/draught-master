"""
Code generation: write extracted data to backend files.

  - exercises  → backend/db/{book_id}_exercises.py
  - lessons    → backend/{book_id}_lessons.json
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List

from config import BookConfig


def write_exercises_py(
    exercises: List[Dict[str, Any]],
    cfg: BookConfig,
    project_root: str = '.',
) -> str:
    """
    Write exercises to backend/db/{book_id}_exercises.py.
    Returns the path written.
    """
    out_path = cfg.output_exercises_py or os.path.join(
        project_root, 'backend', 'db', f'{cfg.book_id}_exercises.py'
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    varname = cfg.exercises_varname()
    chapter_list = sorted({ex['category'] for ex in exercises})

    lines = [
        'from __future__ import annotations',
        '',
        f'# Auto-extracted from {os.path.basename(cfg.pdf_path)}',
        f'# Book ID : {cfg.book_id}',
        f'# Exercise IDs : {cfg.exercise_id_offset + 1} – {cfg.exercise_id_offset + len(exercises)}',
        f'# Chapter ID offset : +{cfg.chapter_id_offset} (avoids collision with other books)',
        '#',
        '# Chapters:',
    ]
    for ex_ch in cfg.exercise_chapters:
        lines.append(f'#   {ex_ch.chapter_id} – {ex_ch.long_title}')
    lines += ['', f'{varname} = [']

    for ex in exercises:
        lines.append('    {')
        lines.append(f'        "name": {json.dumps(ex["name"], ensure_ascii=False)},')
        lines.append(f'        "description": {json.dumps(ex["description"], ensure_ascii=False)},')
        lines.append(f'        "initial_fen": {json.dumps(ex["initial_fen"])},')
        lines.append(f'        "solution_moves": {json.dumps(ex["solution_moves"])},')
        lines.append(f'        "difficulty": {ex["difficulty"]},')
        lines.append(f'        "category": {json.dumps(ex["category"])},')
        lines.append(f'        "hint": {json.dumps(ex.get("hint", ""), ensure_ascii=False)},')
        lines.append('    },')

    lines += [']', '']
    content = '\n'.join(lines)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'Wrote {len(exercises)} exercises → {out_path}')
    return out_path


def write_lessons_json(
    lessons: Dict[str, Any],
    cfg: BookConfig,
    project_root: str = '.',
) -> str:
    """
    Write lessons to backend/{book_id}_lessons.json.
    Returns the path written.
    """
    out_path = cfg.output_lessons_json or os.path.join(
        project_root, 'backend', f'{cfg.book_id}_lessons.json'
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)

    print(f'Wrote {len(lessons)} lesson chapters → {out_path}')
    return out_path


def print_integration_checklist(cfg: BookConfig, n_exercises: int, n_lessons: int) -> None:
    """Print the manual integration steps that remain after code generation."""
    varname = cfg.exercises_varname()
    ex_file = f'backend/db/{cfg.book_id}_exercises.py'
    lesson_file = f'backend/{cfg.book_id}_lessons.json'
    id_start = cfg.exercise_id_offset + 1
    id_end = cfg.exercise_id_offset + n_exercises

    print(f"""
{"═"*60}
POST-EXTRACTION INTEGRATION CHECKLIST
{"═"*60}

Files generated:
  ✓ {ex_file}  ({n_exercises} exercises, IDs {id_start}–{id_end})
  ✓ {lesson_file}  ({n_lessons} chapters)

─── 1. backend/database.py ────────────────────────────────
  a) Add import near top:
       from db.{cfg.book_id}_exercises import {varname}
       _OFFSET_{cfg.book_id.upper()} = {cfg.exercise_id_offset}

  b) In init_db(), add upsert loop after combinaisons:
       for idx, ex in enumerate({varname}, start=_OFFSET_{cfg.book_id.upper()} + 1):
           await db.execute(INSERT ... book_id='{cfg.book_id}' ...)

─── 2. backend/main.py ─────────────────────────────────────
  a) In _lessons_path_for_book(), add:
       if book == '{cfg.book_id}':
           return os.path.join(dirname, '{cfg.book_id}_lessons.json')

  b) In get_lesson(), update chapter routing:
       book = '{cfg.book_id}' if chapter >= {cfg.chapter_id_offset + 1} else ...

─── 3. frontend/src/components/ExerciseLibraryPage.tsx ─────
  Find the BOOKS array entry for '{cfg.book_id}' and set:
       hasExercises: true

─── 4. Commit & push ────────────────────────────────────────
  git add backend/db/{cfg.book_id}_exercises.py \\
          backend/{cfg.book_id}_lessons.json \\
          backend/database.py backend/main.py \\
          frontend/src/components/ExerciseLibraryPage.tsx
  git commit -m "feat: add {cfg.title_fr} exercises and lessons"
  git push -u origin <branch>
{"═"*60}
""")
