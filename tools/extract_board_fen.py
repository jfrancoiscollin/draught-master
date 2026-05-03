"""
Extract FEN positions from draughts board images in the Dubois PDF.
Detects boards by finding dark/light checkerboard regions, then
samples each dark square to detect piece color.
"""
import sys
from PIL import Image
import numpy as np

# International draughts: squares 1-50 are the dark squares
# On a 10x10 board, rows 0-9 top-to-bottom, cols 0-9 left-to-right
# Dark squares: (row+col) % 2 == 1
# Numbering: row 0 cols 1,3,5,7,9 → squares 1-5
#             row 1 cols 0,2,4,6,8 → squares 6-10
# etc.

def sq_number(row, col):
    """Return square number (1-50) for a dark square, or None if light."""
    if (row + col) % 2 == 0:
        return None  # light square
    dark_in_row = col // 2  # 0-4
    return row * 5 + dark_in_row + 1


def find_boards_in_image(img_array, min_board_px=150):
    """
    Find checkerboard regions in the image.
    Strategy: look for columns of alternating dark/light vertical stripes
    then rows of alternating dark/light horizontal stripes.
    Returns list of (x1, y1, x2, y2) bounding boxes.
    """
    gray = np.mean(img_array[:, :, :3], axis=2)
    h, w = gray.shape

    # Threshold: below 180 = dark, above 200 = light
    # Look for regions with alternating dark/light in both axes
    # Simpler: find rectangular regions bounded by dark borders

    # Find rows/cols that are predominantly dark (borders)
    # Actually: find board by looking for regions where
    # variance in both axes is high (checkerboard pattern)

    # Step 1: compute local horizontal variance in 20px strips
    # Boards will have high variance (alternating light/dark)

    # Better approach: scan for the characteristic board border
    # The boards have a visible border (thin dark line around the whole board)

    # Use edge detection: find large rectangular black frames
    # Threshold the image
    dark = (gray < 100).astype(np.uint8)

    # Find horizontal runs of dark pixels (potential top/bottom borders)
    # and vertical runs (potential left/right borders)

    # Project dark pixels onto x-axis and y-axis
    col_dark = dark.sum(axis=0)  # how many dark pixels in each column
    row_dark = dark.sum(axis=1)  # how many dark pixels in each row

    # Find columns with many dark pixels (vertical borders)
    col_thresh = h * 0.15
    row_thresh = w * 0.15

    col_border = col_dark > col_thresh
    row_border = row_dark > row_thresh

    # Find runs of border columns/rows
    def find_transitions(arr):
        transitions = []
        in_run = False
        start = 0
        for i, v in enumerate(arr):
            if v and not in_run:
                in_run = True
                start = i
            elif not v and in_run:
                in_run = False
                transitions.append((start, i))
        if in_run:
            transitions.append((start, len(arr)))
        return transitions

    col_runs = find_transitions(col_border)
    row_runs = find_transitions(row_border)

    # This approach is getting complex. Use simpler:
    # Find boards by looking for the distinct checkerboard pattern
    # Sample the image at candidate board positions

    return find_boards_by_checkerboard(img_array)


def find_boards_by_checkerboard(img_array, step=20):
    """
    Scan the image to find checkerboard regions.
    Returns sorted list of (x1, y1, x2, y2).
    """
    gray = np.mean(img_array[:, :, :3], axis=2)
    h, w = gray.shape

    # For each possible top-left corner, check if it starts a board
    # A board region has alternating light/dark columns and rows
    # with a typical square size

    boards = []
    min_size = 150  # minimum board size in pixels

    # Scan at coarser resolution first
    scan_step = 5
    candidates = []

    for y in range(0, h - min_size, scan_step):
        for x in range(0, w - min_size, scan_step):
            # Check if (x,y) looks like the corner of a checkerboard
            # Sample a small region
            region = gray[y:y+60, x:x+60]
            if region.shape[0] < 60 or region.shape[1] < 60:
                continue
            # Check for alternating pattern: columns should alternate
            col_means = region.mean(axis=0)[::6]  # every 6 pixels
            if len(col_means) < 4:
                continue
            diffs = np.abs(np.diff(col_means))
            if diffs.mean() > 30:  # significant alternation
                candidates.append((x, y))

    # Group nearby candidates
    used = set()
    for i, (x1, y1) in enumerate(candidates):
        if i in used:
            continue
        # Find extent of this board
        # Try to determine square size by looking at color transitions
        region = gray[y1:y1+min(500, h-y1), x1:x1+min(500, w-x1)]
        sq_size = estimate_square_size(region)
        if sq_size is None or sq_size < 15:
            continue

        board_size = sq_size * 10
        x2 = min(x1 + board_size, w)
        y2 = min(y1 + board_size, h)

        # Verify this is actually a board
        if verify_board(gray, x1, y1, sq_size):
            boards.append((x1, y1, x2, y2, sq_size))
            # Mark nearby candidates as used
            for j, (xj, yj) in enumerate(candidates):
                if abs(xj - x1) < board_size and abs(yj - y1) < board_size:
                    used.add(j)

    return boards


