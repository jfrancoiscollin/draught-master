"""
Extract FEN positions from lesson board diagrams in the Dubois PDF.
For each chapter, renders the lesson page, finds board boundaries,
and extracts piece positions using center-sampling.
"""
import subprocess, json, re, sys, tempfile, glob, os
from PIL import Image
import numpy as np

PDF = "/home/user/Ai-draught/docs/livres/apprentissage/dubois_apprendre_combinaisons.pdf"
LESSONS_JSON = "/home/user/Ai-draught/backend/lessons.json"
DPI = 300

# TOC: chapter → page number (populated below)
CHAPTER_PAGES = {
    1:4,2:8,3:11,4:14,5:17,6:20,7:23,8:26,9:29,10:32,
    11:36,12:39,13:42,14:45,15:48,16:51,17:54,18:57,19:60,20:63,
    21:66,22:69,23:73,24:76,25:79,26:82,27:85,28:88,29:91,30:94,
    31:97,32:100,33:103,34:106,35:109,36:112,37:115,38:119,39:123,40:127,41:131
}


def render_page(page_num):
    """Render a PDF page at DPI and return numpy array (R channel only)."""
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
        return arr[:, :, 0].astype(np.float32)  # R channel (R=G, B=0 in this PDF)


def find_board_vertical_borders(r_ch, y_start=400, y_end=None, min_run=200):
    """Find x-positions of vertical board borders (long dark vertical runs)."""
    h, w = r_ch.shape
    if y_end is None:
        y_end = h
    borders = []
    for x in range(10, w-10, 3):
        col = r_ch[y_start:y_end, x]
        # Find longest dark run
        max_run = cur = 0
        for v in col:
            if v < 25:
                cur += 1
                max_run = max(max_run, cur)
            else:
                cur = 0
        if max_run >= min_run:
            borders.append(x)
    # Deduplicate: keep one representative per cluster
    result = []
    for x in borders:
        if not result or x - result[-1] > 10:
            result.append(x)
    return result


def find_board_horizontal_borders(r_ch, x_start=50, x_end=None, min_run=150):
    """Find y-positions of horizontal board borders (long dark horizontal runs)."""
    h, w = r_ch.shape
    if x_end is None:
        x_end = w
    borders = []
    for y in range(100, h-10):
        row = r_ch[y, x_start:x_end]
        max_run = cur = 0
        for v in row:
            if v < 25:
                cur += 1
                max_run = max(max_run, cur)
            else:
                cur = 0
        if max_run >= min_run:
            borders.append(y)
    # Deduplicate
    result = []
    for y in borders:
        if not result or y - result[-1] > 5:
            result.append(y)
    return result


def extract_fen(r_ch, x1, y1, x2, y2):
    """Extract FEN from a board region using center-pixel sampling."""
    sq_w = (x2 - x1) / 10.0
    sq_h = (y2 - y1) / 10.0
    white_sqs, black_sqs = [], []
    sample_r = max(3, int(min(sq_w, sq_h) * 0.06))  # tiny center sample

    for row in range(10):
        for col in range(10):
            if (row + col) % 2 == 0:
                continue  # light square
            sq_num = row * 5 + col // 2 + 1
            cx = int(x1 + col * sq_w + sq_w / 2)
            cy = int(y1 + row * sq_h + sq_h / 2)
            region = r_ch[max(0,cy-sample_r):cy+sample_r, max(0,cx-sample_r):cx+sample_r]
            if region.size == 0:
                continue
            val = region.mean()
            if val < 50:
                black_sqs.append(sq_num)
            elif val > 220:
                white_sqs.append(sq_num)

    w_str = ','.join(str(s) for s in sorted(white_sqs))
    b_str = ','.join(str(s) for s in sorted(black_sqs))
    return f"W:W{w_str}:B{b_str}"


