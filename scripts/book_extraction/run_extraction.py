"""
Main entry point for book extraction.

Usage:
  python scripts/book_extraction/run_extraction.py <config_module> [options]

Examples:
  # Extract a new book (lessons + exercises):
  python scripts/book_extraction/run_extraction.py \\
      scripts/book_extraction/configs/dubois_sens_du_jeu.py

  # Exercises only (lessons already done):
  python scripts/book_extraction/run_extraction.py \\
      scripts/book_extraction/configs/dubois_sens_du_jeu.py --exercises-only

  # Lessons only:
  python scripts/book_extraction/run_extraction.py \\
      scripts/book_extraction/configs/dubois_sens_du_jeu.py --lessons-only

  # Validate without writing files (dry run):
  python scripts/book_extraction/run_extraction.py \\
      scripts/book_extraction/configs/dubois_sens_du_jeu.py --dry-run

  # Audit chapter page numbers — print first line of each configured start page
  # so you can verify they all point to chapter headings:
  python scripts/book_extraction/run_extraction.py \\
      scripts/book_extraction/configs/dubois_sens_du_jeu.py --audit-pages

  # Verbose output (shows board counts, solution details):
  python scripts/book_extraction/run_extraction.py \\
      scripts/book_extraction/configs/dubois_sens_du_jeu.py --verbose
"""
from __future__ import annotations
import argparse
import importlib.util
import os
import sys

# Ensure project root is on sys.path
_here = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_here, '..', '..'))
sys.path.insert(0, _project_root)
sys.path.insert(0, _here)


def load_config(config_path: str):
    """Load a BookConfig instance from a .py config file."""
    spec = importlib.util.spec_from_file_location('book_config', config_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    if not hasattr(mod, 'CONFIG'):
        raise AttributeError(f'{config_path} must define a module-level CONFIG = BookConfig(...)')
    return mod.CONFIG


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Extract lessons and exercises from a draughts book PDF.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('config', help='Path to a book config .py file')
    parser.add_argument('--exercises-only', action='store_true')
    parser.add_argument('--lessons-only', action='store_true')
    parser.add_argument('--dry-run', action='store_true',
                        help='Extract and validate but do not write files')
    parser.add_argument('--audit-pages', action='store_true',
                        help='Print the first line of each configured lesson chapter start '
                             'page so you can verify all page numbers are correct')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--check-legality', action='store_true',
                        help='After extraction, run full game-engine legality check on '
                             'every first move (requires backend/ on sys.path)')
    parser.add_argument('--fix-illegal', action='store_true',
                        help='Automatically correct illegal first moves using heuristics '
                             '(implies --check-legality; writes corrected file)')
    args = parser.parse_args()

    cfg = load_config(args.config)
    print(f'\nBook: {cfg.title_fr}  ({cfg.book_id})')
    print(f'PDF : {cfg.pdf_path}')

    # Import here so numpy/PIL errors are clear if not installed
    from exercise_extraction import extract_all_exercises
    from lesson_extraction import extract_all_lessons
    from pdf_utils import extract_text_pages
    from validation import (
        print_validation_report, validate_lessons, print_lesson_report,
        print_config_report, print_legality_report, fix_illegal_first_moves,
    )
    from codegen import write_exercises_py, write_lessons_json, print_integration_checklist

    exercises = []
    lessons = {}

    # ── Config validation (always runs) ──────────────────────────────────────
    config_ok = print_config_report(cfg)
    if not config_ok and not args.dry_run:
        print('WARNING: config issues found — continuing anyway, but fix before committing.\n')

    # ── Page audit (standalone mode) ─────────────────────────────────────────
    if args.audit_pages:
        if not cfg.lesson_chapters:
            print('No lesson chapters in config.')
            return
        pages = extract_text_pages(cfg.pdf_path, cwd=_project_root)
        print(f'\n{"─"*70}')
        print(f'PAGE AUDIT — first line of each configured lesson chapter start page')
        print(f'{"─"*70}')
        print(f'{"Ch ID":>6}  {"Page":>5}  {"First line on that page"}')
        print(f'{"─"*6}  {"─"*5}  {"─"*55}')
        for lc in sorted(cfg.lesson_chapters, key=lambda c: c.page):
            idx = lc.page - 1
            if 0 <= idx < len(pages):
                first = next((l.strip() for l in pages[idx].split('\n') if l.strip()), '(empty page)')
            else:
                first = f'(page {lc.page} out of range, PDF has {len(pages)} pages)'
            ok = '✓' if first.lower().startswith('chapitre') else '?'
            print(f'{lc.chapter_id:>6}  {lc.page:>5}  {ok}  {first[:60]}')
        print(f'{"─"*70}')
        print('  ✓ = first line looks like a chapter heading')
        print('  ? = first line does not start with "Chapitre" — verify manually\n')
        return

    # ── Exercises ────────────────────────────────────────────────────────────
    if not args.lessons_only:
        print('\n[1/2] Extracting exercises…')
        exercises = extract_all_exercises(cfg, cwd=_project_root, verbose=args.verbose)
        ok = print_validation_report(exercises)
        if not ok and not args.dry_run:
            print('WARNING: validation issues found — files will still be written.')

        # Engine-based legality check (full move generation)
        if args.check_legality or args.fix_illegal:
            print_legality_report(exercises, backend_path=os.path.join(_project_root, 'backend'))

        # Auto-fix illegal first moves
        if args.fix_illegal:
            exercises, corrections = fix_illegal_first_moves(
                exercises,
                backend_path=os.path.join(_project_root, 'backend'),
            )
            fixed = [c for c in corrections if c['fix']]
            uncertain = [c for c in corrections if not c['fix']]
            print(f'  Auto-fix: {len(fixed)} corrigés, {len(uncertain)} incertains')
            for c in uncertain:
                print(f'    [UNCERTAIN] {c["name"]}: {c["stored"]!r}')
            if fixed:
                print()

        if not args.dry_run:
            write_exercises_py(exercises, cfg, project_root=_project_root)

    # ── Lessons ──────────────────────────────────────────────────────────────
    if not args.exercises_only:
        if cfg.lesson_chapters:
            print('\n[2/2] Extracting lessons…')
            pages = extract_text_pages(cfg.pdf_path, cwd=_project_root)
            lessons = extract_all_lessons(pages, cfg)
            print_lesson_report(lessons)
            if not args.dry_run:
                write_lessons_json(lessons, cfg, project_root=_project_root)
        else:
            print('\n[2/2] No lesson chapters defined in config — skipping.')

    # ── Summary ──────────────────────────────────────────────────────────────
    if not args.dry_run:
        print_integration_checklist(cfg, len(exercises), len(lessons))


if __name__ == '__main__':
    main()
