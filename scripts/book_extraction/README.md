# Book Extraction Workflow

Complete guide for extracting lessons and exercises from a Dubois draughts book PDF and integrating them into the app.

---

## Quick Start

```bash
# From project root
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/dubois_sens_du_jeu.py --verbose
```

---

## Overview

```
PDF
 │
 ├─[1] Create config        → scripts/book_extraction/configs/<book_id>.py
 │
 ├─[2] Run extraction       → python run_extraction.py configs/<book_id>.py
 │       ├─ lesson_extraction.py   → backend/<book_id>_lessons.json
 │       │       └─ text + illustrative board diagrams ({fen, label}[])
 │       └─ exercise_extraction.py → backend/db/<book_id>_exercises.py
 │
 ├─[3] Validate             → validation report printed automatically
 │       ├─ --check-legality : engine-based move legality check
 │       ├─ --fix-illegal    : auto-correct illegal first moves
 │       └─ fix config if boards/solutions wrong, re-run
 │
 ├─[4] Verify with Scan     → admin panel in app (Settings → Vérification)
 │       └─ run --lessons-only after correcting to refresh diagrams
 │
 ├─[5] Integrate backend    → database.py + main.py
 │
 └─[6] Integrate frontend   → ExerciseLibraryPage.tsx
```

---

## Step 1 — Create a Book Config

Copy the most similar existing config and adapt it:

```bash
cp scripts/book_extraction/configs/dubois_sens_du_jeu.py \
   scripts/book_extraction/configs/<new_book_id>.py
```

Edit the new file and fill in:

| Field | Description |
|---|---|
| `book_id` | Unique key, snake_case. Must match the `BOOKS` entry in `ExerciseLibraryPage.tsx` |
| `pdf_path` | Relative to project root |
| `exercise_id_offset` | Choose a range that doesn't collide: see **ID Allocation** below |
| `chapter_id_offset` | 0 for book 1, 100 for book 2, 200 for book 3… |
| `board_style` | `'border_lines'` (gray/white boards) or `'dark_squares'` (classic dark/light boards) |
| `exercise_chapters` | List of `ChapterExerciseBlock` — one per chapter with exercises |
| `lesson_chapters` | List of `LessonChapter` — one per chapter with theory text |

### Finding PDF Page Numbers

```bash
# Dump all page texts and grep for chapter headings
pdftotext docs/livres/.../book.pdf - | grep -n "Chapitre\|SOLUTIONS\|Exercices"

# Or use the audit mode to verify all configured page numbers at once:
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --audit-pages
```

### ID Allocation Strategy

```
Book                    chapter_id_offset  exercise_id_offset
dubois_combinaisons     0                  0      (IDs 1–408)
dubois_sens_du_jeu      100                500    (IDs 501–572)
next book               200                600    (IDs 601–…)
next book               300                700    (IDs 701–…)
```

Always leave a gap of ~100 IDs between books to allow future exercises.

---

## Step 2 — Run the Extraction

```bash
# Full extraction (lessons + exercises):
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --verbose

# Exercises only:
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --exercises-only --verbose

# Lessons only (re-runs diagram extraction too):
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --lessons-only

# Dry run (validate but don't write files):
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --dry-run --verbose

# Legality check after extraction:
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --check-legality

# Auto-fix illegal first moves (heuristic corrector):
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --fix-illegal
```

### What the extraction produces

**`backend/<book_id>_lessons.json`** — one entry per chapter:
```json
{
  "101": {
    "title": "Chapitre 1 : la notion d'espace",
    "text": "...",
    "category": "generalites",
    "diagrams": [
      {"fen": "W:W24,29,33:B6,11,17", "label": "Camp des Noirs"},
      {"fen": "W:W27,31,32:B6,8,13",  "label": "Zone frontière"}
    ]
  }
}
```

The `diagrams` field is populated automatically by scanning each lesson page for board images and extracting both the FEN and the caption label (see *Lesson Diagram Extraction* below).

