"""Page geometry for the 永乐大典 (C line).

The 大典 layout differs from both earlier corpora in four ways that matter to
segmentation:

  * every leaf is a single page (not a two-leaf spread), with a red 朱丝栏 frame;
  * the frame's vertical rules delimit *wide* columns, and most columns hold
    **two rows of small characters** (小字双行); a 字头 or section head is a single
    wide character in the same column;
  * page size, column pitch and character size all vary from page to page (and
    between volumes), so no constant may be inherited from A/B;
  * red is used for the rules and the 句读 marks, and in a few places for red
    labels (篆/隸/草), so colour separation is a first-class step.

The module exposes:

  deskew(rgb)             -> (rgb, angle)
  red_masks(rgb)          -> (line_red, ink_red)
  ink_mask(rgb)           -> bool ink mask with red removed
  detect_rules(red)       -> dict(lines_x, frame_y0, frame_y1, pitch)
  segment_columns(...)    -> cells with col/sub/row/kind
  draw_boxes(rgb, cells)  -> overlay for visual checks

All thresholds are in pixels of the working resolution; callers pass `dpi` and
the helpers scale the few absolute numbers by dpi/300.
"""
from __future__ import annotations

import cv2
import numpy as np

from pageproc import _inpaint_patches


# --------------------------------------------------------------------------- colour
def red_masks(rgb: np.ndarray):
    """Two red masks: a sensitive one for the rules, a strict one for ink removal."""
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    rg = r - g
    rb = r - b
    line = (rg > 24) & (rb > 20)
    ink = (rg > 48) & (rb > 42)
    return line, ink


