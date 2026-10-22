"""Page processing: deskew, column detection, character cell segmentation.

Designed for the 四书白文 woodblock scan (vertical columns, right-to-left,
two facing pages per scan).
"""
from __future__ import annotations

import cv2
import numpy as np


def to_gray(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def red_mask(rgb: np.ndarray) -> np.ndarray:
    """Detect the red 圈点 (reading marks) added by hand."""
    b, g, r = rgb[:, :, 2].astype(np.int16), rgb[:, :, 1].astype(np.int16), rgb[:, :, 0].astype(np.int16)
    m = ((r - g) > 32) & ((r - b) > 32)
    return m.astype(np.uint8)


def _inpaint_patches(gray: np.ndarray, mask: np.ndarray, radius: int = 7) -> np.ndarray:
    """Inpaint only around mask components (much faster than a full-frame inpaint)."""
    if not mask.any():
        return gray
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    out = gray.copy()
    H, W = gray.shape
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        pad = radius * 2
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
        sub = gray[y0:y1, x0:x1]
        m = (lab[y0:y1, x0:x1] == i).astype(np.uint8) * 255
        out[y0:y1, x0:x1] = cv2.inpaint(sub, m, radius, cv2.INPAINT_TELEA)
    return out


def ink_mask(rgb: np.ndarray, inpaint: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Return binary ink mask (255 = ink) after removing red marks and page rules."""
    gray = to_gray(rgb)
    red = red_mask(rgb)
    if inpaint and red.any():
        red_d = cv2.dilate(red, np.ones((3, 3), np.uint8))
        gray = _inpaint_patches(gray, red_d, 7)
    # background is light and fairly uniform; ink is dark
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return bw, red


def hysteresis_ink(gray: np.ndarray, lo_frac: float = 0.30, hi_frac: float = 0.62,
                   min_area: int = 60) -> np.ndarray:
    """Hysteresis threshold: keep weak ink only when it is connected to strong ink.

    The book's printed 圈点 (reading circles) are thin, light and dotted; they
    never form a strong core, so they drop out, while antialiased stroke tips
    stay because they touch the solid stroke.
    """
    p5, p90 = np.percentile(gray, 5), np.percentile(gray, 90)
    span = max(1.0, p90 - p5)
    t_strong = p5 + lo_frac * span
    t_weak = p5 + hi_frac * span
    strong = gray < t_strong
    weak = gray < t_weak
    if not weak.any():
        return np.zeros_like(weak)
    n, lab = cv2.connectedComponents(weak.astype(np.uint8), 8)
    keep = np.zeros(n, bool)
    if strong.any():
        keep[np.unique(lab[strong])] = True
    keep[0] = False
    ink = keep[lab]
    # drop tiny specks
    n2, lab2, stats, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    keep2 = np.zeros(n2, bool)
    for i in range(1, n2):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            keep2[i] = True
    return keep2[lab2]


def line_mask(bw: np.ndarray) -> np.ndarray:
    """Long horizontal / vertical rules (page frame)."""
    h, w = bw.shape
    kh = max(200, int(w * 0.16))
    kv = max(200, int(h * 0.16))
    hl = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (kh, 5)))
    vl = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (5, kv)))
    return cv2.dilate(cv2.bitwise_or(hl, vl), np.ones((9, 9), np.uint8))


def clean_text_mask(bw: np.ndarray, min_area: int = 90, max_side_ratio: float = 1.9) -> np.ndarray:
    lm = line_mask(bw)
    txt = cv2.bitwise_and(bw, cv2.bitwise_not(lm))
    n, lab, stats, _ = cv2.connectedComponentsWithStats((txt > 0).astype(np.uint8), 8)
    keep = np.zeros(n, np.uint8)
    h, w = bw.shape
    for i in range(1, n):
        x, y, ww, hh, aa = stats[i]
        if aa < min_area:
            continue
        # drop leftover rule fragments
        if ww > w * 0.5 or hh > h * 0.5:
            continue
        if ww > hh * 12 or hh > ww * 12:
            continue
        if (hh < 14 and ww > 90) or (ww < 14 and hh > 90):
            continue
        keep[i] = 1
    return keep[lab] * 255


def estimate_skew(rgb: np.ndarray, max_deg: float = 3.0) -> float:
    """Estimate page skew from the long frame rules."""
    bw, _ = ink_mask(rgb, inpaint=False)
    lm = line_mask(bw)
    small = cv2.resize(lm, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_NEAREST)
    lines = cv2.HoughLinesP(small, 1, np.pi / 720, threshold=120,
                            minLineLength=int(small.shape[1] * 0.25), maxLineGap=20)
    if lines is None:
        return 0.0
    angs = []
    for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
        a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(a) < max_deg:
            angs.append(a)
        b = 90 - abs(a)
        if abs(b) < max_deg:
            angs.append(np.sign(a) * b)
    if not angs:
        return 0.0
    return float(np.median(angs))


def rotate(rgb: np.ndarray, deg: float) -> np.ndarray:
    if abs(deg) < 0.03:
        return rgb
    h, w = rgb.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    return cv2.warpAffine(rgb, M, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def column_boxes(mask: np.ndarray) -> list[tuple[int, int]]:
    """Vertical text column x-ranges.

    Uses the vertical coverage profile: inside a column most rows carry ink,
    while the corridor between columns is empty for nearly the full height.
    """
    h, w = mask.shape
    cover = (mask > 0).sum(0).astype(np.float32) / h
    cover = np.convolve(cover, np.ones(7) / 7, mode="same")
    on = cover > 0.05
    d = np.diff(on.astype(np.int8))
    s = list(np.flatnonzero(d == 1) + 1)
    e = list(np.flatnonzero(d == -1) + 1)
    if on[0]:
        s = [0] + s
    if on[-1]:
        e = e + [w]
    runs = [(int(a), int(b)) for a, b in zip(s, e) if b - a > 40]
    if not runs:
        return []
    widths = np.array([b - a for a, b in runs])
    med = float(np.median(widths))
    runs = [(a, b) for a, b in runs if (b - a) > med * 0.45]
    # merge fragments split by a thin white seam
    merged = [list(runs[0])]
    for a, b in runs[1:]:
        if a - merged[-1][1] < med * 0.10:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(int(a), int(b)) for a, b in merged]


def _project(mask_col: np.ndarray) -> np.ndarray:
    p = (mask_col > 0).sum(1).astype(np.float32)
    return np.convolve(p, np.ones(5) / 5, mode="same")


def _low_runs(profile: np.ndarray, width: int, min_len: int = 12):
    low = profile < max(2.0, width * 0.02)
    d = np.diff(low.astype(np.int8))
    s = np.flatnonzero(d == 1) + 1
    e = np.flatnonzero(d == -1) + 1
    if low[0]:
        s = np.r_[0, s]
    if low[-1]:
        e = np.r_[e, len(low)]
    runs = [(int(a), int(b)) for a, b in zip(s, e) if b - a >= min_len]
    return runs


def estimate_pitch(mask: np.ndarray, cols: list[tuple[int, int]]) -> float:
    """Character advance estimated from the summed normalised column profiles."""
    if not cols:
        return 320.0
    P = np.zeros(mask.shape[0], dtype=np.float64)
    for x0, x1 in cols:
        p = (mask[:, x0:x1] > 0).sum(1).astype(np.float64) / max(1, x1 - x0)
        P += p
    nz = np.flatnonzero(P > P.max() * 0.05)
    if len(nz) < 200:
        return 320.0
    q = P[nz[0]:nz[-1]]
    q = q - q.mean()
    ac = np.correlate(q, q, "full")[len(q) - 1:]
    ac /= (ac[0] + 1e-9)
    lo, hi = 200, min(460, len(ac) - 2)
    if hi <= lo:
        return 320.0
    k = lo + int(np.argmax(ac[lo:hi]))
    # parabolic refinement
    if 0 < k < len(ac) - 1:
        y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
        denom = (y0 - 2 * y1 + y2)
        if abs(denom) > 1e-9:
            k = k + 0.5 * (y0 - y2) / denom
    return float(k)


def split_chars(mask_col: np.ndarray, pitch: float = 320.0) -> list[tuple[int, int]]:
    """Split a vertical column into characters on a regular grid.

    The grid pitch comes from the page-wide autocorrelation; per column we fit
    a small phase/scale correction so that every cut lands in a white band.
    """
    p = (mask_col > 0).sum(1).astype(np.float32)
    w = mask_col.shape[1]
    nz = np.flatnonzero(p > 0)
    if len(nz) == 0:
        return []
    runs = _low_runs(p, w, 10)
    y0 = runs[0][1] if runs and runs[0][0] <= 3 else int(nz[0])
    y1 = runs[-1][0] if runs and runs[-1][1] >= len(p) - 3 else int(nz[-1]) + 1
    if y1 - y0 < 60:
        y0, y1 = int(nz[0]), int(nz[-1]) + 1
    H = y1 - y0
    if H < 60:
        return [(y0, y1)]

    ps = np.convolve(p, np.ones(9) / 9, mode="same")
    scale = np.linspace(0.96, 1.04, 17)
    best = None
    for sc in scale:
        P = pitch * sc
        N = max(1, int(round(H / P)))
        if N == 0:
            continue
        for d in range(-int(P / 2), int(P / 2) + 1, 3):
            bs = [y0 + d + k * P for k in range(1, N)]
            if not bs:
                continue
            if bs[-1] > y1 or bs[0] < y0 + P * 0.5:
                continue
            idx = np.clip(np.round(bs).astype(int), 0, len(ps) - 1)
            score = float(ps[idx].mean()) + abs(sc - 1.0) * 30.0
            if best is None or score < best[0]:
                best = (score, P, d, N)
    if best is None:
        N = max(1, int(round(H / pitch)))
        P = H / N
        return [(int(y0 + i * P), int(y0 + (i + 1) * P)) for i in range(N)]
    _, P, d, N = best
    bound = [y0] + [y0 + d + k * P for k in range(1, N)] + [y1]
    for i in range(1, len(bound)):
        if bound[i] <= bound[i - 1] + 10:
            bound[i] = bound[i - 1] + 10
    bound[-1] = y1
    return [(int(round(bound[i])), int(round(bound[i + 1]))) for i in range(len(bound) - 1)]


def trim_box(mask: np.ndarray, box, pad: int = 4, min_ink: int = 40):
    """Tighten a cell box to its ink, with padding. Returns (x0,y0,x1,y1) or None."""
    x0, y0, x1, y1 = box
    sub = mask[y0:y1, x0:x1]
    ys, xs = np.nonzero(sub)
    if len(ys) < min_ink:
        return None
    return (int(xs.min() + x0), int(ys.min() + y0), int(xs.max() + x0 + 1), int(ys.max() + y0 + 1))


def text_block(mask: np.ndarray, frac: float = 0.22) -> tuple[int, int, int, int]:
    """Bounding box of the dense text area (ignores stray rule fragments)."""
    d = cv2.blur((mask > 0).astype(np.float32), (121, 121))
    rows, cols = d.sum(1), d.sum(0)
    def ext(p):
        th = p.max() * frac
        idx = np.flatnonzero(p > th)
        if len(idx) == 0:
            return 0, len(p) - 1
        return int(idx[0]), int(idx[-1])
    y0, y1 = ext(rows)
    x0, x1 = ext(cols)
    return x0, y0, x1, y1


def analyze_page(rgb: np.ndarray, min_comp_area: int = 60) -> dict:
    """Full page analysis: deskew, mask, columns, character cells.

    Cell assignment is component-based: every connected ink component is
    assigned to the grid slot containing its centroid, so neighbouring
    characters never bleed into a glyph.
    """
    ang = estimate_skew(rgb)
    rgb_r = rotate(rgb, ang)
    bw, _ = ink_mask(rgb_r)
    mask = clean_text_mask(bw)
    bx0, by0, bx1, by1 = text_block(mask)
    mask[:, :bx0] = 0
    mask[:, bx1 + 1:] = 0
    mask[:by0] = 0
    mask[by1 + 1:] = 0

    cols = column_boxes(mask)
    if not cols:
        return dict(angle=ang, columns=[], cells=[], mask=mask, lab=np.zeros_like(mask),
                    block=(bx0, by0, bx1, by1), pitch=320.0)
    pitch = estimate_pitch(mask, cols)

    n, lab, stats, cent = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)

    col_slots = {}
    cell_ranges = []
    for ci, (x0, x1) in enumerate(cols):
        ranges = split_chars(mask[:, x0:x1], pitch)
        col_slots[ci] = (x0, x1)
        for ri, (y0, y1) in enumerate(ranges):
            cell_ranges.append([ci, ri, x0, x1, y0, y1])

    def nearest_cell(cx, cy):
        best = None
        for ci, (x0, x1) in enumerate(cols):
            if x0 - 20 <= cx <= x1 + 20:
                for k, (cci, ri, _, _, y0, y1) in enumerate(cell_ranges):
                    if cci != ci:
                        continue
                    c = (y0 + y1) / 2
                    d = abs(cy - c)
                    if d < (y1 - y0) * 0.75 and (best is None or d < best[0]):
                        best = (d, k)
                break
        return best[1] if best else None

    dt = cv2.distanceTransform((mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
    comps = []
    for i in range(1, n):
        a = stats[i, cv2.CC_STAT_AREA]
        if a < 55:
            continue
        # drop hair-thin fragments: printed 圈点 arcs and paper creases
        if a < 3000 and float(dt[lab == i].max()) < 2.3:
            continue
        w, h = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if w > mask.shape[1] * 0.5 or h > mask.shape[0] * 0.5:
            continue
        comps.append(i)

    # pass 1: nearest slot by centroid
    assign = {}
    for i in comps:
        k = nearest_cell(cent[i][0], cent[i][1])
        if k is not None:
            assign.setdefault(k, []).append(i)

    def bbox_of(ids):
        x0 = min(int(stats[i, cv2.CC_STAT_LEFT]) for i in ids)
        y0 = min(int(stats[i, cv2.CC_STAT_TOP]) for i in ids)
        x1 = max(int(stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH]) for i in ids)
        y1 = max(int(stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT]) for i in ids)
        return x0, y0, x1, y1

    # pass 2: pull in detached strokes (撇/捺 tips, dots) that overlap the cell box
    for _ in range(2):
        boxes = {k: bbox_of(ids) for k, ids in assign.items()}
        owner = {i: k for k, ids in assign.items() for i in ids}
        for i in comps:
            if i in owner:
                continue
            x0 = int(stats[i, cv2.CC_STAT_LEFT]); y0 = int(stats[i, cv2.CC_STAT_TOP])
            x1 = x0 + int(stats[i, cv2.CC_STAT_WIDTH]); y1 = y0 + int(stats[i, cv2.CC_STAT_HEIGHT])
            area = int(stats[i, cv2.CC_STAT_AREA])
            best = None
            for k, (bx0, by0, bx1, by1) in boxes.items():
                ix = max(0, min(x1, bx1 + 6) - max(x0, bx0 - 6))
                iy = max(0, min(y1, by1 + 6) - max(y0, by0 - 6))
                ov = ix * iy
                if ov > 0.45 * max(1, area) and (best is None or ov > best[0]):
                    best = (ov, k)
            if best:
                assign[best[1]].append(i)
                owner[i] = best[1]

    cells = []
    for k, ids in assign.items():
        ci, ri, x0, x1, y0, y1 = cell_ranges[k]
        xa, ya, xb, yb = bbox_of(ids)
        sub = np.isin(lab[ya:yb, xa:xb], ids)
        if sub.sum() < 80:
            continue
        cells.append(dict(col=ci, row=ri, x0=int(xa), y0=int(ya), x1=int(xb), y1=int(yb),
                          slot_y0=y0, slot_y1=y1, col_x0=x0, col_x1=x1,
                          comp_ids=ids, ink=float(sub.mean())))
    cells.sort(key=lambda c: (c["col"], c["row"]))
    return dict(angle=ang, columns=cols, cells=cells, mask=mask, lab=lab,
                block=(bx0, by0, bx1, by1), pitch=pitch)


