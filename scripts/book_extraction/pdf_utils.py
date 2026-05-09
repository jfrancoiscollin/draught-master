"""
PDF utility functions: text extraction and image rendering.
Wraps pdftotext and pdftoppm (poppler tools, must be installed).
"""
from __future__ import annotations
import glob
import subprocess
import tempfile
from pathlib import Path
from typing import List

import numpy as np
from PIL import Image


def extract_text_pages(pdf_path: str, cwd: str = '.') -> List[str]:
    """Return list of page texts (split on form-feed \\f)."""
    result = subprocess.run(
        ['pdftotext', pdf_path, '-'],
        capture_output=True, text=True, cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(f'pdftotext failed: {result.stderr}')
    return result.stdout.split('\f')


def render_page_gray(
    pdf_path: str,
    page: int,           # 1-based
    dpi: int = 200,
    cwd: str = '.',
) -> np.ndarray:
    """Render a single PDF page and return a float32 grayscale array."""
    with tempfile.TemporaryDirectory() as tmp:
        prefix = str(Path(tmp) / 'pg')
        subprocess.run(
            ['pdftoppm', '-r', str(dpi), '-f', str(page), '-l', str(page),
             '-png', pdf_path, prefix],
            capture_output=True, cwd=cwd,
        )
        files = sorted(glob.glob(f'{prefix}-*.png'))
        if not files:
            raise RuntimeError(f'pdftoppm produced no output for page {page}')
        img = Image.open(files[0])
        arr = np.array(img)
        if arr.ndim == 3:
            return arr[:, :, :3].mean(axis=2).astype(np.float32)
        return arr.astype(np.float32)
