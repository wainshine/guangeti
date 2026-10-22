"""Skeleton-based parametric brush for CJK glyph synthesis.

Pipeline
--------
mask → skeleton (pruned) → stroke graph (nodes/edges) → per-point frames
(orientation, radius, distance-to-end, distance-to-junction) → width model →
variable-width rendering → binary mask.

All fonts used here must be OFL/Apache/UFL (see AGENTS.md).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import convolve
from skimage.morphology import skeletonize

SIZE = 256
NB8 = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], np.int32)


# ---------------------------------------------------------------- rendering
def render_char(ch: str, font_path: str, size: int = SIZE) -> np.ndarray:
    """Render one character into the *em frame* used by the whole pipeline
    (canvas = em 0..1000 x 880..-120, baseline at 0.88*size)."""
    font = _font_cache(font_path, size)
    img = Image.new("L", (size, size), 0)
    ImageDraw.Draw(img).text((0, 880 * size / 1000.0), ch, fill=255, font=font, anchor="ls")
    return np.array(img) > 127


_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _font_cache(path: str, px: int) -> ImageFont.FreeTypeFont:
    key = (path, px)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(path, px)
    return _FONT_CACHE[key]


# ---------------------------------------------------------------- skeleton
def _neighbour_count(sk: np.ndarray) -> np.ndarray:
    return convolve(sk.astype(np.int32), NB8, mode="constant")


def prune_spurs(sk: np.ndarray, max_len: int = 6, rounds: int = 8) -> np.ndarray:
    """Remove short dead-end branches (spurs) that skeletonisation creates."""
    sk = sk.copy()
    for _ in range(rounds):
        changed = False
        nb = _neighbour_count(sk)
        ends = np.argwhere(sk & (nb == 1))
        for y, x in ends:
            if not sk[y, x]:
                continue
            path = [(y, x)]
            py, px = -1, -1
            cy, cx = y, x
            ok = False
            for _ in range(max_len + 1):
                nbrs = [(cy + dy, cx + dx)
                        for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                        if (dy or dx)
                        and 0 <= cy + dy < sk.shape[0]
                        and 0 <= cx + dx < sk.shape[1]
                        and sk[cy + dy, cx + dx]]
                nbrs = [p for p in nbrs if p != (py, px)]
                if len(nbrs) == 0:
                    ok = True          # isolated stub
                    break
                if len(nbrs) > 1:      # reached a junction
                    break
                py, px = cy, cx
                cy, cx = nbrs[0]
                path.append((cy, cx))
            if ok or len(path) <= max_len:
                if not (sk[cy, cx] and _neighbour_count(sk)[cy, cx] >= 3):
                    continue
                for (yy, xx) in path[:-1]:
                    sk[yy, xx] = False
                changed = True
        if not changed:
            break
    return sk


def skeleton_of(mask: np.ndarray, prune: bool = True, max_spur: int = 6) -> np.ndarray:
    sk = skeletonize(mask)
    if prune:
        sk = prune_spurs(sk, max_len=max_spur)
        # pruning can leave 1-px islands; drop tiny components
        n, lab, st, _ = cv2.connectedComponentsWithStats(sk.astype(np.uint8), 8)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < 8:
                sk[lab == i] = False
    return sk


# ---------------------------------------------------------------- stroke graph
def stroke_edges(sk: np.ndarray) -> list[dict]:
    """Split a skeleton into polylines between nodes (endpoints / junctions)."""
    h, w = sk.shape
    nb = _neighbour_count(sk)
    is_node = sk & (nb != 2)
    visited = np.zeros_like(sk, bool)
    edges: list[dict] = []

    def nbrs(y, x):
        out = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if not (dy or dx):
                    continue
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and sk[yy, xx]:
                    out.append((yy, xx))
        return out

    starts = list(map(tuple, np.argwhere(is_node)))
    for sy, sx in starts:
        for ny, nx in nbrs(sy, sx):
            if visited[ny, nx]:
                continue
            path = [(sy, sx), (ny, nx)]
            visited[ny, nx] = True
            py, px, cy, cx = sy, sx, ny, nx
            closed = False
            while not is_node[cy, cx]:
                nxt = [p for p in nbrs(cy, cx) if p != (py, px)]
                if not nxt:
                    break
                if len(nxt) > 1:
                    break
                py, px = cy, cx
                cy, cx = nxt[0]
                if visited[cy, cx]:
                    closed = True
                    break
                visited[cy, cx] = True
                path.append((cy, cx))
            # a "node" is a skeleton pixel with degree != 2; only degree >= 3 is a
            # junction -- degree 1 is a free stroke end (was conflated before).
            edges.append({"pts": path,
                          "start_node": bool(nb[path[0][0], path[0][1]] >= 3),
                          "end_node": bool(nb[path[-1][0], path[-1][1]] >= 3),
                          "closed": closed})
    return [e for e in edges if len(e["pts"]) >= 2]


def _tangents(pts: np.ndarray, win: int = 3) -> np.ndarray:
    n = len(pts)
    t = np.zeros((n, 2), np.float32)
    for i in range(n):
        a = pts[max(0, i - win)]
        b = pts[min(n - 1, i + win)]
        d = b - a
        norm = np.linalg.norm(d) + 1e-6
        t[i] = d / norm
    return t


def edge_frames(edge: dict, dt: np.ndarray, size: int = SIZE) -> dict:
    pts = np.asarray(edge["pts"], np.float32)          # (y, x)
    n = len(pts)
    tan = _tangents(pts)                               # unit tangent in (y, x)
    # orientation: 1 = vertical stroke (tangent is (dy, dx); a vertical stroke
    # has a large dy component)
    vert = np.abs(tan[:, 0])
    idx = np.arange(n, dtype=np.float32)
    d_start = idx
    d_end = (n - 1) - idx
    d_near = np.minimum(d_start, d_end)
    is_junc_start = edge["start_node"]
    is_junc_end = edge["end_node"]
    # distance to junction along the polyline (inf if that end is a free end)
    dj = np.full(n, np.inf, np.float32)
    if is_junc_start:
        dj = np.minimum(dj, d_start)
    if is_junc_end:
        dj = np.minimum(dj, d_end)
    # distance to the nearest *free* end (junction ends do not count as stroke tips)
    d_free = np.full(n, np.inf, np.float32)
    if not is_junc_start:
        d_free = np.minimum(d_free, d_start)
    if not is_junc_end:
        d_free = np.minimum(d_free, d_end)
    ys = np.clip(pts[:, 0].astype(int), 0, size - 1)
    xs = np.clip(pts[:, 1].astype(int), 0, size - 1)
    r_obs = dt[ys, xs]
    return {"pts": pts, "vert": vert, "d_near": d_near, "d_free": d_free, "dj": dj,
            "len": n - 1, "r_obs": r_obs,
            "start_junction": is_junc_start, "end_junction": is_junc_end}


def glyph_frames(mask: np.ndarray, size: int = SIZE) -> list[dict]:
    sk = skeleton_of(mask)
    dt = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    return [edge_frames(e, dt, size) for e in stroke_edges(sk)]


# ---------------------------------------------------------------- width model
def model_radius(vert, d_free, dj, p) -> np.ndarray:
    """r = r0 * (1 + k*vert^pw) * (1 + be*exp(-(d_free/le)^2)) * (1 + bj*exp(-(dj/lj)^2))

    Free ends are *thicker* than stroke bodies in this woodblock print (顿笔),
    not thinner — measured on 150 real glyphs.
    """
    r0, k, pw, be, le, bj, lj = p
    orient = 1.0 + k * np.power(np.clip(vert, 0, 1), pw)
    end = 1.0 + be * np.where(np.isfinite(d_free), np.exp(-np.square(d_free / max(1e-3, le))), 0.0)
    jb = 1.0 + bj * np.where(np.isfinite(dj), np.exp(-np.square(dj / max(1e-3, lj))), 0.0)
    return r0 * orient * end * jb


def collect_fit_data(masks, stride: int = 3):
    vs, dfs, djs, rs = [], [], [], []
    for m in masks:
        for f in glyph_frames(m):
            n = len(f["pts"])
            if n < 4:
                continue
            vs.append(f["vert"][::stride])
            dfs.append(f["d_free"][::stride])
            djs.append(f["dj"][::stride])
            rs.append(f["r_obs"][::stride])
    return (np.concatenate(vs).astype(np.float64), np.concatenate(dfs).astype(np.float64),
            np.concatenate(djs).astype(np.float64), np.concatenate(rs).astype(np.float64))


def fit_width_model(v, d_free, dj, r, p0=(6.2, 0.25, 2.0, 0.35, 6.0, 0.10, 3.0)):
    from scipy.optimize import least_squares
    lo = [3.0, 0.0, 0.5, 0.0, 1.0, 0.0, 1.0]
    hi = [12.0, 1.2, 6.0, 1.0, 20.0, 0.5, 20.0]
    res = least_squares(lambda p: model_radius(v, d_free, dj, p) - r, np.array(p0, float),
                        bounds=(lo, hi), loss="soft_l1", f_scale=1.0, max_nfev=600)
    return res.x, float(np.sqrt(np.mean((model_radius(v, d_free, dj, res.x) - r) ** 2)))


def render_brushed(frames, params, size: int = SIZE, ss: int = 2) -> np.ndarray:
    """Render variable-width strokes from frames; ss = supersampling factor."""
    S = size * ss
    out = np.zeros((S, S), np.uint8)
    for f in frames:
        pts = f["pts"] * ss
        n = len(f["pts"])
        r = model_radius(f["vert"], f["d_free"], f["dj"], params) * ss
        for (y, x), rr in zip(pts, r):
            cv2.circle(out, (int(round(x)), int(round(y))), max(1, int(round(rr))), 1, -1,
                       lineType=cv2.LINE_8)
    return cv2.resize(out * 255, (size, size), interpolation=cv2.INTER_AREA) > 127


def brush_glyph(ch: str, font_path: str, params, size: int = SIZE) -> np.ndarray:
    m = render_char(ch, font_path, size)
    return render_brushed(glyph_frames(m, size), params, size)


def render_proportional(frames, scale: float = 1.28, be: float = 0.30, le: float = 0.18,
                        size: int = SIZE, ss: int = 2) -> np.ndarray:
    """Re-render strokes with radius proportional to the *source* local width.

    r(s) = dt_src(s) * scale * (1 + be * exp(-(u_free/le)^2))
    where u_free is the distance to the nearest free stroke end, normalised by
    half the stroke length (so le is scale-free).
    """
    out = np.zeros((size * ss, size * ss), np.uint8)
    for f in frames:
        pts = f["pts"] * ss
        n = len(f["pts"])
        half = max(1.0, (n - 1) / 2.0)
        u = np.where(np.isfinite(f["d_free"]), f["d_free"] / half, 1.0)
        boost = 1.0 + be * np.exp(-np.square(u / max(1e-3, le)))
        r = f["r_obs"] * scale * boost * ss
        # trim free ends so the round cap lands on the original stroke tip
        lo, hi = 0, n
        if not f.get("start_junction", False):
            lo = min(n - 1, int(round(0.65 * r[0])))
        if not f.get("end_junction", False):
            hi = max(lo + 1, n - int(round(0.65 * r[-1])))
        pts, r = pts[lo:hi], r[lo:hi]
        if len(pts) < 2:
            continue
        for (y, x), rr in zip(pts, r):
            cv2.circle(out, (int(round(x)), int(round(y))), max(1, int(round(rr))), 1, -1)
    return cv2.resize(out * 255, (size, size), interpolation=cv2.INTER_AREA) > 127


def render_polygon(frames, scale: float = 1.28, be: float = 0.18, le: float = 0.22,
                   size: int = SIZE, ss: int = 2) -> np.ndarray:
    """Sweep a variable-width ribbon along each stroke (blunt ends, no round caps).

    Unlike disk stamping this does not add r pixels of length at every stroke end,
    which kept the ink budget ~40% too high.
    """
    S = size * ss
    out = np.zeros((S, S), np.uint8)
    for f in frames:
        pts = f["pts"] * ss
        n = len(pts)
        if n < 2:
            continue
        half = max(1.0, (n - 1) / 2.0)
        u = np.where(np.isfinite(f["d_free"]), f["d_free"] / half, 1.0)
        boost = 1.0 + be * np.exp(-np.square(u / max(1e-3, le)))
        r = np.maximum(1.2 * ss, f["r_obs"] * scale * boost * ss)
        tan = np.gradient(pts, axis=0)
        norm = np.linalg.norm(tan, axis=1, keepdims=True) + 1e-6
        tan = tan / norm
        nrm = np.stack([-tan[:, 1], tan[:, 0]], axis=1)     # (dy, dx) normal
        left = pts + nrm * r[:, None]
        right = pts - nrm * r[:, None]
        poly = np.concatenate([left, right[::-1]], axis=0)
        cv2.fillPoly(out, [np.round(poly).astype(np.int32)], 1, lineType=cv2.LINE_AA)
    return cv2.resize(out * 255, (size, size), interpolation=cv2.INTER_AREA) > 127


def brush_polygon(ch: str, font_path: str, scale: float = 1.28, be: float = 0.18,
                  le: float = 0.22, size: int = SIZE) -> np.ndarray:
    m = render_char(ch, font_path, size)
    return render_polygon(glyph_frames(m, size), scale, be, le, size)


def as_mask(a) -> np.ndarray:
    """Coerce any {bool, 0/1, 0/255} array to a boolean ink mask."""
    a = np.asarray(a)
    if a.dtype == bool:
        return a
    if a.size and a.max() <= 1:
        return a.astype(bool)
    return a > 127


def dice(a, b) -> float:
    a, b = as_mask(a), as_mask(b)
    return float(2 * (a & b).sum() / max(1, a.sum() + b.sum()))


# ---------------------------------------------------------------- field render
def _end_kind(pts: np.ndarray, at_start: bool) -> str:
    """Classify a free stroke end: 顿 (horizontal/vertical press) vs 锋 (diagonal tip)."""
    k = min(6, len(pts) - 1)
    seg = (pts[k] - pts[0]) if at_start else (pts[-1] - pts[-1 - k])
    seg = np.abs(seg) / (np.linalg.norm(seg) + 1e-6)
    if seg[1] >= 0.72:      # mostly horizontal
        return "dun"
    if seg[0] >= 0.72:      # mostly vertical
        return "dun"
    return "feng"


def end_kinds(f: dict) -> tuple[str, str]:
    pts = f["pts"]
    return (_end_kind(pts, True) if not f.get("start_junction") else "junc",
            _end_kind(pts, False) if not f.get("end_junction") else "junc")


def render_field(frames, scale: float = 0.90, be: float = 0.28, le: float = 0.20,
                 contrast: float = 0.06, size: int = SIZE, ss: int = 1) -> np.ndarray:
    """Render strokes as the zero level-set of (distance - radius).

    No round caps: the ribbon terminates at the skeleton end, so ink budget is
    governed by `scale` alone.  `dun` ends are widened (顿笔); `feng` ends keep
    the source taper.
    """
    S = size * ss
    acc = np.full((S, S), np.inf, np.float32)
    for f in frames:
        pts = (f["pts"] * ss).astype(np.float32)
        n = len(pts)
        if n < 2:
            continue
        half = max(1.0, (n - 1) / 2.0)
        u = np.where(np.isfinite(f["d_free"]), f["d_free"] / half, 1.0)
        ks, ke = end_kinds(f)
        boost = np.ones(n, np.float32)
        # u = 0 at a free end -> the 顿笔 boost must peak there
        if ks == "dun":
            boost *= 1.0 + be * np.exp(-np.square(u / max(1e-3, le)))
        if ke == "dun":
            boost *= 1.0 + be * np.exp(-np.square(u / max(1e-3, le)))
        orient = 1.0 + contrast * (2.0 * f["vert"] - 1.0)
        r = np.maximum(1.0 * ss, f["r_obs"] * scale * orient * boost * ss)

        y0 = max(0, int(pts[:, 0].min() - r.max() - 2))
        y1 = min(S, int(pts[:, 0].max() + r.max() + 2))
        x0 = max(0, int(pts[:, 1].min() - r.max() - 2))
        x1 = min(S, int(pts[:, 1].max() + r.max() + 2))
        if y1 <= y0 or x1 <= x0:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        P = np.stack([yy, xx], -1).astype(np.float32)          # (H,W,2)
        best = np.full(P.shape[:2], np.inf, np.float32)
        for i in range(n - 1):
            p0, p1 = pts[i], pts[i + 1]
            r0, r1 = r[i], r[i + 1]
            v = p1 - p0
            L2 = float(v @ v) + 1e-6
            t = np.clip(((P - p0) @ v) / L2, 0.0, 1.0)
            proj = p0 + t[..., None] * v
            d = np.linalg.norm(P - proj, axis=-1)
            rr = r0 + t * (r1 - r0)
            best = np.minimum(best, d - rr)
        acc[y0:y1, x0:x1] = np.minimum(acc[y0:y1, x0:x1], best)
    ink = acc <= 0
    if ss > 1:
        ink = cv2.resize(ink.astype(np.uint8) * 255, (size, size),
                         interpolation=cv2.INTER_AREA) > 127
    return ink


def brush_field(ch: str, font_path: str, **kw) -> np.ndarray:
    m = render_char(ch, font_path, kw.get("size", SIZE))
    return render_field(glyph_frames(m, kw.get("size", SIZE)), **kw)


def render_with_ink_budget(frames, target_ink: float, size: int = SIZE,
                           lo: float = 0.55, hi: float = 1.35, iters: int = 5, **kw):
    """Bisect the global scale so the rendered ink matches `target_ink` pixels."""
    best = None
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        m = render_field(frames, scale=mid, size=size, **kw)
        n = int(m.sum())
        best = m
        if n > target_ink:
            hi = mid
        else:
            lo = mid
    return best


def ink_target_for(ch: str, font_path: str, ratio: float = 0.83, size: int = SIZE) -> int:
    """Target ink = source ink * ratio (0.83 because WenKai is 1.20x the print)."""
    src = render_char(ch, font_path, size)
    return max(1, int(round(src.sum() * ratio)))