def find_boards_on_page(r_ch):
    """Return list of (x1, y1, x2, y2) for each board on the page."""
    h, w = r_ch.shape

    # Find vertical borders across the whole page
    v_borders = find_board_vertical_borders(r_ch, y_start=300, min_run=250)
    h_borders = find_board_horizontal_borders(r_ch, min_run=200)

    if len(v_borders) < 2 or len(h_borders) < 2:
        return []

    # Pair consecutive vertical borders as board left/right
    # Filter: board width should be 500-900px
    board_xs = []
    for i in range(len(v_borders) - 1):
        x1, x2 = v_borders[i], v_borders[i+1]
        if 400 < (x2 - x1) < 1000:
            board_xs.append((x1, x2))

    # Find matching horizontal borders for each board column
    # A board's top/bottom borders span the board's x range
    boards = []
    # Use the first and last horizontal borders that span at least 2/3 of a board width
    # For simplicity: find the topmost and bottommost horizontal borders
    # that span at least 300px in dark pixels
    board_y_pairs = []
    # Find rows with very long dark runs (spans multiple boards)
    long_h = [y for y in h_borders
               if (r_ch[y, 50:w-50] < 25).sum() > w * 0.3]

    if len(long_h) >= 2:
        # Multiple possible top/bottom pairs - group by proximity
        # Typically boards have their top and bottom borders
        groups = []
        cur = [long_h[0]]
        for y in long_h[1:]:
            if y - cur[-1] < 20:
                cur.append(y)
            else:
                groups.append(cur)
                cur = [y]
        groups.append(cur)

        # Each group is either a single top border or bottom border
        # Pair them: min distance between groups should be ~500-800px (board height)
        for i in range(len(groups) - 1):
            y1 = groups[i][-1]  # bottom of top border group
            y2 = groups[i+1][0]  # top of bottom border group
            if 400 < (y2 - y1) < 900:
                board_y_pairs.append((y1 + 2, y2 - 2))
    elif long_h:
        # Only one horizontal border found - not enough info
        pass

    if not board_y_pairs and h_borders:
        # Fallback: use first and last horizontal borders
        y1, y2 = h_borders[0] + 2, h_borders[-1] - 2
        if y2 - y1 > 400:
            board_y_pairs = [(y1, y2)]

    for bx1, bx2 in board_xs:
        for by1, by2 in board_y_pairs:
            # Verify: center of this region should have some gray pixels
            mid_x = (bx1 + bx2) // 2
            mid_y = (by1 + by2) // 2
            sample = r_ch[mid_y-20:mid_y+20, mid_x-20:mid_x+20]
            gray_count = ((sample > 100) & (sample < 230)).sum()
            if gray_count > 50:  # has some gray (dark squares)
                boards.append((bx1+2, by1+2, bx2-2, by2-2))

    # Sort left to right (then top to bottom)
    boards.sort(key=lambda b: (b[1], b[0]))
    return boards


def process_chapter(chapter):
    page = CHAPTER_PAGES.get(chapter)
    if page is None:
        return []
    r_ch = render_page(page)
    if r_ch is None:
        return []
    boards = find_boards_on_page(r_ch)
    fens = [extract_fen(r_ch, *b) for b in boards]
    return fens


if __name__ == "__main__":
    chapters_to_process = list(range(1, 42))
    if len(sys.argv) > 1:
        chapters_to_process = [int(a) for a in sys.argv[1:]]

    with open(LESSONS_JSON) as f:
        lessons = json.load(f)

    results = {}
    for ch in chapters_to_process:
        fens = process_chapter(ch)
        ch_str = str(ch)
        results[ch_str] = fens
        status = "OK" if fens else "NO BOARDS"
        print(f"Ch {ch:2d} (page {CHAPTER_PAGES.get(ch,'?')}): {len(fens)} boards → {status}")
        if fens:
            for i, fen in enumerate(fens[:3]):
                print(f"  Diag {i+1}: {fen}")

    # Update lessons.json with diagram FENs
    for ch_str, fens in results.items():
        if ch_str in lessons and fens:
            lessons[ch_str]['diagrams'] = fens

    with open(LESSONS_JSON, 'w', encoding='utf-8') as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)

    print("\nlessons.json updated with diagram FENs.")
