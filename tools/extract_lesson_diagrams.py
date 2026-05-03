"""
Extract FEN positions from lesson board diagrams in the Dubois PDF.
Robust version: finds horizontal borders first, then vertical borders
that span the full board height (avoiding false positives from pieces/text).
"""
import subprocess, json, sys, tempfile, glob, os
from PIL import Image
import numpy as np

PDF = "/home/user/Ai-draught/docs/livres/apprentissage/dubois_apprendre_combinaisons.pdf"
LESSONS_JSON = "/home/user/Ai-draught/backend/lessons.json"
DPI = 300

CHAPTER_PAGES = {
    1:4,2:8,3:11,4:14,5:17,6:20,7:23,8:26,9:29,10:32,
    11:36,12:39,13:42,14:45,15:48,16:51,17:54,18:57,19:60,20:63,
    21:66,22:69,23:73,24:76,25:79,26:82,27:85,28:88,29:91,30:94,
    31:97,32:100,33:103,34:106,35:109,36:112,37:115,38:119,39:123,40:127,41:131
}


def render_page(page_num):
    with tempfile.TemporaryDirectory() as tmpdir:
        prefix = os.path.join(tmpdir, "pg")
        subprocess.run(
            ["pdftoppm", "-r", str(DPI), "-f", str(page_num), "-l", str(page_num),
             "-png", PDF, prefix],
            check=True, capture_output=True
        )
        files = glob.glob(f"{prefix}-*.png")
        if not files:
            return None
        arr = np.array(Image.open(files[0]))
        # Use R channel (which equals G in this PDF; B may vary slightly)
        return arr[:, :, 0].astype(np.float32)


def find_h_border_groups(r_ch, min_run=200):
    """Find groups of rows that are horizontal board borders."""
    h, w = r_ch.shape
    borders = []
    for y in range(100, h - 10):
        row = r_ch[y, 50:]
        max_run = cur = 0
        for v in row:
            if v < 25:
                cur += 1
                max_run = max(max_run, cur)
            else:
                cur = 0
        if max_run >= min_run:
            borders.append(y)
    groups = []
    if borders:
        cur = [borders[0]]
        for y in borders[1:]:
            if y - cur[-1] <= 8:
                cur.append(y)
            else:
                groups.append(cur)
                cur = [y]
        groups.append(cur)
    return [(g[0], g[-1]) for g in groups]


def find_v_borders_in_band(r_ch, y1, y2, min_span_ratio=0.82):
    """Find x positions of vertical borders that span most of the y1-y2 band."""
    w = r_ch.shape[1]
    min_run = int((y2 - y1) * min_span_ratio)
    borders = []
    for x in range(10, w - 10, 2):
        col = r_ch[y1:y2, x]
        max_run = cur = 0
        for v in col:
            if v < 25:
                cur += 1
                max_run = max(max_run, cur)
            else:
                cur = 0
        if max_run >= min_run:
            borders.append(x)
    # Deduplicate: one per cluster
    result = []
    for x in borders:
        if not result or x - result[-1] > 10:
            result.append(x)
    return result


def find_boards_on_page(r_ch):
    """Return list of (x1, y1, x2, y2) for boards on the page, sorted top→left."""
    h_groups = find_h_border_groups(r_ch)

    boards = []
    # Pair consecutive horizontal border groups as top/bottom of a board row
    for i in range(len(h_groups) - 1):
        by1 = h_groups[i][1] + 2    # just below top border
        by2 = h_groups[i + 1][0] - 2  # just above bottom border
        board_h = by2 - by1
        if not (350 < board_h < 1000):
            continue

        v_borders = find_v_borders_in_band(r_ch, by1, by2)
        # Pair consecutive vertical borders as left/right of a board
        for j in range(len(v_borders) - 1):
            bx1 = v_borders[j] + 2
            bx2 = v_borders[j + 1] - 2
            board_w = bx2 - bx1
            if 350 < board_w < 900:
                boards.append((bx1, by1, bx2, by2))

    boards.sort(key=lambda b: (b[1], b[0]))
    return boards


