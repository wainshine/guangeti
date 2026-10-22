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


def vectorize(img: np.ndarray, scale: float, cx: float, cy: float) -> list:
    ink = binarize(img)
    cs = trace(ink)
    return to_em(cs, img.shape, scale, cx, cy)


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


def contour_bounds(contours):
    xs, ys = [], []
    for c in contours:
        xs.append(c["start"][0]); ys.append(c["start"][1])
        for s in c["segs"]:
            for i in range(1, len(s), 2):
                xs.append(s[i]); ys.append(s[i + 1])
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
