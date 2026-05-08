"""
Extract lesson text per chapter from the Dubois combinaisons PDF.
Outputs backend/lessons.json  {chapter_num: {title, text, category}}
"""
import subprocess, re, json

result = subprocess.run(
    ['pdftotext', 'docs/livres/apprentissage/dubois_apprendre_combinaisons.pdf', '-'],
    capture_output=True, text=True, cwd='/home/user/Ai-draught'
)
pages = result.stdout.split('\f')

CHAPTER_CATEGORIES = {
    1:'combinaisons_2', 2:'combinaisons_2_3', 3:'combinaisons_3',
    4:'combinaisons_3', 5:'combinaisons_3_4', 6:'combinaisons_3_4',
    7:'combinaisons_2_3', 8:'combinaisons_3', 9:'combinaisons_3',
    10:'combinaisons_3', 11:'combinaisons_3',
    12:'combinaisons_4', 13:'combinaisons_4', 14:'combinaisons_4',
    15:'combinaisons_4', 16:'combinaisons_4', 17:'combinaisons_4',
    18:'combinaisons_4', 19:'combinaisons_4', 20:'combinaisons_4',
    21:'combinaisons_4',
    22:'combinaisons_4_5', 23:'combinaisons_4_5', 24:'combinaisons_4_5',
    25:'combinaisons_4_5', 26:'combinaisons_4_5', 27:'combinaisons_4_5',
    28:'combinaisons_4_5', 29:'combinaisons_4_5',
    30:'combinaisons_5', 31:'combinaisons_5',
    32:'combinaisons_5_6', 33:'combinaisons_5_6', 34:'combinaisons_5_6',
    35:'combinaisons_5_6', 36:'combinaisons_5_6', 37:'combinaisons_5_6',
    38:'combinaisons_5_6', 39:'combinaisons_5_6', 40:'combinaisons_5_6',
    41:'combinaisons_6',
}

# Detect chapter start pages (exclude TOC: lines with "....." are TOC entries)
CHAPTER_RE = re.compile(r'^Chapitre\s+(\d+)\s*[:\-]?\s*(.+)', re.MULTILINE)
EXERCISES_RE = re.compile(r'^\s*COMBINAISONS\s+EN\s+\d', re.MULTILINE)

chapter_pages = {}
for pg_idx, page_text in enumerate(pages):
    for m in CHAPTER_RE.finditer(page_text):
        line = m.group(0)
        if '.....' in line:  # TOC entry — skip
            continue
        ch_num = int(m.group(1))
        title_raw = re.sub(r'\s+', ' ', m.group(2)).strip().rstrip('.')
        # If the title ends with a conjunction/preposition, the next line may be a continuation
        next_pos = m.end()
        rest = page_text[next_pos:]
        cont_m = re.match(r'[ \t]*\n([a-z][^\n]{0,60})\n', rest)
        if cont_m:
            title_raw = title_raw + ' ' + cont_m.group(1).strip()
        if ch_num not in chapter_pages:
            chapter_pages[ch_num] = (pg_idx, f"Chapitre {ch_num} : {title_raw}")

lessons = {}
chapter_nums = sorted(chapter_pages.keys())

for i, ch_num in enumerate(chapter_nums):
    start_pg, title = chapter_pages[ch_num]
    end_pg = chapter_pages[chapter_nums[i+1]][0] if i+1 < len(chapter_nums) else len(pages)

    chapter_text = '\n'.join(pages[start_pg:end_pg])

    # Keep only lesson portion — cut before exercise diagrams page
    m_ex = EXERCISES_RE.search(chapter_text)
    lesson_text = chapter_text[:m_ex.start()] if m_ex else chapter_text

    # Remove chapter heading (one or two lines) already stored in title
    lesson_text = re.sub(r'^Chapitre\s+\d+[^\n]*\n?(?:[a-z][^\n]*\n)?', '', lesson_text, count=1, flags=re.IGNORECASE)

    # Remove diagram captions (appear in lesson illustrative diagrams, image-only)
    lesson_text = re.sub(r'[ \t]*(Trait aux (?:blancs|noirs|Blancs|Noirs)|La rafle|La prise majoritaire)[ \t]*\n?', '\n', lesson_text)

    # Remove lone page numbers
    lesson_text = re.sub(r'^\s*\d{1,3}\s*$', '', lesson_text, flags=re.MULTILINE)

    # Collapse blank lines
    lesson_text = re.sub(r'\n{3,}', '\n\n', lesson_text).strip()

    if not lesson_text:
        continue

    lessons[str(ch_num)] = {
        "title": title,
        "text": lesson_text,
        "category": CHAPTER_CATEGORIES.get(ch_num, ""),
    }

out_path = 'backend/lessons.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(lessons, f, ensure_ascii=False, indent=2)

print(f"Extracted {len(lessons)} lessons → {out_path}")
for ch in sorted(lessons.keys(), key=int):
    d = lessons[ch]
    print(f"  Ch{ch:2d}: {d['title'][:55]:<55} ({len(d['text'])} chars)")