**`backend/db/<book_id>_exercises.py`** — Python list of exercise dicts:
```python
EXERCISES = [
  {
    'name': 'LES COMBINAISONS EN 2 TEMPS – D1',
    'description': '...',
    'initial_fen': 'W:W25,30,31:B18,22,23',
    'solution_moves': ['30-24', '19x30', '35x24'],
    'difficulty': 1,
    'category': 'combinaisons_2',
    'heuristic_fix': False,  # True if first move was auto-corrected
  },
  ...
]
```

---

## Step 3 — Validate and Fix

The extraction script prints a validation report automatically. Two levels of checking are available:

### Level 1 — Structural validation (always runs)

Checks FEN format, solution presence, suspicious move notation, duplicate FENs, missing fields.

### Level 2 — Engine-based legality check (`--check-legality`)

Uses the game engine (`backend/game_engine.py`) to verify that every stored first move is actually legal in the given position.

```bash
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --check-legality
```

### Level 3 — Auto-fix illegal moves (`--fix-illegal`)

Applies heuristics to correct illegal first moves before writing the output file. Three strategies are tried in order:

1. **Reversal** — `27-32` stored but legal is `32-27` (OCR transposition)
2. **Off-by-one source** — closest occupied square to the stored source
3. **Single legal move** — when only one legal move exists from the occupied source

```bash
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --fix-illegal
```

Auto-corrected exercises get `heuristic_fix=True` in the output. **These must be verified against the physical book** before the flag is removed.

### Common Issues and Fixes

#### ❌ Wrong number of boards detected

```
WARNING: Chapter 108: expected 4 boards, got 2
```

**Cause:** Board detection parameters don't match this book's board style.

**Fix:**
```python
# In your config, try adjusting:
expected_board_px=480,   # measured from a known-good page render
min_border_run=350,      # lower if borders are thinner
```

**Debugging:**
```python
from scripts.book_extraction.pdf_utils import render_page_gray
from scripts.book_extraction.board_detection import find_boards
import matplotlib.pyplot as plt

gray = render_page_gray('docs/livres/.../book.pdf', page=12, cwd='.')
boards = find_boards(gray, style='border_lines', expected_board_px=505)
plt.imshow(gray, cmap='gray')
for (x1,y1,x2,y2) in boards:
    plt.plot([x1,x2,x2,x1,x1],[y1,y1,y2,y2,y1],'r-',lw=2)
plt.show()
print(f'{len(boards)} boards found')
```

> **Note on lesson diagrams:** Illustrative boards in lesson pages are often
> smaller (~440 px) than exercise boards (~505 px). The extractor automatically
> retries with `expected_px=440` and `expected_px=380` when the standard
> parameters find nothing. If that still fails, inspect the page with the
> debug snippet above and adjust `min_border_run`.

#### ❌ Empty solutions (`sol=[]`)

**Cause A:** D1 has no newline before it — fixed by the `\n` prepend in `solution_parsing.py`.

**Cause B:** Solution page layout is different from the standard. Dump the raw text:
```python
pages = extract_text_pages('docs/livres/.../book.pdf', cwd='.')
print(repr(pages[sol_page - 1][:600]))
```
Then adjust `solution_split_pattern` in the config or fix `extract_moves()` in `solution_parsing.py`.

**Cause C:** Multi-page solutions (`sol_page_end`). If solutions overflow to the next page:
```python
ChapterExerciseBlock(77, 79, 115, ..., sol_page_end=80)
```

#### ❌ Pieces detected in wrong squares

**Cause:** Thresholds don't match this book's scan quality. Sample a few squares manually:
```python
gray = render_page_gray('docs/livres/.../book.pdf', page=12)
# Inspect pixel values around a known square center
print(gray[row_center-5:row_center+5, col_center-5:col_center+5].mean())
```
Then adjust `white_piece_threshold` and `black_piece_threshold` in the config.

#### ❌ Spurious moves in solution (e.g. `'16-22-26'`)

These are position-sequence notations from explanatory text. The validation report flags them as "Suspicious move". They are automatically rejected by `_is_valid_move()`. No fix needed — just verify the real solution moves are present.

