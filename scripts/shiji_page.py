"""Page geometry for the 《史記》 manuscript scan (NUS 藏 傳姜立綱抄本).

The scan is a *bound* volume photographed as a spread: two leaves, a crease at the
fold, each leaf with its own skew, and the paper near the spine sitting lower than the
outer edge.  `pageproc.analyze_page` only does one global rotation, which cannot fix
two leaves at once, and its column model assumes axis-aligned text columns.

This module supplies the missing first stage:

  paper_mask   isolate the bright leaf area (the surround is dark grey)
  fold_x       locate the crease that splits the spread into leaves
  ink_mask     paper-relative, red 句讀 marks removed (they ARE red in this scan)
  column_runs  vertical text columns from the ink coverage profile
  centerlines  per-column ink midline c_i(y)
  warp_maps    displacement field that maps every column onto a vertical line
               (this removes both the per-leaf skew and the residual curvature)

Everything downstream (segmentation, cell cutting) then works on an image whose
columns are straight and vertical.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

PAPER_WHITE = 245


# ----------------------------------------------------------------- basic loading
def load_page(doc, page_no: int, dpi: int = 300) -> np.ndarray:
    pix = doc[page_no].get_pixmap(dpi=dpi)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()


# ----------------------------------------------------------------- paper & fold
def surround_mask(gray: np.ndarray, dark: int = 140) -> np.ndarray:
    """The dark surround, found by flooding inward from the frame border.

    Unlike a plain brightness threshold this never punches holes in the leaf: foxing
    stains and the crease are enclosed by paper, so the flood cannot reach them.
    """
    h, w = gray.shape
    free = (gray < dark).astype(np.uint8)
    m = np.zeros((h + 2, w + 2), np.uint8)
    ff = free.copy()
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)] + \
                [(x, 0) for x in range(0, w, 50)] + [(x, h - 1) for x in range(0, w, 50)] + \
                [(0, y) for y in range(0, h, 50)] + [(w - 1, y) for y in range(0, h, 50)]:
        if free[seed[1], seed[0]]:
            cv2.floodFill(ff, m, seed, 2)
    return ff == 2


def _fill_holes(mask: np.ndarray) -> np.ndarray:
    """Fill every enclosed hole (dense ink blobs are 60x100 px, larger than any kernel).

    Only the four corners seed the flood fill (audit 3-10): when the paper touches an
    edge the background is connected around it, so the corners still reach it; but if a
    crop ever loses all four corners this would fill the whole frame.  "surround" mode
    below is the safer caller-side contract.
    """
    m = mask.astype(np.uint8)
    inv = (1 - m).astype(np.uint8)
    h, w = inv.shape
    ff = inv.copy()
    ffmask = np.zeros((h + 2, w + 2), np.uint8)
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if ff[seed[1], seed[0]]:
            cv2.floodFill(ff, ffmask, seed, 2)
    holes = (inv == 1) & (ff != 2)
    return (mask | holes)


def paper_mask(gray: np.ndarray, close: int = 61) -> np.ndarray:
    """Bright region = the leaf area; enclosed dark blobs (ink, stains) count as paper."""
    br = (gray > 140).astype(np.uint8)
    br = cv2.morphologyEx(br, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    br = cv2.morphologyEx(br, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(br, 8)
    if n >= 2:
        i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        pm = (lab == i)
    else:
        pm = np.ones_like(gray, bool)
    return _fill_holes(pm)


def paper_box(pm: np.ndarray):
    ys = np.flatnonzero(pm.any(1))
    xs = np.flatnonzero(pm.any(0))
    return int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1


def fold_x(gray: np.ndarray, pm: np.ndarray, dark_ratio: float = 0.985):
    """x of the crease, or None when the page is a single leaf.

    The crease is a narrow band where *even the brightest* pixels are darker than the
    paper, so the 90th percentile per column dips there.  A text column cannot fake
    that: its brightest pixels are still bare paper.
    """
    x0, y0, x1, y1 = paper_box(pm)
    if x1 - x0 < gray.shape[1] * 0.55:
        return None, 0.0                      # single leaf
    seg = gray[y0:y1, x0:x1].astype(np.float32)
    sub = pm[y0:y1, x0:x1]
    seg = np.where(sub, seg, 255.0)           # the dark surround must not lower p90
    prof = np.percentile(seg, 90, axis=0)
    prof = np.convolve(prof, np.ones(9) / 9, "same")
    xa, xb = int((x1 - x0) * 0.28), int((x1 - x0) * 0.72)
    k = xa + int(np.argmin(prof[xa:xb]))
    typ = float(np.median(prof[max(0, xa - 200):min(len(prof), xb + 200)]))
    depth = float(prof[k]) / max(1.0, typ)
    return (x0 + k, depth) if depth < dark_ratio else (None, depth)


def leaf_ranges(pm: np.ndarray, fold, min_frac: float = 0.18):
    """x ranges of the leaves (1 or 2), clipped to the paper."""
    x0, y0, x1, y1 = paper_box(pm)
    if fold is None or not (x0 + (x1 - x0) * 0.2 < fold < x1 - (x1 - x0) * 0.2):
        return [(x0, x1)]
    return [(x0, int(fold)), (int(fold), x1)]


# ----------------------------------------------------------------- ink
def _nanpct(a, q, axis, fill):
    """nanpercentile with the all-NaN slices filled (they only occur outside the paper)."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        out = np.nanpercentile(a, q, axis=axis)
    return np.nan_to_num(out, nan=fill)


