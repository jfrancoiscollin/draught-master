"""
Unit tests for text_correction.py.

Covers:
  - Generic PDF artifact cleanup (stray ordinal 'e', broken URL)
  - Book-specific patch application
  - post_process_lessons() combined pipeline
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import warnings
import pytest
from text_correction import (
    clean_extracted_text,
    apply_book_corrections,
    post_process_lessons,
    SENS_DU_JEU_CORRECTIONS,
)


# ── clean_extracted_text ──────────────────────────────────────────────────────

class TestCleanExtractedText:
    def test_stray_ordinal_e_before_number(self):
        # "Riga 1998\ne\n30 temps" → "Riga 1998\n30e temps"
        text = 'Riga 1998\ne\n30 temps – trait aux blancs'
        result = clean_extracted_text(text)
        assert '30e temps' in result
        assert '\ne\n' not in result

    def test_stray_ordinal_e_two_digit_number(self):
        # "2e" ordinal — works when number is two digits
        text = 'position\ne\n2 diagramme suivant'
        result = clean_extracted_text(text)
        assert '2e diagramme' in result
        assert '\ne\n' not in result

    def test_broken_url_colon_slash(self):
        text = "Voir http ://example.com/path pour plus d'infos."
        result = clean_extracted_text(text)
        assert 'http://' in result
        assert 'http ://' not in result

    def test_multiple_broken_urls(self):
        text = 'http ://a.com et http ://b.com'
        result = clean_extracted_text(text)
        assert result.count('http://') == 2
        assert 'http ://' not in result

    def test_clean_text_unchanged(self):
        text = 'Ce texte est parfaitement propre. 30e temps, http://ok.com.'
        assert clean_extracted_text(text) == text

    def test_empty_string(self):
        assert clean_extracted_text('') == ''


# ── apply_book_corrections ────────────────────────────────────────────────────

class TestApplyBookCorrections:
    def _lessons(self, ch_id: str, text: str):
        return {ch_id: {'title': 'Test', 'text': text, 'category': 'test'}}

    def test_single_patch_applied(self):
        lessons = self._lessons('1', 'Il y a de de problèmes ici.')
        corrections = {'1': [('de de', 'de', 'duplicate word')]}
        patched, applied = apply_book_corrections(lessons, corrections)
        assert 'de de' not in patched['1']['text']
        assert 'de problèmes' in patched['1']['text']
        assert len(applied) == 1

    def test_multiple_patches_same_chapter(self):
        lessons = self._lessons('2', 'sans lequel et micro faiblesses')
        corrections = {
            '2': [
                ('sans lequel', 'dans lequel', 'fix 1'),
                ('micro faiblesses', 'micro-faiblesses', 'fix 2'),
            ]
        }
        patched, applied = apply_book_corrections(lessons, corrections)
        assert 'dans lequel' in patched['2']['text']
        assert 'micro-faiblesses' in patched['2']['text']
        assert len(applied) == 2

    def test_missing_patch_warns(self):
        lessons = self._lessons('3', 'texte sans erreur')
        corrections = {'3': [('introuvable', 'corrigé', 'will not match')]}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            patched, applied = apply_book_corrections(lessons, corrections)
        assert any('not found' in str(warning.message) for warning in w)
        assert applied == []

    def test_missing_chapter_warns(self):
        lessons = self._lessons('5', 'contenu')
        corrections = {'99': [('x', 'y', 'wrong chapter')]}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            apply_book_corrections(lessons, corrections)
        assert any('99' in str(warning.message) for warning in w)

    def test_input_not_mutated(self):
        lessons = {'1': {'title': 'T', 'text': 'original', 'category': 'c'}}
        corrections = {'1': [('original', 'modifié', 'test')]}
        apply_book_corrections(lessons, corrections)
        assert lessons['1']['text'] == 'original'


# ── post_process_lessons ──────────────────────────────────────────────────────

class TestPostProcessLessons:
    def test_generic_cleanup_applied_without_corrections(self):
        lessons = {
            '1': {'title': 'T', 'text': 'Riga 1998\ne\n30 temps', 'category': 'c'},
        }
        result = post_process_lessons(lessons)
        assert '30e temps' in result['1']['text']

    def test_book_corrections_applied_with_corrections(self):
        lessons = {
            '1': {'title': 'T', 'text': 'jeu de de dames', 'category': 'c'},
        }
        corrections = {'1': [('jeu de de dames', 'jeu de dames', 'fix')]}
        result = post_process_lessons(lessons, corrections)
        assert 'jeu de dames' in result['1']['text']

    def test_both_layers_applied_together(self):
        lessons = {
            '1': {
                'title': 'T',
                'text': 'http ://example.com et de de problèmes',
                'category': 'c',
            },
        }
        corrections = {'1': [('de de', 'de', 'dup')]}
        result = post_process_lessons(lessons, corrections)
        assert 'http://' in result['1']['text']
        assert 'de de' not in result['1']['text']

    def test_no_corrections_arg_allowed(self):
        lessons = {'1': {'title': 'T', 'text': 'texte', 'category': 'c'}}
        result = post_process_lessons(lessons)
        assert result['1']['text'] == 'texte'

    def test_sens_du_jeu_corrections_smoke(self):
        # Smoke test: corrections dict is importable and has expected chapters
        assert '101' in SENS_DU_JEU_CORRECTIONS
        assert '102' in SENS_DU_JEU_CORRECTIONS
        assert '110' in SENS_DU_JEU_CORRECTIONS
        for ch_id, patches in SENS_DU_JEU_CORRECTIONS.items():
            for patch in patches:
                assert len(patch) == 3, f'ch{ch_id}: patch must be (old, new, reason)'
