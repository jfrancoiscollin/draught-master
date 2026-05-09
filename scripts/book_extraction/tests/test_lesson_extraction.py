"""
Unit tests for lesson_extraction.py.

Covers: page range collection, text cleaning, and full extraction logic.
No PDF is required — tests use in-memory page lists.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lesson_extraction import _collect_text, _clean_lesson_text, extract_all_lessons
from config import BookConfig, LessonChapter, ChapterExerciseBlock


# ── _collect_text ─────────────────────────────────────────────────────────────

class TestCollectText:
    PAGES = ['page1', 'page2', 'page3', 'page4', 'page5']

    def test_single_page(self):
        result = _collect_text(self.PAGES, start=1, end=2)
        assert result == 'page1'

    def test_multi_page(self):
        result = _collect_text(self.PAGES, start=2, end=5)
        assert 'page2' in result
        assert 'page3' in result
        assert 'page4' in result
        assert 'page5' not in result  # end is exclusive

    def test_start_equals_end(self):
        # Empty range: start >= end means nothing to collect
        result = _collect_text(self.PAGES, start=3, end=3)
        assert result == ''

    def test_end_beyond_pages(self):
        # Should not raise; just stops at last page
        result = _collect_text(self.PAGES, start=4, end=100)
        assert 'page4' in result
        assert 'page5' in result

    def test_one_based_indexing(self):
        # start=1 should return pages[0]
        result = _collect_text(self.PAGES, start=1, end=2)
        assert result == 'page1'


# ── _clean_lesson_text ────────────────────────────────────────────────────────

class TestCleanLessonText:
    def test_removes_pure_page_numbers(self):
        raw = 'Intro text.\n42\nMore text.'
        result = _clean_lesson_text(raw, title='some title')
        assert '42' not in result.split()

    def test_keeps_numbers_in_prose(self):
        raw = 'The pion 36 is important.'
        result = _clean_lesson_text(raw, title='some title')
        assert '36' in result

    def test_removes_duplicate_title(self):
        title = "Chapitre 102 : la notion d'avantage"
        raw = f'{title}\nSome content.'
        result = _clean_lesson_text(raw, title=title)
        assert title not in result

    def test_collapses_excessive_blank_lines(self):
        raw = 'Line 1.\n\n\n\n\nLine 2.'
        result = _clean_lesson_text(raw, title='x')
        assert '\n\n\n' not in result

    def test_empty_input_returns_empty(self):
        assert _clean_lesson_text('', title='x') == ''


# ── extract_all_lessons ───────────────────────────────────────────────────────

def _make_cfg(lesson_chapters, exercise_chapters=None):
    """Build a minimal BookConfig for testing."""
    return BookConfig(
        book_id='test_book',
        title_fr='Test',
        title_en='Test',
        pdf_path='dummy.pdf',
        exercise_id_offset=0,
        chapter_id_offset=0,
        lesson_chapters=lesson_chapters,
        exercise_chapters=exercise_chapters or [],
    )


class TestExtractAllLessons:
    def test_returns_all_chapter_ids(self):
        pages = ['Page A content.', 'Page B content.', 'Page C content.', 'Page D.']
        cfg = _make_cfg([
            LessonChapter(1, 1, 'Chapter 1', 'cat'),
            LessonChapter(2, 3, 'Chapter 2', 'cat'),
        ])
        lessons = extract_all_lessons(pages, cfg)
        assert set(lessons.keys()) == {'1', '2'}

    def test_text_is_collected_up_to_next_chapter(self):
        pages = ['Ch1 content.', 'Ch1 page 2.', 'Ch2 content.', 'Ch2 page 2.']
        cfg = _make_cfg([
            LessonChapter(1, 1, 'Chapter 1', 'cat'),
            LessonChapter(2, 3, 'Chapter 2', 'cat'),
        ])
        lessons = extract_all_lessons(pages, cfg)
        assert 'Ch1 content' in lessons['1']['text']
        assert 'Ch2 content' not in lessons['1']['text']

    def test_text_stops_at_exercise_page(self):
        pages = ['Ch1 content.', 'More ch1.', 'Exercise page.', 'Solutions.', 'Ch2.']
        cfg = _make_cfg(
            lesson_chapters=[
                LessonChapter(10, 1, 'Chapter 10', 'cat'),
                LessonChapter(20, 5, 'Chapter 20', 'cat'),
            ],
            exercise_chapters=[
                ChapterExerciseBlock(ex_page=3, sol_page=4, chapter_id=10,
                                     short_title='CH10', long_title='chapter 10'),
            ],
        )
        lessons = extract_all_lessons(pages, cfg)
        # Lesson text should be pages 1–2 only (exercise page 3 is excluded)
        assert 'Exercise page' not in lessons['10']['text']
        assert 'Ch1 content' in lessons['10']['text']

    def test_title_and_category_set(self):
        pages = ['Content.']
        cfg = _make_cfg([LessonChapter(5, 1, 'My Title', 'my_cat')])
        lessons = extract_all_lessons(pages, cfg)
        assert lessons['5']['title'] == 'My Title'
        assert lessons['5']['category'] == 'my_cat'

    def test_empty_page_list_produces_empty_text(self):
        cfg = _make_cfg([LessonChapter(1, 1, 'Ch', 'cat')])
        lessons = extract_all_lessons([], cfg)
        assert lessons['1']['text'] == ''