def estimate_square_size(region):
    """Estimate checkerboard square size from a region."""
    # Look at column means and find the period of alternation
    col_means = region.mean(axis=0)
    # Find zero crossings of the derivative
    diff = np.diff(col_means)
    # Find positions where diff changes sign (local extrema)
    sign_changes = np.where(np.diff(np.sign(diff)))[0]
    if len(sign_changes) < 4:
        return None
    # Period = average distance between sign changes
    dists = np.diff(sign_changes)
    # Filter out very small dists
    dists = dists[dists > 5]
    if len(dists) == 0:
        return None
    return int(np.median(dists) * 2)  # *2 because sign changes at every half-period


def verify_board(gray, x1, y1, sq_size, tolerance=0.3):
    """Check if the region looks like a 10x10 draughts board."""
    h, w = gray.shape
    dark_count = 0
    light_count = 0
    for row in range(10):
        for col in range(10):
            sx = x1 + col * sq_size + sq_size // 4
            sy = y1 + row * sq_size + sq_size // 4
            ex = sx + sq_size // 2
            ey = sy + sq_size // 2
            if ex >= w or ey >= h:
                return False
            sq_val = gray[sy:ey, sx:ex].mean()
            if (row + col) % 2 == 0:  # should be light
                if sq_val > 150:
                    light_count += 1
            else:  # should be dark
                if sq_val < 150:
                    dark_count += 1
    return dark_count > 30 and light_count > 30


def analyze_board(img_array, x1, y1, sq_size):
    """
    Analyze a board and return the FEN string.
    White pieces = light circles on dark squares
    Black pieces = dark circles on dark squares
    """
    gray = np.mean(img_array[:, :, :3], axis=2)
    h, w = gray.shape

    # For each dark square, determine if there's a piece and its color
    white_squares = []
    black_squares = []

    for row in range(10):
        for col in range(10):
            if (row + col) % 2 == 0:
                continue  # light square, skip

            sq_num = sq_number(row, col)
            cx = x1 + col * sq_size + sq_size // 2
            cy = y1 + row * sq_size + sq_size // 2
            r = sq_size // 3  # piece radius

            if cx - r < 0 or cx + r >= w or cy - r < 0 or cy + r >= h:
                continue

            # Sample the square background (corners) and center
            center_region = gray[cy-r:cy+r, cx-r:cx+r]
            if center_region.size == 0:
                continue

            center_val = center_region.mean()

            # Sample background (dark square itself, no piece)
            # Use corners of the square
            bg_samples = []
            margin = sq_size // 6
            for bx, by in [(x1 + col*sq_size + margin, y1 + row*sq_size + margin),
                           (x1 + col*sq_size + sq_size - margin - 1, y1 + row*sq_size + margin),
                           (x1 + col*sq_size + margin, y1 + row*sq_size + sq_size - margin - 1)]:
                if 0 <= bx < w and 0 <= by < h:
                    bg_samples.append(gray[by, bx])
            bg_val = np.mean(bg_samples) if bg_samples else 100

            # If center is much lighter than dark square bg → white piece
            # If center is similar to dark bg but with darker central spot → black piece
            # No piece: center similar to dark background

            piece_brightness = center_val

            if piece_brightness > 160:
                white_squares.append(sq_num)
            elif piece_brightness < 80:
                black_squares.append(sq_num)
            # else: empty dark square

    white_str = ','.join(str(s) for s in sorted(white_squares))
    black_str = ','.join(str(s) for s in sorted(black_squares))
    return f"W:W{white_str}:B{black_str}"


def extract_boards_from_page(pdf_path, page_num, output_prefix="/tmp/board"):
    """Extract all board FENs from a given PDF page."""
    import subprocess
    img_path = f"/tmp/extracted_page_{page_num}.png"
    subprocess.run([
        "pdftoppm", "-r", "300", "-f", str(page_num), "-l", str(page_num),
        "-png", pdf_path, img_path.replace(".png", "")
    ], check=True, capture_output=True)
    # pdftoppm adds -PAGENUM.png suffix
    import glob
    files = glob.glob(f"/tmp/extracted_page_{page_num}-*.png")
    if not files:
        print(f"No image generated for page {page_num}")
        return []
    img_file = files[0]
    img = Image.open(img_file)
    arr = np.array(img)
    boards = find_boards_by_checkerboard(arr)
    results = []
    for i, (x1, y1, x2, y2, sq_size) in enumerate(sorted(boards, key=lambda b: (b[1], b[0]))):
        fen = analyze_board(arr, x1, y1, sq_size)
        results.append({'page': page_num, 'index': i+1, 'bounds': (x1,y1,x2,y2), 'sq_size': sq_size, 'fen': fen})
    return results


if __name__ == "__main__":
    page = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    pdf = "/home/user/Ai-draught/docs/livres/apprentissage/dubois_apprendre_combinaisons.pdf"
    results = extract_boards_from_page(pdf, page)
    for r in results:
        print(f"Board {r['index']} at {r['bounds']} sq={r['sq_size']}px: {r['fen']}")
