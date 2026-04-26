import subprocess
import re
import os
import json
from PIL import Image
import numpy as np

PDF = '/home/user/Ai-draught/dubois_apprent_combin.pdf'
TMPDIR = '/tmp/dubois_pages'
os.makedirs(TMPDIR, exist_ok=True)

# ─── STEP 1: Extract all solutions from text ────────────────────────────────

def is_valid_move(m):
    parts = re.split(r'[-x]', m)
    if len(parts) < 2:
        return False
    try:
        nums = [int(p) for p in parts]
        return all(1 <= n <= 50 for n in nums) and len(nums) <= 8
    except:
        return False

def extract_solutions_from_page(page_text):
    solutions = {}
    pattern = r'D(\d+)\s*:\s*(.*?)(?=D\d+\s*:|$)'
    matches = re.findall(pattern, page_text, re.DOTALL)
    for d_num_str, sol_text in matches:
        d_num = int(d_num_str)
        sol_text_clean = sol_text.replace('\n', ' ').strip()
        raw_moves = re.findall(r'\b(\d{1,2}[-x]\d{1,2}(?:[-x]\d{1,2})*)\b', sol_text_clean)
        valid_moves = [m for m in raw_moves if is_valid_move(m)]
        solutions[d_num] = {
            'text': sol_text_clean[:200],
            'first_move': valid_moves[0] if valid_moves else None
        }
    return solutions

# Extract text page by page
result = subprocess.run(['pdftotext', '-f', '1', '-l', '133', PDF, '-'],
                       capture_output=True, text=True)
full_text = result.stdout

# Split into pages by form feed
all_pages_text = full_text.split('\f')
print(f"Total text pages: {len(all_pages_text)}")

# Known solution page indices (0-based)
SOL_PAGES = [6, 9, 12, 15, 18, 21, 24, 27, 30, 34, 37, 40, 43, 46, 49, 52,
             55, 58, 61, 64, 67, 71, 74, 77, 80, 83, 86, 89, 92, 95, 98, 101,
             104, 107, 110, 113, 117, 121, 125, 129, 132]

# Corresponding exercise pages (one before each solution page)
EX_PAGES = [s - 1 for s in SOL_PAGES]  # 0-based indices of exercise pages

all_solutions = {}  # D-number -> {text, first_move}
chapter_titles = {}  # chapter index (0-based) -> title string

for ch_idx, sol_page_idx in enumerate(SOL_PAGES):
    page_text = all_pages_text[sol_page_idx] if sol_page_idx < len(all_pages_text) else ''
    sols = extract_solutions_from_page(page_text)
    for d_num, sol in sols.items():
        all_solutions[d_num] = sol
    
    # Extract chapter title from exercise page
    ex_page_text = all_pages_text[EX_PAGES[ch_idx]] if EX_PAGES[ch_idx] < len(all_pages_text) else ''
    # Title is usually in first few lines
    lines = [l.strip() for l in ex_page_text.split('\n') if l.strip()]
    title = lines[0] if lines else f'Chapitre {ch_idx+1}'
    chapter_titles[ch_idx] = title

print(f"Solutions found: {len(all_solutions)}")
valid_count = sum(1 for s in all_solutions.values() if s['first_move'])
print(f"With valid first move: {valid_count}")

# Save solutions
with open('/tmp/solutions.json', 'w') as f:
    json.dump({'solutions': all_solutions, 'chapter_titles': chapter_titles,
               'ex_pages': EX_PAGES, 'sol_pages': SOL_PAGES}, f, indent=2)

print("Solutions saved to /tmp/solutions.json")