def flatten(gray: np.ndarray, pm: np.ndarray, target: float = 230.0, sigma: int = 25) -> np.ndarray:
    """Remove illumination gradients and the fold shadow (multiplicative background)."""
    g = np.where(pm, gray, np.nan).astype(np.float32)
    bx = _nanpct(g, 80, 0, target)
    by = _nanpct(g, 80, 1, target)
    k = 2 * sigma + 1
    bx = np.convolve(np.pad(bx, (sigma, sigma), mode="edge"), np.ones(k) / k, "same")[sigma:sigma + len(bx)]
    by = np.convolve(np.pad(by, (sigma, sigma), mode="edge"), np.ones(k) / k, "same")[sigma:sigma + len(by)]
    bg = np.outer(by, bx) / max(1.0, target)
    bg = np.maximum(bg, 40.0)
    out = gray.astype(np.float32) * (target / bg)
    return np.clip(out, 0, 255).astype(np.uint8)


def ink_mask(rgb: np.ndarray, gray_flat: np.ndarray, pm: np.ndarray,
             thr_frac: float = 0.45, red_thr: int = 24) -> np.ndarray:
    """Binary ink.  Paper-relative threshold; red 句讀 marks dropped by colour."""
    vals = gray_flat[pm]
    lo = float(np.percentile(vals, 2))
    med = float(np.median(vals))
    thr = lo + thr_frac * (med - lo)
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    red = (r - g) > red_thr
    red = cv2.dilate(red.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    return (gray_flat < thr) & pm & (~red)


# ----------------------------------------------------------------- columns
def column_runs(ink: np.ndarray, x0: int, x1: int, frac: float = 0.05, min_w: int = 40):
    """Vertical text columns as (a, b) x-ranges inside [x0, x1)."""
    sub = ink[:, x0:x1]
    h = sub.shape[0]
    cov = np.convolve(sub.sum(0).astype(np.float32) / h, np.ones(9) / 9, "same")
    on = cov > frac
    if not on.any():
        return []
    d = np.diff(on.astype(np.int8))
    s = list(np.flatnonzero(d == 1) + 1)
    e = list(np.flatnonzero(d == -1) + 1)
    if on[0]:
        s = [0] + s
    if on[-1]:
        e = e + [len(on)]
    runs = [(int(a) + x0, int(b) + x0) for a, b in zip(s, e) if b - a >= min_w]
    if not runs:
        return []
    w = np.array([b - a for a, b in runs], float)
    med = float(np.median(w))
    return [(a, b) for a, b in runs if (b - a) >= med * 0.55]


def keep_text_columns(runs, ink: np.ndarray):
    """Drop the page-edge shadow strips: their ink coverage is full-height."""
    keep = []
    for a, b in runs:
        sub = ink[:, a:b]
        cov = sub.sum(1) > 0
        # a text column has white gaps (between characters); a shadow strip does not
        runs_of_white = 0
        d = np.diff(cov.astype(np.int8))
        runs_of_white = int((d == 1).sum())
        if runs_of_white >= 3 or b - a < 60:
            keep.append((a, b))
    return keep if keep else runs


def _smooth_valid(v: np.ndarray, ok: np.ndarray, win: int) -> np.ndarray:
    """Interpolate NaNs then box-smooth, keeping support where data exists."""
    idx = np.arange(len(v))
    out = np.interp(idx, idx[ok], v[ok])
    k = max(1, int(win) | 1)
    out = np.convolve(np.pad(out, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "same")[k // 2:k // 2 + len(v)]
    return out


def centerlines(ink: np.ndarray, runs, win: int, min_rows: int = 120):
    """Per-column ink midline c(y), smoothed over `win` rows.

    Returns list of dict(x0, x1, xc, c, ok, n) with c the smoothed midline (full page
    height) and ok the rows that actually carried ink.
    """
    H = ink.shape[0]
    out = []
    for a, b in runs:
        sub = ink[:, a:b]
        c = np.full(H, np.nan)
        for y in range(H):
            xs = np.flatnonzero(sub[y])
            if len(xs) >= 3:
                c[y] = (xs[0] + xs[-1]) * 0.5 + a
        ok = ~np.isnan(c)
        if ok.sum() < min_rows:
            continue
        cs = _smooth_valid(np.nan_to_num(c), ok, win)
        out.append(dict(x0=a, x1=b, xc=(a + b) / 2.0, c=cs, ok=ok, n=int(ok.sum())))
    return out


def col_line_fit(col):
    """Slope (deg) and residual (px, median |dev from line|) of a column midline."""
    ok = col["ok"]
    y = np.flatnonzero(ok).astype(np.float64)
    v = col["c"][ok]
    if len(y) < 50:
        return None
    A = np.polyfit(y, v, 1)
    res = v - np.polyval(A, y)
    return dict(deg=float(np.degrees(np.arctan(A[0]))),
                res_med=float(np.median(np.abs(res))),
                res_p90=float(np.percentile(np.abs(res), 90)),
                slope=float(A[0]))


def straightness(cols, win_name=""):
    """Aggregate straightness of a set of columns."""
    rows = [col_line_fit(c) for c in cols]
    rows = [r for r in rows if r]
    if not rows:
        return dict(n=0)
    deg = np.array([r["deg"] for r in rows])
    rm = np.array([r["res_med"] for r in rows])
    return dict(n=len(rows), deg_med=float(np.median(deg)), deg_abs_med=float(np.median(np.abs(deg))),
                res_med=float(np.median(rm)), res_p90=float(np.percentile(rm, 90)))


# ----------------------------------------------------------------- warp
def warp_maps(cols, shape, sigma_x: int = 9, max_shift: float = 0.22):
    """Displacement field (mapx, mapy) that straightens every column.

    dx is constant inside a column (so glyphs are not sheared) and interpolated across
    the white gaps, then smoothed a little to avoid kinks at column edges.
    """
    H, W = shape
    cols = [c for c in cols if col_line_fit(c)]
    if len(cols) < 2:
        return None, None, 0.0
    cols = sorted(cols, key=lambda c: c["xc"])
    centers = np.array([c["xc"] for c in cols])
    gaps = np.diff(centers)
    dxcol = []
    for k, c in enumerate(cols):
        ok = c["ok"]
        tgt = float(np.median(c["c"][ok]))
        d = c["c"] - tgt
        # never move a column so far that it can touch its neighbour
        nb = []
        if k > 0:
            nb.append(gaps[k - 1])
        if k < len(gaps):
            nb.append(gaps[k])
        lim = 0.30 * min(nb) if nb else 60.0
        dxcol.append(np.clip(d, -lim, lim))
    dxcol = np.stack(dxcol)

    xs = np.array([c["xc"] for c in cols])
    xx = np.arange(W, dtype=np.float32)
    idx = np.searchsorted(xs, xx).clip(1, len(xs) - 1)
    x_lo, x_hi = xs[idx - 1], xs[idx]
    t = ((xx - x_lo) / np.maximum(1e-6, x_hi - x_lo)).clip(0, 1)[None, :]
    t = np.where(xx[None, :] <= xs[0], 0.0, t)
    t = np.where(xx[None, :] >= xs[-1], 1.0, t)
    a = dxcol[idx - 1].T                      # (H, W)
    b = dxcol[idx].T
    amp = (a * (1 - t) + b * t).astype(np.float32)
    # inside a column, force the constant value again (no interpolation across glyphs)
    for k, c in enumerate(cols):
        pad = 6
        a0 = max(0, c["x0"] - pad)
        a1 = min(W, c["x1"] + pad)
        amp[:, a0:a1] = dxcol[k][:, None]
    k = 2 * sigma_x + 1
    amp = cv2.GaussianBlur(amp, (k, k), sigma_x, borderType=cv2.BORDER_REPLICATE)
    # dst(x, y) = src(x + amp, y): sampling to the right of x pulls a midline that sits
    # at c(y) into c(y) + amp, i.e. the content shifts RIGHT by amp.  (The sign was
    # inverted once in development and doubled the residual instead of removing it;
    # audit 3-10 flagged the comment, the formula itself was correct.)
    mapx = (xx[None, :] + amp).astype(np.float32)
    mapy = np.repeat(np.arange(H, dtype=np.float32)[:, None], W, axis=1)
    return mapx, mapy, float(np.abs(dxcol).max())


def apply_warp(rgb: np.ndarray, mapx, mapy, pm: np.ndarray) -> np.ndarray:
    out = cv2.remap(rgb, mapx, mapy, interpolation=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE)
    if pm is not None:
        out = np.where(pm[:, :, None], out, PAPER_WHITE).astype(np.uint8)
    return out


def dewarp_page(rgb: np.ndarray, win: int = 0, sigma_x: int = 9, verbose: bool = False) -> dict:
    """Full rectification: returns the warped image plus the measurements behind it."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    pm = paper_mask(gray)
    fold, fold_depth = fold_x(gray, pm)
    leaves = leaf_ranges(pm, fold)
    H, W = gray.shape
    if not win:
        win = max(31, int(H * 0.09) | 1)     # ~2 character pitches at 300 dpi
    gflat = flatten(gray, pm)
    ink = ink_mask(rgb, gflat, pm)

    all_cols = []
    before = []
    for (x0, x1) in leaves:
        runs = column_runs(ink, x0 + 2, x1 - 2)
        runs = keep_text_columns(runs, ink)
        cols = centerlines(ink, runs, win)
        all_cols.extend(cols)
        st = straightness(cols)
        if st.get("n"):
            before.append(dict(leaf=[int(x0), int(x1)], **st))

    mapx, mapy, maxdx = warp_maps(all_cols, (H, W), sigma_x=sigma_x)
    info = dict(fold=(None if fold is None else int(fold)), fold_depth=round(float(fold_depth), 4),
                leaves=[[int(a), int(b)] for a, b in leaves], win=int(win),
                n_cols=len(all_cols), max_shift_px=round(maxdx, 2), before=before)
    if mapx is None:
        return dict(image=rgb, info=info, pm=pm)

    warped = apply_warp(rgb, mapx, mapy, pm)
    # measure again on the rectified image
    g2 = cv2.cvtColor(warped, cv2.COLOR_RGB2GRAY)
    ink2 = ink_mask(warped, g2, pm)
    after = []
    for (x0, x1) in leaves:
        runs = column_runs(ink2, x0 + 2, x1 - 2)
        runs = keep_text_columns(runs, ink2)
        cols = centerlines(ink2, runs, win)
        st = straightness(cols)
        if st.get("n"):
            # distance to the fold, to split near-spine from page-edge columns
            if fold is not None:
                d = [abs(c["xc"] - fold) for c in cols]
                res = [col_line_fit(c)["res_med"] for c in cols]
                near = [r for r, dd in zip(res, d) if dd < 300]
                far = [r for r, dd in zip(res, d) if dd > 600]
                st["near"] = float(np.median(near)) if near else None
                st["far"] = float(np.median(far)) if far else None
            else:
                st["near"] = st["far"] = None
            after.append(dict(leaf=[int(x0), int(x1)], **st))
    info["after"] = after
    return dict(image=warped, info=info, pm=pm)


# ---------------------------------------------------------------- counter repair
def _hole_count(m: np.ndarray) -> int:
    out = cv2.findContours(m.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    hier = out[-1]
    if hier is None:
        return 0
    return int(sum(1 for h in hier[0] if h[3] != -1))


_WK_FONT: dict = {}


def wk_holes(ch: str, size: int = 256) -> int:
    """How many counters WenKai draws for this character (the reference count)."""
    from PIL import Image, ImageDraw, ImageFont
    if size not in _WK_FONT:
        f = ImageFont.truetype(str(Path(__file__).resolve().parents[1]
                                   / "data/base/LXGWWenKai-Regular.ttf"), size)
        _WK_FONT[size] = f
    im = Image.new("L", (size, size), 0)
    ImageDraw.Draw(im).text((size // 2, int(0.88 * size)), ch, fill=255, font=_WK_FONT[size],
                            anchor="ms")
    return _hole_count(np.array(im) > 127)


def _holes_at(m: np.ndarray, size: int = 256) -> int:
    """Hole count in the *rendering* space the audit measures at (256 px)."""
    if m.shape[0] != size:
        m = cv2.resize(m.astype(np.uint8), (size, size), interpolation=cv2.INTER_NEAREST)
    return _hole_count(m > 0)


def repair_counters(m: np.ndarray, ch: str, base_close: int = 7,
                    extra=(11, 15, 19, 24, 32), max_ink_gain: float = 0.08):
    """Close the ink, escalating, until the counter that WenKai draws reappears.

    The scan's strokes are grey at the edges, so a 1-2 px gap lets a counter leak to
    the outside and potrace then sees no hole at all (audit rev2 P0 / rev3 2-3).
    A fixed kernel fixes most glyphs but not all; this retries with a bigger kernel
    only for the ones that still have no counter, and gives up if the ink grows by
    more than `max_ink_gain` (i.e. strokes would visibly thicken).

    The escalation range matters: at 512 px, `四` needs 15, `年` needs 11, `国` needs 24
    and `园` needs 32 (audit 2026-10-27 found `国` still solid in the shipped font because
    the old list stopped at 15).  The ink budget is what keeps that safe: 24 costs +3.7%
    on `国`, 32 costs +6.2% on `园`.
    """
    want = wk_holes(ch, 256)
    if want == 0 or _holes_at(m) >= want:
        return m, 0
    base = int(m.sum())
    best_m, best_k = m, 0
    for k in (base_close, *extra):
        if k <= 0:
            continue
        kk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        m2 = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, kk) > 0
        if (m2.sum() - base) / max(1, base) > max_ink_gain:
            break
        got = _holes_at(m2)
        if got >= want:
            return np.asarray(m2, dtype=bool), int(k)
        if got > _holes_at(best_m):
            best_m, best_k = m2, k
    # no kernel reached WenKai's count; keep the best one found (never worse than input)
    return (np.asarray(best_m, dtype=bool), int(best_k)) if best_k else (m, 0)
