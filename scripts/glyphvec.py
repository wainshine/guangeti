"""Vectorise a glyph bitmap with potrace and normalise it to font units."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import potrace

EM = 1000


def clean_ink(mask: np.ndarray, min_area: int = 55, min_thick: float = 2.2) -> np.ndarray:
    """Drop specks and isolated hair-thin strokes (printed 圈点 arcs)."""
    m = mask.astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return mask
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    keep = np.zeros(n, bool)
    for i in range(1, n):
        a = stats[i, cv2.CC_STAT_AREA]
        if a < min_area:
            continue
        if float(dt[lab == i].max()) < min_thick:
            continue
        keep[i] = True
    return keep[lab]


def denoise_mask(ink: np.ndarray, rel: float = 0.0025, min_px: int = 40,
                 hole_rel: float = 0.002, hole_px: int = 50) -> np.ndarray:
    """Drop paper speckles and fill pinholes before tracing.

    A 300 dpi scan of a Ming manuscript carries dust, paper fibre and ink spatter;
    `clean_ink` only removes components that are both small and thin.  Those specks
    become separate contours (or ragged edges) in the font, which is exactly what
    makes the shipped glyphs look scratched at display sizes.  Thresholds are
    relative to the glyph's own ink area so they scale from 150 to 512 px.
    """
    m = ink.astype(np.uint8)
    area = int(m.sum())
    if area < 200:
        return ink
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    amin = max(min_px, int(rel * area))
    keep = np.zeros(n, bool)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= amin:
            keep[i] = True
    m = keep[lab].astype(np.uint8)
    # fill pinholes that do not touch the crop border
    inv = (1 - m).astype(np.uint8)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(inv, 8)
    hmax = max(hole_px, int(hole_rel * area))
    out = m.copy()
    H, W = m.shape
    for i in range(1, n2):
        x, y, w, h, a = st2[i]
        if a <= hmax and x > 0 and y > 0 and x + w < W and y + h < H:
            out[lab2 == i] = 1
    # one median pass removes the 1-px ragged edge left by thresholding
    out = (cv2.medianBlur(out * 255, 3) > 127).astype(np.uint8)
    return out.astype(bool)


def _hole_count(m: np.ndarray) -> int:
    cc = cv2.findContours(m.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    h = cc[-1]
    return 0 if h is None else sum(1 for x in h[0] if x[3] != -1)


def clamp_em_bbox(contours, maxw: float = 1000.0, maxh: float = 1000.0):
    """Scale a glyph down if its outline leaves the 1000-unit em box.

    A few real samples lean so far that the normalised outline is 1-2% taller than the
    em; most rasterisers clip that.  Scaling about the bbox centre keeps the glyph's
    visual position while bringing it back inside the box.
    """
    xs, ys = [], []
    for c in contours:
        xs.append(c["start"][0]); ys.append(c["start"][1])
        for sg in c["segs"]:
            xs += [sg[1], sg[-2]]; ys += [sg[2], sg[-1]]
    if not xs:
        return contours
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = x1 - x0, y1 - y0
    if w <= maxw and h <= maxh:
        return contours
    k = min(maxw / max(1e-6, w), maxh / max(1e-6, h))
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    out = []
    for c in contours:
        c2 = {"start": [cx + (c["start"][0] - cx) * k, cy + (c["start"][1] - cy) * k],
              "segs": []}
        for sg in c["segs"]:
            if sg[0] == "L":
                c2["segs"].append(["L", cx + (sg[1] - cx) * k, cy + (sg[2] - cy) * k])
            else:
                c2["segs"].append([sg[0],
                                   cx + (sg[1] - cx) * k, cy + (sg[2] - cy) * k,
                                   cx + (sg[3] - cx) * k, cy + (sg[4] - cy) * k,
                                   cx + (sg[5] - cx) * k, cy + (sg[6] - cy) * k])
        out.append(c2)
    return out


def adjust_mask_area(ink: np.ndarray, target_area: float, max_iter: int = 12,
                     stats: dict | None = None, supersample: int = 2) -> np.ndarray:
    """Nudge a glyph's stroke width so its ink area hits `target_area` (in px).

    The 大典 was copied by many hands; stroke weight varies by page by up to 2x.  A font
    assembled from one sample per character inherits that patchwork, which is the most
    visible defect at display sizes.  The adjustment is a sub-pixel dilation/erosion via
    the distance transform, so the glyph's shape and bbox barely move.  Iterated because
    the boundary-pixel count overestimates the perimeter of a stroke band.
    """
    def _stop(reason, it):
        if stats is not None:
            stats["stop"] = reason
            stats["iters"] = it

    if int(ink.sum()) < 200 or target_area <= 0:
        _stop("too_small", 0)
        return ink
    ss = max(1, int(supersample))
    if ss > 1:
        h, w = ink.shape
        m = (cv2.resize(ink.astype(np.uint8), (w * ss, h * ss),
                        interpolation=cv2.INTER_NEAREST) > 0).astype(np.uint8)
        target_area = target_area * ss * ss
    else:
        m = ink.astype(np.uint8)
    h0 = _hole_count(m)
    prev = m.copy()
    clamped = False
    for _it in range(max_iter):
        area = int(m.sum())
        if abs(area - target_area) / max(1.0, target_area) < 0.04:
            _stop("tol", _it + 1)
            break
        er = cv2.erode(m, np.ones((3, 3), np.uint8))
        perim = max(1, int((m & (1 - er)).sum()))
        delta = (float(target_area) - area) / perim
        if abs(delta) > 5.0:
            clamped = True
        delta = max(-5.0, min(5.0, delta))
        if abs(delta) < 0.05:
            _stop("clamped" if clamped else "small_delta", _it + 1)
            break
        if delta > 0:
            dto = cv2.distanceTransform((1 - m).astype(np.uint8), cv2.DIST_L2, 5)
            m = ((m > 0) | (dto <= delta)).astype(np.uint8)
        else:
            dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
            m = ((m > 0) & (dt > 1.0 - delta)).astype(np.uint8)
        # never trade a counter for weight: 四/園/因/圈 are common and a solid 四 is a
        # visible defect.  If this step closed a hole, stop and keep the previous mask.
        if _hole_count(m) < h0:
            m = prev
            _stop("hole", _it + 1)
            break
        prev = m.copy()
    else:
        _stop("clamped" if clamped else "max_iter", max_iter)
    if stats is not None and "stop" not in stats:
        stats["stop"] = "tol"
        stats["iters"] = max_iter
    if ss > 1:
        h, w = ink.shape
        small = cv2.resize(m.astype(np.uint8), (w, h), interpolation=cv2.INTER_AREA) >= 0.5
        return small
    return m.astype(bool)


def binarize(img: np.ndarray) -> np.ndarray:
    """Return a boolean ink mask from a grayscale glyph crop."""
    img = cv2.medianBlur(img, 3)
    thr, _ = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thr = min(max(thr, 120), 200)
    ink = img < thr
    # drop specks and isolated neighbour fragments
    n, lab, stats, cent = cv2.connectedComponentsWithStats(ink.astype(np.uint8), 8)
    keep = np.zeros(n, bool)
    h, w = ink.shape
    main = None
    if n > 1:
        areas = stats[1:, cv2.CC_STAT_AREA]
        main = 1 + int(np.argmax(areas))
    for i in range(1, n):
        x, y, ww, hh, a = stats[i]
        if a < 25:
            continue
        cx, cy = cent[i]
        # ignore small blobs hugging the crop border (neighbour strokes)
        border = cx < w * 0.04 or cx > w * 0.96 or cy < h * 0.04 or cy > h * 0.96
        if border and a < 400 and i != main:
            continue
        keep[i] = True
    return keep[lab]


def trace(ink: np.ndarray, turdsize: int = 2, alphamax: float = 1.0, opttol: float = 0.25):
    """Vectorise a binary mask.

    turdsize=2 (was 8): small counters (e.g. 年's 4px hole) were being dropped by
    potrace's speck filter — see audit P0 layer 3.
    """
    try:
        p = potrace.Bitmap(~ink).trace(turdsize=turdsize, alphamax=alphamax,
                                       opticurve=True, opttolerance=opttol)
    except ValueError:
        # potrace's curve optimiser raises on a degenerate sliver (seen on a few 大典
        # glyphs after the weight adjustment); fall back to polygons rather than
        # dropping the whole generation run
        p = potrace.Bitmap(~ink).trace(turdsize=turdsize, alphamax=alphamax,
                                       opticurve=False, opttolerance=opttol)
    H = ink.shape[0]
    contours = []
    for curve in p:
        segs = []
        for seg in curve:
            if type(seg).__name__ == "CornerSegment":
                segs.append(("L", seg.end_point.x, seg.end_point.y))
            else:
                segs.append(("C", seg.c1.x, seg.c1.y, seg.c2.x, seg.c2.y,
                             seg.end_point.x, seg.end_point.y))
        if len(segs) >= 3:
            contours.append(dict(start=(curve.start_point.x, curve.start_point.y), segs=segs))
    return contours


def to_em(contours, scale, page_x0, page_y0, slot_cx, slot_cy, em_cx=500.0, em_cy=380.0):
    """Map potrace pixel coords (crop-relative, y down) to font units (y up)."""
    def mx(px):
        return (page_x0 + px - slot_cx) * scale + em_cx

    def my(py):
        return (slot_cy - (page_y0 + py)) * scale + em_cy

    out = []
    for c in contours:
        sx, sy = c["start"]
        segs = []
        for s in c["segs"]:
            if s[0] == "L":
                segs.append(("L", mx(s[1]), my(s[2])))
            else:
                segs.append(("C", mx(s[1]), my(s[2]), mx(s[3]), my(s[4]), mx(s[5]), my(s[6])))
        out.append(dict(start=(mx(sx), my(sy)), segs=segs))
    return out


@dataclass
class GlyphSpec:
    contours: list
    box: tuple


def vectorize(img: np.ndarray, scale: float, page_x0: float, page_y0: float,
              slot_cx: float, slot_cy: float) -> list:
    """Deprecated: the live path is generate_lib.raster_to_em; kept for reference."""
    ink = binarize(img)
    cs = trace(ink)
    return to_em(cs, scale, page_x0, page_y0, slot_cx, slot_cy)


_WK_INK = {}


def wenkai_ink_256(ch: str) -> int:
    """Ink area of the same character in WenKai, rendered at 256 px (cached)."""
    if ch in _WK_INK:
        return _WK_INK[ch]
    from PIL import Image, ImageDraw, ImageFont
    from pathlib import Path
    f = ImageFont.truetype(str(Path(__file__).resolve().parents[1]
                               / "data/base/LXGWWenKai-Regular.ttf"), 256)
    im = Image.new("L", (256, 256), 0)
    ImageDraw.Draw(im).text((0, 880 * 256 / 1000.0), ch, fill=255, font=f, anchor="ls")
    n = int((np.array(im) > 127).sum())
    _WK_INK[ch] = n
    return n


def target_ink_256(ch: str, a: float = 38.7258, exp: float = 0.5701) -> float:
    """C-corpus ink target at 256 px: ink = a * wenkai_ink^exp (see EXPERIMENTS-C E13)."""
    w = wenkai_ink_256(ch)
    if w < 80:
        return 0.0
    return float(a * (w ** exp))


_BASE = None


def base_bounds(char: str):
    """Ink bbox of a character in the base (LXGW WenKai) font, in em units."""
    global _BASE
    if _BASE is None:
        from fontTools.ttLib import TTFont
        from fontTools.pens.boundsPen import BoundsPen
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / "data" / "base" / "LXGWWenKai-Regular.ttf"
        f = TTFont(str(p))
        _BASE = (f.getGlyphSet(), f.getBestCmap())
    gs, cmap = _BASE
    cp = ord(char)
    if cp not in cmap:
        return None
    from fontTools.pens.boundsPen import BoundsPen
    bp = BoundsPen(gs)
    gs[cmap[cp]].draw(bp)
    return bp.bounds


def _cubic_axis(p0, p1, p2, p3):
    """Extrema of a 1-D cubic Bezier (returns list of values incl. endpoints)."""
    A = -p0 + 3 * p1 - 3 * p2 + p3
    B = 2 * (p0 - 2 * p1 + p2)
    C = p1 - p0
    ts = [0.0, 1.0]
    if abs(A) < 1e-12:
        if abs(B) > 1e-12:
            t = -C / B
            if 0 < t < 1:
                ts.append(t)
    else:
        disc = B * B - 4 * A * C
        if disc >= 0:
            r = disc ** 0.5
            for t in ((-B + r) / (2 * A), (-B - r) / (2 * A)):
                if 0 < t < 1:
                    ts.append(t)
    out = []
    for t in ts:
        u = 1 - t
        out.append(u ** 3 * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t ** 3 * p3)
    return out


def contour_bounds(contours):
    """Exact bbox of cubic outlines (control points alone overestimate a Bezier)."""
    xs, ys = [], []
    for c in contours:
        x0, y0 = c["start"]
        xs.append(x0); ys.append(y0)
        px, py = x0, y0
        for s in c["segs"]:
            if s[0] == "L":
                xs.append(s[1]); ys.append(s[2])
                px, py = s[1], s[2]
            else:
                c1x, c1y, c2x, c2y, ex, ey = s[1:]
                xs.extend(_cubic_axis(px, c1x, c2x, ex))
                ys.extend(_cubic_axis(py, c1y, c2y, ey))
                px, py = ex, ey
    return (min(xs), min(ys), max(xs), max(ys))


def transform(contours, sx, sy, dx, dy):
    out = []
    for c in contours:
        segs = []
        for s in c["segs"]:
            vals = list(s[1:])
            segs.append((s[0],) + tuple(v * (sx if i % 2 == 0 else sy) + (dx if i % 2 == 0 else dy)
                                        for i, v in enumerate(vals)))
        out.append(dict(start=(c["start"][0] * sx + dx, c["start"][1] * sy + dy), segs=segs))
    return out


def normalize_to_base(contours, char, blend=0.8, min_scale=0.6, max_scale=1.7):
    """Blend the glyph bbox toward the base font's bbox for the same character."""
    bb = base_bounds(char)
    if bb is None:
        return contours
    x0, y0, x1, y1 = contour_bounds(contours)
    w, h = max(1e-3, x1 - x0), max(1e-3, y1 - y0)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    sx = (blend * tw + (1 - blend) * w) / w
    sy = (blend * th + (1 - blend) * h) / h
    sx = min(max(sx, min_scale), max_scale)
    sy = min(max(sy, min_scale), max_scale)
    # align bbox centres
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    tcx, tcy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    dx = tcx - cx * sx
    dy = tcy - cy * sy
    return transform(contours, sx, sy, dx, dy)