def extract_fen(r_ch, x1, y1, x2, y2):
    """
    Extract FEN from a board region.
    Center-pixel sampling: dark square bg ~192, black piece ~0, white piece ~255.
    King detection: a king has a second disc below center — sample at cy+30%sq_h:
      black king → still dark (<60) at that offset
      white king → still bright (>220) at that offset
      regular piece → background (~192)
    """
    sq_w = (x2 - x1) / 10.0
    sq_h = (y2 - y1) / 10.0
    white_sqs, black_sqs = [], []
    white_king_sqs, black_king_sqs = [], []
    sample_r = max(3, int(min(sq_w, sq_h) * 0.07))
    king_offset = int(sq_h * 0.30)  # offset to check for second disc

    img_h, img_w = r_ch.shape

    for row in range(10):
        for col in range(10):
            if (row + col) % 2 == 0:
                continue
            sq_num = row * 5 + col // 2 + 1
            cx = int(x1 + col * sq_w + sq_w / 2)
            cy = int(y1 + row * sq_h + sq_h / 2)

            region = r_ch[
                max(0, cy - sample_r):min(img_h, cy + sample_r),
                max(0, cx - sample_r):min(img_w, cx + sample_r)
            ]
            if region.size == 0:
                continue
            val = region.mean()

            if val < 50:
                # Check for king: second dark disc at cy + king_offset
                lower_y = cy + king_offset
                lower_val = r_ch[lower_y, cx] if 0 <= lower_y < img_h else 192
                if lower_val < 60:
                    black_king_sqs.append(sq_num)
                else:
                    black_sqs.append(sq_num)
            elif val > 220:
                # Check for white king: second bright disc at cy + king_offset
                lower_y = cy + king_offset
                lower_val = r_ch[lower_y, cx] if 0 <= lower_y < img_h else 192
                if lower_val > 200:
                    white_king_sqs.append(sq_num)
                else:
                    white_sqs.append(sq_num)

    w_parts = ','.join(str(s) for s in sorted(white_sqs))
    wk_parts = ','.join(f'K{s}' for s in sorted(white_king_sqs))
    b_parts = ','.join(str(s) for s in sorted(black_sqs))
    bk_parts = ','.join(f'K{s}' for s in sorted(black_king_sqs))

    w_str = ','.join(filter(None, [w_parts, wk_parts]))
    b_str = ','.join(filter(None, [b_parts, bk_parts]))
    return f"W:W{w_str}:B{b_str}"


def process_chapter(chapter, verbose=False):
    page = CHAPTER_PAGES.get(chapter)
    if page is None:
        return []
    r_ch = render_page(page)
    if r_ch is None:
        return []
    boards = find_boards_on_page(r_ch)
    fens = [extract_fen(r_ch, *b) for b in boards]
    if verbose:
        for i, (b, fen) in enumerate(zip(boards, fens)):
            print(f"  Board {i+1} bounds={b}: {fen}")
    return fens


if __name__ == "__main__":
    chapters_to_process = list(range(1, 42))
    if len(sys.argv) > 1:
        chapters_to_process = [int(a) for a in sys.argv[1:]]

    verbose = len(chapters_to_process) <= 5

    with open(LESSONS_JSON) as f:
        lessons = json.load(f)

    results = {}
    for ch in chapters_to_process:
        fens = process_chapter(ch, verbose=verbose)
        ch_str = str(ch)
        results[ch_str] = fens
        status = "OK" if fens else "NO BOARDS"
        print(f"Ch {ch:2d} (page {CHAPTER_PAGES.get(ch,'?')}): {len(fens)} boards → {status}")
        if verbose and fens:
            for i, fen in enumerate(fens[:5]):
                print(f"  Diag {i+1}: {fen}")

    # Update lessons.json
    for ch_str, fens in results.items():
        if ch_str in lessons:
            if fens:
                lessons[ch_str]['diagrams'] = fens
            else:
                lessons[ch_str].pop('diagrams', None)

    with open(LESSONS_JSON, 'w', encoding='utf-8') as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)

    print("\nlessons.json updated.")