#### ❌ Duplicate FEN detected

Two diagrams got identical FEN. Usually means board detection picked up the same board twice. Fix: tighten `min_border_run` or `expected_board_px` to reduce false positives.

#### ❌ Illegal first moves after extraction

Run `--fix-illegal` to apply heuristic corrections. Then use the in-app verification tool (Settings → Vérification des exercices, with Scan enabled) to cross-check remaining `heuristic_fix=True` exercises against the book.

---

## Lesson Diagram Extraction

Lesson pages often contain illustrative board positions (structural examples, game fragments) that the extraction pipeline now detects automatically.

### How it works

For each lesson chapter, `lesson_extraction.py`:
1. Renders every page in the chapter's range to a grayscale image
2. Runs `find_boards()` on the image (same algorithm as exercises)
3. Falls back to smaller expected sizes (440 px, 380 px) if nothing is found — handles the small 3-column illustrative grids common in Dubois books
4. Extracts a FEN for each detected board
5. Infers the caption label from `pdftotext -layout` output:
   - **Multi-column lines** (labels separated by 4+ spaces) are the primary signal — a line like `L'enchaînement latéral     L'enchaînement en tenaille` maps directly to the row of boards above it
   - **Single-column short phrases** are used as fallback for single-board pages
   - Labels ending with `.` `,` `?` `:` are rejected (sentence fragments / headings)
   - URL fragments (`=`, `&`), pure move sequences, and chapter titles (` : ` pattern) are also rejected
   - Falls back to `Diag. N` when no label can be inferred

### Diagram data format

The `diagrams` field in `lessons.json` uses `{fen, label}` objects:

```json
"diagrams": [
  {"fen": "W:W...", "label": "L'enchaînement latéral"},
  {"fen": "W:W...", "label": "Le pion arrière"}
]
```

The frontend (`LessonPanel.tsx`) supports both this format and the legacy `string[]` format (backward-compatible).

### Triggering a diagram re-extraction

If you edit the lesson pages config or the PDF, re-run lessons only:

```bash
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --lessons-only
```

---

## Step 4 — Verify with Scan (optional but recommended)

After extraction, use the in-app exercise verification tool to cross-check solutions against the Scan engine:

1. Deploy the generated files to the server
2. Open Settings → Vérification des exercices
3. Select the dataset (All / Base / Sens du Jeu)
4. Enable **+ Scan** and click **Lancer la vérification**
5. Copy the report with **Copier le rapport complet**
6. Investigate mismatches:
   - `[SCAN_MISMATCH]` — Scan suggests a different move; check the book
   - `[HEURISTIQUE]` — auto-corrected first move; must be verified against the book
   - `[ILLEGAL]` — move is not legal in the position; re-run `--fix-illegal`

---

## Step 5 — Integrate Backend

After files are generated, the script prints a checklist. The changes are:

### `backend/database.py`

```python
# 1. Import at top of file:
from db.<book_id>_exercises import <BOOK_ID>_EXERCISES
_OFFSET_<BOOK_ID> = <exercise_id_offset>

# 2. In init_db(), add upsert loop:
for idx, ex in enumerate(<BOOK_ID>_EXERCISES, start=_OFFSET_<BOOK_ID> + 1):
    await db.execute(
        "INSERT INTO exercises (..., book_id) VALUES (?, ..., '<book_id>')"
        " ON CONFLICT(id) DO UPDATE SET ...",
        (idx, ex['name'], ...)
    )
await db.commit()
```

### `backend/main.py`

```python
# In _lessons_path_for_book():
if book == '<book_id>':
    return os.path.join(dirname, '<book_id>_lessons.json')

# In get_lesson(), update chapter routing:
elif chapter >= <chapter_id_offset + 1>:
    book = '<book_id>'
```

---

## Step 6 — Integrate Frontend

### `frontend/src/components/ExerciseLibraryPage.tsx`

Find the BOOKS array entry for the new book and set `hasExercises: true`.

If the book isn't in BOOKS yet, add it:

```typescript
{
  id: '<book_id>',
  title: '<title_fr>',
  titleEn: '<title_en>',
  author: 'J-P. Dubois',
  category: 'apprentissage',   // or 'perfectionnement' or 'reference'
  emoji: '📘',
  hasExercises: true,
},
```

---

## Step 7 — Commit and Push

```bash
git add \
  backend/db/<book_id>_exercises.py \
  backend/<book_id>_lessons.json \
  backend/database.py \
  backend/main.py \
  frontend/src/components/ExerciseLibraryPage.tsx \
  scripts/book_extraction/configs/<book_id>.py

git commit -m "feat: add '<title_fr>' exercises and lessons"
git push -u origin <branch>
```

---

## Module Reference

| File | Purpose |
|---|---|
| `config.py` | `BookConfig`, `ChapterExerciseBlock`, `LessonChapter` dataclasses |
| `pdf_utils.py` | `extract_text_pages()`, `render_page_gray()` |
| `board_detection.py` | `find_boards()` — dispatches to `border_lines` or `dark_squares`; `find_boards_border_lines()` for direct parameter control |
| `fen_extraction.py` | `analyze_board_fen()`, `validate_fen()` |
| `solution_parsing.py` | `parse_solution_page()`, `extract_moves()`, `get_turn_from_page()` |
| `lesson_extraction.py` | `extract_all_lessons()` — text + diagram extraction; `_extract_lesson_diagrams()`, `_extract_labels_from_page()` |
| `exercise_extraction.py` | `extract_all_exercises()` — main exercise pipeline |
| `validation.py` | `print_validation_report()`, `validate_lessons()`, `validate_exercises_with_engine()`, `fix_illegal_first_moves()` |
| `codegen.py` | `write_exercises_py()`, `write_lessons_json()`, `print_integration_checklist()` |
| `run_extraction.py` | CLI entry point — `--verbose`, `--dry-run`, `--audit-pages`, `--check-legality`, `--fix-illegal`, `--lessons-only`, `--exercises-only` |
| `configs/` | Per-book configuration files |
| `tests/` | Unit tests — run with `pytest scripts/book_extraction/tests/` |

---

## Tests

```bash
# Run all extraction tests:
pytest scripts/book_extraction/tests/ -v

# Run only legality/engine tests (requires backend/game_engine.py):
pytest scripts/book_extraction/tests/test_legality_check.py -v
```

Tests cover: FEN validation, move validation, exercise validation, lesson validation, config validation, engine-based legality, heuristic fixer.

---

## Dependencies

```bash
# System (apt / brew):
apt-get install poppler-utils   # provides pdftotext, pdftoppm

# Python:
pip install numpy pillow
# Optional for visual debugging:
pip install matplotlib
```

---

## Lessons Learned

| Book | Board style | Issue | Fix |
|---|---|---|---|
| Apprendre les combinaisons | dark/light | — | `dark_squares` strategy |
| Apprendre le sens du jeu | gray/white | Gray squares invisible to dark-pixel detector | `border_lines` strategy on border runs |
| Apprendre le sens du jeu | gray/white | D1 solutions missing | Prepend `\n` before `re.split` on solution page |
| Apprendre le sens du jeu | gray/white | Analysis text leaked into solutions | `_is_valid_move` rejects `A-B-C` multi-step notation |
| Apprendre le sens du jeu | gray/white | Bracketed comments in solutions | `re.sub(r'\[[\s\S]*?\]', '', ...)` with DOTALL |
| Apprendre le sens du jeu | gray/white | 50 illegal first moves (OCR errors) | `--fix-illegal` heuristic + Scan verification |
| Apprendre le sens du jeu | gray/white | Illustrative lesson boards not detected | Fallback to `expected_px=440/380` in `_extract_lesson_diagrams()` |
| Apprendre le sens du jeu | gray/white | Lesson diagram labels were sentence fragments | Filter `.` `,` `?` endings, URL patterns, move sequences in `_is_label()` |

Add new rows here as you encounter issues with future books.
