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
 │       ├─ extract_lessons.py    → backend/<book_id>_lessons.json
 │       └─ extract_exercises.py  → backend/db/<book_id>_exercises.py
 │
 ├─[3] Validate             → validation report printed automatically
 │       └─ fix config if boards/solutions wrong, re-run
 │
 ├─[4] Integrate backend    → database.py + main.py
 │
 └─[5] Integrate frontend   → ExerciseLibraryPage.tsx
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
| `board_style` | `'border_lines'` (gray/white) or `'dark_squares'` (classic dark/light) |
| `exercise_chapters` | List of `ChapterExerciseBlock` — one per chapter with exercises |
| `lesson_chapters` | List of `LessonChapter` — one per chapter with theory text |

### Finding PDF Page Numbers

```bash
# Open the PDF and note:
# - The page number of each chapter's first text page
# - The page number of the exercise diagrams page
# - The page number of the solutions page

# Quick check: dump all page texts and grep for chapter headings
pdftotext docs/livres/.../book.pdf - | grep -n "Chapitre\|SOLUTIONS\|Exercices"
```

### ID Allocation Strategy

```
Book                    chapter_id_offset  exercise_id_offset
dubois_combinaisons     0                  0      (IDs 1–408)
dubois_sens_du_jeu      100                500    (IDs 501–572)
next book               200                600    (IDs 601–…)
next book               300                700    (IDs 701–…)
```

Always leave a gap of ~100 IDs between books so room for future exercises.

---

## Step 2 — Run the Extraction

```bash
# Full extraction (lessons + exercises):
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --verbose

# Exercises only:
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --exercises-only --verbose

# Lessons only:
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --lessons-only

# Dry run (validate but don't write files):
python scripts/book_extraction/run_extraction.py \
    scripts/book_extraction/configs/<book_id>.py --dry-run --verbose
```

---

## Step 3 — Validate and Fix

The extraction script prints a validation report automatically.

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
# Quick visual check — run this in Python:
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

#### ❌ Empty solutions (`sol=[]`)

**Cause A:** D1 has no newline before it (should be fixed by `\n` prepend in solution_parsing.py).

**Cause B:** Solution page layout is different from the standard.  Dump the raw text:
```python
pages = extract_text_pages('docs/livres/.../book.pdf', cwd='.')
print(repr(pages[sol_page - 1][:600]))
```
Then adjust `solution_split_pattern` in the config or fix `extract_moves()` in `solution_parsing.py`.

**Cause C:** Multi-page solutions (`sol_page_end`).  If solutions overflow to the next page:
```python
ChapterExerciseBlock(77, 79, 115, ..., sol_page_end=80)
                         ^                             ^
                    sol_page starts                  sol_page ends
```

#### ❌ Pieces detected in wrong squares

**Cause:** Thresholds don't match this book's scan.  Sample a few squares manually:
```python
gray = render_page_gray('docs/livres/.../book.pdf', page=12)
# Print pixel values for a range of squares:
# manually inspect gray[row_center-5:row_center+5, col_center-5:col_center+5].mean()
```
Then adjust `white_piece_threshold` and `black_piece_threshold`.

#### ❌ Spurious moves in solution (e.g. `'16-22-26'`, `'37-38-42-47'`)

These are position-sequence notations from the explanatory text, not moves.  The validation report flags them as "Suspicious move".  They are automatically rejected by `_is_valid_move()` (only `A-B` and `AxBxC` forms accepted).  No fix needed — just verify the real solution moves are present.

#### ❌ Duplicate FEN detected

Two diagrams got identical FEN.  Usually means board detection picked up the same board twice.  Fix: tighten `min_border_run` or `expected_board_px` to reduce false positives.

---

## Step 4 — Integrate Backend

After files are generated, the script prints a checklist.  The changes are:

### `backend/database.py`

```python
# 1. Import at top of file (after existing imports):
from db.<book_id>_exercises import <BOOK_ID>_EXERCISES
_OFFSET_<BOOK_ID> = <exercise_id_offset>

# 2. In init_db(), add migration for book_id column (already exists for sens_du_jeu):
"ALTER TABLE exercises ADD COLUMN book_id TEXT DEFAULT 'dubois_combinaisons'"

# 3. In init_db(), add upsert loop after sens_du_jeu upsert:
for idx, ex in enumerate(<BOOK_ID>_EXERCISES, start=_OFFSET_<BOOK_ID> + 1):
    await db.execute(
        "INSERT INTO exercises (..., book_id) VALUES (?, ..., '<book_id>')
         ON CONFLICT(id) DO UPDATE SET ..., book_id='<book_id>'",
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
# Chapters >= (chapter_id_offset + 1) belong to this book.
# Add an elif clause:
elif chapter >= <chapter_id_offset + 1> and chapter < <next_book_offset>:
    book = '<book_id>'
```

---

## Step 5 — Integrate Frontend

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

## Step 6 — Commit and Push

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
| `board_detection.py` | `find_boards()` — dispatches to `border_lines` or `dark_squares` |
| `fen_extraction.py` | `analyze_board_fen()`, `validate_fen()` |
| `solution_parsing.py` | `parse_solution_page()`, `extract_moves()`, `get_turn_from_page()` |
| `lesson_extraction.py` | `extract_all_lessons()` |
| `exercise_extraction.py` | `extract_all_exercises()` — main pipeline |
| `validation.py` | `print_validation_report()`, `validate_lessons()` |
| `codegen.py` | `write_exercises_py()`, `write_lessons_json()`, `print_integration_checklist()` |
| `run_extraction.py` | CLI entry point |
| `configs/` | Per-book configuration files |

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

| Book | Board style | Key issue | Fix |
|---|---|---|---|
| Apprendre les combinaisons | dark/light | — | dark_squares strategy |
| Apprendre le sens du jeu | gray/white | Gray squares invisible to dark-pixel detector | border_lines strategy on border runs |
| Apprendre le sens du jeu | gray/white | D1 solutions missing | Prepend `\n` before `re.split` on solution page |
| Apprendre le sens du jeu | gray/white | Analysis text leaked into solutions | `_is_valid_move` rejects `A-B-C` multi-step notation |
| Apprendre le sens du jeu | gray/white | Bracketed comments `[plus fort que 34-30]` | `re.sub(r'\[[\s\S]*?\]', '', ...)` with DOTALL |

Add new rows here as you encounter issues with future books.