def ink_mask(rgb: np.ndarray, frac: float = 0.34, dpi: int = 300) -> np.ndarray:
    """Black ink only: remove red (rules + 句读 + red labels), then threshold.

    A fixed paper-relative percentile eats the antialiased stroke edges on this
    scan (strokes become ragged and occasionally break), while a bare Otsu drifts
    on leaves with little ink.  The threshold is therefore Otsu, clamped to a
    paper-relative band: measured on 30 leaves, Otsu lands at ~0.55 of the
    p2..p50 span, and the clamp only matters on nearly blank leaves.
    """
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, red = red_masks(rgb)
    red_d = cv2.dilate(red.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    if red_d.any():
        gray = _inpaint_patches(gray, red_d.astype(np.uint8), max(5, int(7 * dpi / 300)))
    p2, p50 = np.percentile(gray, 2), np.percentile(gray, 50)
    span = max(1.0, p50 - p2)
    otsu, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thr = min(max(float(otsu), p2 + 0.42 * span), p2 + 0.62 * span)
    return gray < thr


# --------------------------------------------------------------------------- deskew
def _score_angle(red_small: np.ndarray, ang: float) -> float:
    h, w = red_small.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    rot = cv2.warpAffine(red_small, M, (w, h), flags=cv2.INTER_NEAREST)
    prof = rot.sum(0).astype(np.float64)
    k = min(40, len(prof) // 4)
    return float(np.sort(prof)[-k:].sum())


def deskew(rgb: np.ndarray, max_deg: float = 1.2, step: float = 0.05):
    """Rotate the page so the red rules are vertical.

    Scored on a quarter-scale red mask: a correctly aligned page concentrates the
    rule energy into a few columns, a skewed one smears it.
    """
    line, _ = red_masks(rgb)
    h, w = line.shape
    small = cv2.resize(line.astype(np.float32), (max(1, w // 4), max(1, h // 4)),
                       interpolation=cv2.INTER_AREA)
    angs = np.arange(-max_deg, max_deg + 1e-9, step)
    scores = [_score_angle(small, a) for a in angs]
    best = float(angs[int(np.argmax(scores))])
    # parabolic refinement on the score curve
    i = int(np.argmax(scores))
    if 0 < i < len(angs) - 1 and (scores[i - 1] - 2 * scores[i] + scores[i + 1]) < 0:
        den = scores[i - 1] - 2 * scores[i] + scores[i + 1]
        best += 0.5 * (scores[i - 1] - scores[i + 1]) / den * step
    if abs(best) < 0.03:
        return rgb, 0.0
    M = cv2.getRotationMatrix2D((w / 2, h / 2), best, 1.0)
    out = cv2.warpAffine(rgb, M, (w, h), flags=cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_REPLICATE)
    return out, float(best)


# --------------------------------------------------------------------------- rules
def _autocorr_pitch(prof: np.ndarray, lo: int, hi: int) -> float:
    q = prof.astype(np.float64) - float(np.mean(prof))
    if not np.any(q):
        return 0.0
    ac = np.correlate(q, q, "full")[len(q) - 1:]
    ac /= ac[0] + 1e-9
    hi = min(hi, len(ac) - 2)
    if hi <= lo + 2:
        return 0.0
    seg = ac[lo:hi]
    k = lo + int(np.argmax(seg))
    # prefer the fundamental: harmonics (2x, 3x the true period) also score high,
    # and picking one makes the line finder merge real rules as "double rules"
    top = float(seg.max())
    for j in range(lo + 1, hi - 1):
        if ac[j] >= 0.78 * top and ac[j] >= ac[j - 1] and ac[j] >= ac[j + 1]:
            k = j
            break
    if 0 < k < len(ac) - 1:
        y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-9:
            k = k + 0.5 * (y0 - y2) / den
    return float(k)


def _peaks(prof: np.ndarray, thr: float, dist: int):
    """Local maxima above thr, at least dist apart (greedy by height)."""
    cand = np.flatnonzero(prof > thr)
    if len(cand) == 0:
        return np.array([], int)
    order = cand[np.argsort(prof[cand])][::-1]
    kept = []
    for x in order:
        if all(abs(int(x) - k) >= dist for k in kept):
            kept.append(int(x))
    return np.array(sorted(kept), int)


def _rule_lines(vprof: np.ndarray, dpi: int) -> tuple[list[int], float]:
    """Vertical rule positions from the column-wise red profile."""
    h, w = 1, len(vprof)
    ps = np.convolve(vprof.astype(np.float64), np.ones(5) / 5, mode="same")
    if ps.max() <= 1e-6:
        return [], 0.0
    pitch0 = _autocorr_pitch(ps, max(60, int(w * 0.03)), max(120, int(w * 0.30)))
    if pitch0 <= 0:
        return [], 0.0
    thr = max(0.10 * ps.max(), 0.07)
    peaks = _peaks(ps, thr, max(20, int(pitch0 * 0.45)))
    if len(peaks) < 2:
        return [], pitch0
    # refine pitch from the observed gaps that are close to the autocorrelation value
    gaps = np.diff(peaks).astype(float)
    good = gaps[(gaps > pitch0 * 0.75) & (gaps < pitch0 * 1.25)]
    pitch = float(np.median(good)) if len(good) >= 2 else pitch0
    # fill missing lines: a gap that is ~k*pitch gets k-1 lines inserted
    filled = [int(peaks[0])]
    for a, b in zip(peaks[:-1], peaks[1:]):
        gap = b - a
        k = int(round(gap / pitch))
        if k >= 2 and abs(gap / pitch - k) < 0.22:
            for j in range(1, k):
                filled.append(int(round(a + j * gap / k)))
        elif gap < pitch * 0.30 and len(filled) > 1:
            # a double rule (frame drawn twice): keep the stronger one
            if ps[b] > ps[filled[-1]]:
                filled[-1] = int(b)
            continue
        filled.append(int(b))
    # snap each line to the local profile maximum (+-8% pitch)
    half = max(3, int(pitch * 0.08))
    out = []
    for x in filled:
        a, b = max(0, x - half), min(len(ps), x + half + 1)
        out.append(int(a + np.argmax(ps[a:b])))
    # drop near-duplicates again after snapping
    ded = [out[0]]
    for x in out[1:]:
        if x - ded[-1] >= pitch * 0.30:
            ded.append(x)
        elif ps[x] > ps[ded[-1]]:
            ded[-1] = x
    return ded, pitch


def detect_rules(rgb: np.ndarray, dpi: int = 300) -> dict:
    """Vertical red rules, the horizontal frame, and the text band."""
    line, _ = red_masks(rgb)
    h, w = line.shape
    vprof = line.sum(0).astype(np.float64) / h
    lines, pitch = _rule_lines(vprof, dpi)
    # horizontal rules: use the x-range actually covered by the vertical frame
    if len(lines) >= 2:
        x0, x1 = lines[0], lines[-1]
    else:
        x0, x1 = 0, w
    hprof = line[:, x0:x1 + 1].sum(1).astype(np.float64) / max(1, x1 - x0 + 1)
    hp = np.convolve(hprof, np.ones(5) / 5, mode="same")
    thr = max(0.25 * hp.max(), 0.12)
    rows = _peaks(hp, thr, max(20, int(h * 0.02)))
    y0 = int(rows[0]) if len(rows) else 0
    y1 = int(rows[-1]) if len(rows) else h - 1
    # the frame's top/bottom lines sit on the highest peaks near the extremes
    if len(rows) >= 2:
        top = [r for r in rows if r < h * 0.30]
        bot = [r for r in rows if r > h * 0.70]
        if top:
            y0 = int(top[int(np.argmax([hp[r] for r in top]))])
        if bot:
            y1 = int(bot[int(np.argmax([hp[r] for r in bot]))])
    return dict(lines=lines, pitch=float(pitch), frame=(int(x0), int(y0), int(x1), int(y1)),
                hprof=hp)


# --------------------------------------------------------------------------- cells
def _white_corridor(ink: np.ndarray, y0: int, y1: int, w: int) -> np.ndarray:
    """For each x, the share of rows in [y0,y1) with no ink within +-2 px."""
    band = ink[y0:y1, :]
    if band.size == 0:
        return np.zeros(w, np.float32)
    d = cv2.dilate(band.astype(np.uint8), np.ones((1, 5), np.uint8))
    return 1.0 - d.mean(0)


def _split_subrows(ink: np.ndarray, L: int, R: int, y0: int, y1: int, pitch: float):
    """Return (xs, kind): xs is 1 or 2 sub-row x-ranges.

    A two-row column has a vertical white corridor somewhere in the middle 60% of
    the column.  A wide 字头 crosses it, but only over a fraction of the height,
    so the corridor test uses the share of *rows* that are clear.
    """
    w = ink.shape[1]
    corridor = _white_corridor(ink, y0, y1, w)
    c0 = int(L + 0.28 * (R - L))
    c1 = int(L + 0.72 * (R - L)) + 1
    seg = corridor[c0:c1]
    if len(seg) == 0:
        return [(L, R)], "single"
    k = int(np.argmax(seg))
    frac = float(seg[k])
    xsplit = c0 + k
    left = ink[y0:y1, L:xsplit]
    right = ink[y0:y1, xsplit:R]
    have_l, have_r = float(left.mean()), float(right.mean())
    # Both sub-rows must carry comparable ink.  On a *single* row of small
    # characters (e.g. 卷10949 的 建置沿革 页) the text is offset to one side of the
    # red column, so a white corridor exists and the naive test would split every
    # character in half.  Requiring the two sides to be balanced rejects that.
    balanced = min(have_l, have_r) >= 0.30 * max(1e-6, max(have_l, have_r))
    if frac >= 0.62 and have_l > 0.01 and have_r > 0.01 and balanced:
        return [(L, xsplit), (xsplit, R)], "double"
    return [(L, R)], "single"


def _big_bands(ink: np.ndarray, L: int, R: int, y0: int, y1: int, xsplit: int,
               pitch: float) -> list[tuple[int, int]]:
    """y-ranges where a glyph crosses the sub-row gutter (a wide 字头)."""
    half = max(3, int(0.035 * (R - L)))
    bridge = ink[y0:y1, max(L, xsplit - half):min(R, xsplit + half)].any(1)
    # close small holes so a diagonal stroke is not cut into pieces
    k = max(3, int(pitch * 0.03)) | 1
    bridge = cv2.morphologyEx(bridge.astype(np.uint8), cv2.MORPH_CLOSE,
                              np.ones((k, 1), np.uint8))[:, 0] > 0
    runs = []
    s = None
    for i, v in enumerate(bridge):
        if v and s is None:
            s = i
        if not v and s is not None:
            runs.append((y0 + s, y0 + i))
            s = None
    if s is not None:
        runs.append((y0 + s, y0 + len(bridge)))
    return [(a, b) for a, b in runs if b - a > 0.45 * (R - L)]


def _split_chars(strip: np.ndarray, pitch: float) -> list[tuple[int, int]]:
    """Cut a sub-row into characters on a regular grid (adapted from pageproc)."""
    p = (strip > 0).sum(1).astype(np.float32)
    w = strip.shape[1]
    nz = np.flatnonzero(p > 0)
    if len(nz) == 0:
        return []
    y0, y1 = int(nz[0]), int(nz[-1]) + 1
    H = y1 - y0
    if H < pitch * 0.45:
        return [(y0, y1)]
    ps = np.convolve(p, np.ones(9) / 9, mode="same")
    best = None
    for sc in np.linspace(0.94, 1.06, 13):
        P = pitch * sc
        N = max(1, int(round(H / P)))
        if N == 0:
            continue
        for d in np.arange(-P / 2, P / 2 + 1e-9, max(1.0, P / 24)):
            bs = [y0 + d + k * P for k in range(1, N)]
            if bs and (bs[-1] > y1 - P * 0.3 or bs[0] < y0 + P * 0.3):
                continue
            idx = np.clip(np.round(bs).astype(int), 0, len(ps) - 1)
            score = float(ps[idx].mean()) + abs(sc - 1.0) * 30.0
            if best is None or score < best[0]:
                best = (score, P, d, N)
    if best is None:
        N = max(1, int(round(H / pitch)))
        return [(int(y0 + i * H / N), int(y0 + (i + 1) * H / N)) for i in range(N)]
    _, P, d, N = best
    bounds = [y0] + [y0 + d + k * P for k in range(1, N)] + [y1]
    for i in range(1, len(bounds)):
        if bounds[i] <= bounds[i - 1] + max(8, pitch * 0.25):
            bounds[i] = bounds[i - 1] + max(8, pitch * 0.25)
    bounds[-1] = y1
    return [(int(round(bounds[i])), int(round(bounds[i + 1]))) for i in range(len(bounds) - 1)]


def segment_page(rgb: np.ndarray, dpi: int = 300) -> dict:
    """Full page -> columns, cells.  No labelling here, geometry only."""
    rgb, angle = deskew(rgb)
    ink = ink_mask(rgb, dpi=dpi)
    rules = detect_rules(rgb, dpi=dpi)
    lines = rules["lines"]
    x0, y0, x1, y1 = rules["frame"]
    pitch = rules["pitch"]
    out = dict(angle=angle, ink=ink, rules=rules, cells=[], columns=[])

    if len(lines) < 2:
        return out
    # text band: inside the frame, with a small margin so the rule itself is out
    band0 = min(y1, max(y0, 0)) + max(4, int(pitch * 0.04))
    band1 = max(band0 + 10, y1 - max(4, int(pitch * 0.04)))

    cells = []
    for ci in range(len(lines) - 1):
        L, R = int(lines[ci]), int(lines[ci + 1])
        if R - L < pitch * 0.45:
            continue
        Lm, Rm = L + max(2, int(pitch * 0.015)), R - max(2, int(pitch * 0.015))
        # ink footprint of this column decides the top/bottom of the text
        col = ink[band0:band1, Lm:Rm]
        rows = np.flatnonzero(col.sum(1) > 0)
        if len(rows) < 5:
            continue
        t0 = band0 + int(rows[0])
        t1 = band0 + int(rows[-1]) + 1
        subs, kind = _split_subrows(ink, Lm, Rm, t0, t1, pitch)
        bigs = []
        if len(subs) == 2:
            xsplit = subs[1][0]
            bigs = _big_bands(ink, Lm, Rm, t0, t1, xsplit, pitch)
        out["columns"].append(dict(idx=ci, x0=L, x1=R, kind=kind,
                                   n_sub=len(subs), y0=t0, y1=t1))
        # --- wide single glyphs (字头) are their own cells
        for (a, b) in bigs:
            cells.append(dict(col=ci, sub=0, kind="big", x0=Lm, y0=int(a), x1=Rm, y1=int(b)))
        # --- remaining ranges, split into sub-row strips
        cuts = [(t0, t1)]
        for (a, b) in bigs:
            nxt = []
            for (c, d) in cuts:
                if b <= c or a >= d:
                    nxt.append((c, d))
                else:
                    if a > c:
                        nxt.append((c, a))
                    if b < d:
                        nxt.append((b, d))
            cuts = nxt
        for (c, d) in cuts:
            if d - c < pitch * 0.30:
                continue
            for si, (sl, sr) in enumerate(subs):
                strip = ink[c:d, sl:sr]
                if strip.sum() < 40:
                    continue
                # expected character advance: half the rule pitch for a two-row
                # column, the full rule pitch for a single wide glyph
                guess = (pitch * 0.5) if len(subs) == 2 else pitch
                ys = np.flatnonzero(strip.sum(1) > 0)
                hstrip = int(ys[-1] - ys[0]) + 1 if len(ys) else 0
                if hstrip < guess * 0.5:
                    continue
                p = _autocorr_pitch(strip.sum(1).astype(np.float64),
                                    max(8, int(guess * 0.55)), max(16, int(guess * 1.55)))
                char_pitch = p if p > 0 else guess
                char_pitch = float(np.clip(char_pitch, guess * 0.62, guess * 1.35))
                # a short strip with a single glyph must not be cut
                if hstrip < char_pitch * 1.45:
                    ranges = [(c + int(ys[0]), c + int(ys[-1]) + 1)]
                else:
                    ranges = [(c + a, c + b) for a, b in
                              _split_chars(strip, char_pitch)]
                for ri, (a, b) in enumerate(ranges):
                    cells.append(dict(col=ci, sub=si, kind="small",
                                      x0=int(sl), y0=int(a), x1=int(sr), y1=int(b)))
    out["cells"] = cells
    return out


def assign_components(ink: np.ndarray, cells: list[dict], pitch: float,
                      min_area: float = 60, y_core=None):
    """Attach connected components to cells (two passes, as in pageproc).

    Each cell gets `comp_ids`, `bbox` (tight ink box) and `ink` (fill ratio).
    Returns the component label image so callers can build per-cell masks from
    exactly the assigned components (never from a rectangle crop, which lets a
    neighbour's stroke in).
    """
    """Attach connected components to cells (two passes, as in pageproc).

    Each cell gets `comp_ids`, `bbox` (tight ink box) and `ink` (fill ratio).
    """
    n, lab, stats, cent = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    comps = []
    for i in range(1, n):
        a = stats[i, cv2.CC_STAT_AREA]
        if a < min_area:
            continue
        comps.append(i)
    # pass 1: centroid inside the cell box (with a small margin)
    assign = {k: [] for k in range(len(cells))}
    owner = {}
    for i in comps:
        cx, cy = cent[i]
        best = None
        for k, c in enumerate(cells):
            lo, hi = (y_core[k] if y_core is not None else (c["y0"] - 4, c["y1"] + 4))
            if c["x0"] - 4 <= cx <= c["x1"] + 4 and lo <= cy <= hi:
                # prefer the cell whose centre is closest
                d = (cx - (c["x0"] + c["x1"]) / 2) ** 2 + (cy - (c["y0"] + c["y1"]) / 2) ** 2
                if best is None or d < best[0]:
                    best = (d, k)
        if best:
            assign[best[1]].append(i)
            owner[i] = best[1]
    # pass 2: detached strokes that overlap a cell's ink box strongly
    for _ in range(2):
        boxes = {}
        for k, ids in assign.items():
            if not ids:
                continue
            boxes[k] = (min(stats[i, 0] for i in ids), min(stats[i, 1] for i in ids),
                        max(stats[i, 0] + stats[i, 2] for i in ids),
                        max(stats[i, 1] + stats[i, 3] for i in ids))
        for i in comps:
            if i in owner:
                continue
            if y_core is not None:
                cx, cy = cent[i]
                if not any(lo <= cy <= hi and c["x0"] - 4 <= cx <= c["x1"] + 4
                           for c, (lo, hi) in zip(cells, y_core)):
                    continue
            x0 = int(stats[i, 0]); y0 = int(stats[i, 1])
            x1 = x0 + int(stats[i, 2]); y1 = y0 + int(stats[i, 3])
            area = int(stats[i, 4])
            best = None
            for k, (bx0, by0, bx1, by1) in boxes.items():
                ix = max(0, min(x1, bx1 + 6) - max(x0, bx0 - 6))
                iy = max(0, min(y1, by1 + 6) - max(y0, by0 - 6))
                ov = ix * iy
                if ov > 0.5 * max(1, area) and (best is None or ov > best[0]):
                    best = (ov, k)
            if best:
                assign[best[1]].append(i)
                owner[i] = best[1]
    for k, c in enumerate(cells):
        ids = assign[k]
        if not ids:
            c["comp_ids"] = []
            c["bbox"] = None
            continue
        x0 = min(int(stats[i, 0]) for i in ids)
        y0 = min(int(stats[i, 1]) for i in ids)
        x1 = max(int(stats[i, 0] + stats[i, 2]) for i in ids)
        y1 = max(int(stats[i, 1] + stats[i, 3]) for i in ids)
        m = np.isin(lab[y0:y1, x0:x1], ids)
        c["comp_ids"] = ids
        c["bbox"] = (x0, y0, x1, y1)
        c["ink"] = float(m.mean())
    return lab


def draw_boxes(rgb: np.ndarray, cells: list[dict], out_path: str, scale: float = 0.4):
    img = rgb.copy()
    for c in cells:
        color = (0, 0, 255) if c.get("kind") == "big" else (0, 160, 0)
        cv2.rectangle(img, (c["x0"], c["y0"]), (c["x1"], c["y1"]), color, 2)
        cv2.putText(img, str(c.get("col", 0)), (c["x0"] + 2, c["y0"] + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    cv2.imwrite(out_path, cv2.cvtColor(small, cv2.COLOR_RGB2BGR))
