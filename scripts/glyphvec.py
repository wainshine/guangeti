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


def trace(ink: np.ndarray, turdsize: int = 8, alphamax: float = 1.0, opttol: float = 0.25):
    p = potrace.Bitmap(~ink).trace(turdsize=turdsize, alphamax=alphamax,
                                   opticurve=True, opttolerance=opttol)
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
