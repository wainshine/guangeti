"""Cap geometry in em space: measure the real caps, then replace synthesised ones."""
from __future__ import annotations

import cv2
from shapely.geometry import Polygon, Point

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import brush_lib as B  # noqa: E402
from generate_lib import raster_to_em  # noqa: E402
from glyphvec import trace  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
K = 1000.0 / 256.0


def synth_contours(ch: str, font: str | None = None):
    m = B.render_char(ch, font or str(ROOT / "data/base/LXGWWenKai-Regular.ttf"))
    m = m.astype(np.uint8)
    m = __import__("cv2").erode(m, np.ones((1, 3), np.uint8))
    m = __import__("cv2").morphologyEx(m, __import__("cv2").MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cs = trace(m > 0, turdsize=4, alphamax=1.0, opttol=0.25)
    return raster_to_em(cs, 256)


def contour_poly(c, step=1.5):
    pts = [np.array(c["start"], float)]
    for s in c["segs"]:
        if s[0] == "L":
            pts.append(np.array(s[1:3], float))
        else:
            p0 = pts[-1]
            p1 = np.array(s[1:3], float); p2 = np.array(s[3:5], float); p3 = np.array(s[5:7], float)
            n = max(2, int(np.linalg.norm(p3 - p0) / step))
            for t in np.linspace(0, 1, n)[1:]:
                u = 1 - t
                pts.append(u**3 * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t**3 * p3)
    return np.array(pts)


def frames_em(mask):
    out = []
    for f in B.glyph_frames(mask):
        n = len(f["pts"]); k = max(5, n // 6)
        for idx, junc in ((0, f.get("start_junction")), (-1, f.get("end_junction"))):
            if junc:
                continue
            body = f["r_obs"][k:2 * k] if idx == 0 else f["r_obs"][-2 * k:-k]
            w = float(np.median(body)) if len(body) else float(f["r_obs"][idx])
            if w < 2.5:
                continue
            pts = f["pts"]; kk = min(5, n - 1)
            P = pts[idx].astype(float)
            d = pts[idx] - pts[kk if idx == 0 else -1 - kk]
            dv = np.array([d[1] * K, -d[0] * K])
            dv = dv / (np.linalg.norm(dv) + 1e-9)
            out.append({
                "P": np.array([P[1] * K, 880.0 - P[0] * K]),
                "d": dv,
                "w": w * K,
            })
    return out


def cap_measure(contours, frames, cut=0.8):
    """For each end: cut at Q = P - cut*w*d, return cap height / w and asymmetry / w."""
    polys = [contour_poly(c) for c in contours]
    out = []
    for fr in frames:
        P, d, w = fr["P"], fr["d"], fr["w"]
        Q = P - d * (cut * w)
        best = None
        for poly in polys:
            s = (poly - Q) @ d
            sign = np.sign(s)
            if not (sign.max() > 0 and sign.min() < 0):
                continue
            idx = np.nonzero(np.diff(sign) != 0)[0]
            if len(idx) < 2:
                continue
            # take the pair that brackets the cap (both crossings near Q)
            pts = []
            for i in idx:
                t = -s[i] / (s[i + 1] - s[i] + 1e-9)
                pts.append((i, poly[i] + t * (poly[i + 1] - poly[i]), t))
            # pick the two crossings whose mid-arc is on the +d side
            for a in range(len(pts)):
                for b in range(a + 1, len(pts)):
                    ia, pa, _ = pts[a]; ib, pb, _ = pts[b]
                    if ib - ia < 3:
                        continue
                    arc = poly[ia:ib + 1]
                    if ((arc - Q) @ d).mean() <= 0:
                        continue
                    h = float(((arc - Q) @ d).max()) / w
                    n = np.array([-d[1], d[0]])
                    asym = float(np.abs(((arc - Q) @ n).mean())) / w
                    cand = (h, asym)
                    if best is None or cand[0] < best[0]:
                        best = cand
        if best:
            out.append(best)
    return out


def replace_cap(poly: np.ndarray, Q, d, h, s=0.0, w=1.0) -> np.ndarray:
    """Cut the contour at the plane through Q (normal d) and insert a tent cap."""
    res = _replace_cap_dir(poly, Q, d, h, s, w)
    if res is poly:
        res = _replace_cap_dir(poly[::-1], Q, d, h, s, w)
        if res is not poly[::-1]:
            pass
    return res


def _replace_cap_dir(poly, Q, d, h, s, w):
    sign = np.sign((poly - Q) @ d)
    if not (sign.max() > 0 and sign.min() < 0):
        return poly
    idx = np.nonzero(np.diff(sign) != 0)[0]
    if len(idx) < 2:
        return poly
    pts = []
    for i in idx:
        t = -sign[i] / (sign[i + 1] - sign[i] + 1e-9)
        pts.append((i, poly[i] + t * (poly[i + 1] - poly[i])))
    # choose the pair whose arc lies on the +d side
    best = None
    for a in range(len(pts)):
        for b in range(a + 1, len(pts)):
            ia, pa = pts[a]; ib, pb = pts[b]
            if ib - ia < 3:
                continue
            arc = poly[ia:ib + 1]
            if ((arc - Q) @ d).mean() <= 0:
                continue
            span = float((arc - Q).dot(d).max())
            if best is None or span < best[0]:
                best = (span, ia, ib, pa, pb)
    if best is None:
        return poly
    _, ia, ib, pa, pb = best
    chord = float(np.linalg.norm(pa - pb))
    # sanity: chord should be about the stroke width (2w) and the replaced arc short
    if not (1.3 * w <= chord <= 3.1 * w) or (ib - ia) > 0.35 * len(poly):
        return poly
    n = np.array([-d[1], d[0]])
    T = Q + d * (h * float(np.linalg.norm(pa - pb)) * 0.5) + n * s
    head = poly[:ia + 1]
    tail = poly[ib:]
    return np.vstack([head, T, tail])


def _poly_area_sign(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _valid(poly_pts, tol_area):
    try:
        pg = Polygon(poly_pts)
    except Exception:
        return False, 0.0
    if not pg.is_valid:
        fixed = pg.buffer(0)
        bad = abs(pg.area - fixed.area)
        return bad <= tol_area, bad
    return True, 0.0


def replace_all(contours, frames, h=0.96, s=0.0, max_extend=1.15, verbose=False, h_array=None):
    """Replace caps with validity guards; falls back to the original contour on failure."""
    polys = [contour_poly(c) for c in contours]
    shapes = [Polygon(p) if len(p) >= 3 else None for p in polys]
    kept = skipped = 0
    for fi, fr in enumerate(frames):
        hh = float(h_array[fi]) if h_array is not None else float(h)
        P, d, w = fr["P"], fr["d"], fr["w"]
        Q = P - d * (0.8 * w)
        best = None
        for j, poly in enumerate(polys):
            dist = np.linalg.norm(poly - P, axis=1).min()
            if best is None or dist < best[0]:
                best = (dist, j)
        if best is None:
            continue
        j = best[1]
        cand = replace_cap(polys[j], Q, d, hh, s, w)
        # apex must not land inside another contour
        apex = cand[min(len(cand) - 1, np.argmax((cand - P) @ d))]
        inside_other = any(k != j and shapes[k] is not None and shapes[k].contains(Point(apex))
                           for k in range(len(shapes)))
        ok, bad = _valid(cand, tol_area=0.01 * w * w)
        # cap extent must not grow beyond max_extend * original
        orig_ext = float(((polys[j] - Q) @ d).max())
        new_ext = float(((cand - Q) @ d).max())
        if inside_other or not ok or new_ext > max_extend * max(orig_ext, 1e-6):
            skipped += 1
            continue
        polys[j] = cand
        shapes[j] = Polygon(cand)
        kept += 1
    if verbose:
        print(f"  caps kept {kept}, skipped {skipped}")
    return [dict(start=tuple(p[0]), segs=[("L", float(x), float(y)) for x, y in p[1:]]) for p in polys]


# ---------------------------------------------------------------- segment-level
def _seg_points(c, seg):
    """Sample one segment densely (returns list of points, excluding its start)."""
    if seg[0] == "L":
        return [np.array(seg[1:3], float)]
    p1 = np.array(seg[1:3], float); p2 = np.array(seg[3:5], float); p3 = np.array(seg[5:7], float)
    return [p1, p2, p3]


def _split_seg(c_pt, seg, t):
    """Split a segment at parameter t, returning (head, tail, point)."""
    if seg[0] == "L":
        p0 = c_pt; p1 = np.array(seg[1:3], float)
        pt = p0 + t * (p1 - p0)
        return ("L", *pt), ("L", *p1), pt
    p0 = c_pt; p1 = np.array(seg[1:3], float); p2 = np.array(seg[3:5], float); p3 = np.array(seg[5:7], float)
    def lerp(a, b, u): return a + u * (b - a)
    a1 = lerp(p0, p1, t); a2 = lerp(p1, p2, t); a3 = lerp(p2, p3, t)
    b1 = lerp(a1, a2, t); b2 = lerp(a2, a3, t)
    pt = lerp(b1, b2, t)
    head = ("C", *a1, *b1, *pt)
    tail = ("C", *b2, *a3, *p3)
    return head, tail, pt


def replace_cap_curve(c, d, w, h, Q=None, cut=0.8):
    """Replace the cap arc of contour `c` with two straight segments meeting at T.

    Keeps the rest of the contour's original Bezier segments (no polyline bloat).
    Returns (new_contour, ok).
    """
    P = Q if Q is not None else None
    start = np.array(c["start"], float)
    segs = c["segs"]
    # flatten with mapping
    pts = [start]; meta = []      # (seg_index, t_end)
    cur = start
    for i, s in enumerate(segs):
        if s[0] == "L":
            pts.append(np.array(s[1:3], float)); meta.append((i, 1.0)); cur = pts[-1]
        else:
            p1 = np.array(s[1:3], float); p2 = np.array(s[3:5], float); p3 = np.array(s[5:7], float)
            for u in np.linspace(0, 1, 12)[1:]:
                v = 1 - u
                pts.append(v**3*cur + 3*v*v*u*p1 + 3*v*u*u*p2 + u**3*p3)
                meta.append((i, u))
            cur = pts[-1]
    pts = np.array(pts)
    sgn = np.sign((pts - Q) @ d)
    if not (sgn.max() > 0 and sgn.min() < 0):
        return c, False
    idx = np.nonzero(np.diff(sgn) != 0)[0]
    if len(idx) < 2:
        return c, False
    cross = []
    for i in idx:
        t = -sgn[i] / (sgn[i+1] - sgn[i] + 1e-9)
        cross.append((i, t, pts[i] + t * (pts[i+1] - pts[i])))
    best = None
    for a in range(len(cross)):
        for b in range(a+1, len(cross)):
            ia, ta, pa = cross[a]; ib, tb, pb = cross[b]
            arc = pts[ia:ib+1]
            if ((arc - Q) @ d).mean() <= 0:
                continue
            chord = float(np.linalg.norm(pa - pb))
            if not (1.3*w <= chord <= 3.1*w):
                continue
            if (ib - ia) > 0.35 * len(pts):
                continue
            if best is None or chord < best[0]:
                best = (chord, ia, ta, pa, ib, tb, pb)
    if best is None:
        return c, False
    _, ia, ta, pa, ib, tb, pb = best
    # original cap area (arc + chord) for the area guard
    arc = pts[ia:ib+1]
    cap_area = abs(_poly_area_sign(np.vstack([arc, pa])))
    n = np.array([-d[1], d[0]])
    T = Q + d * (h * w)
    tent_area = 0.5 * float(np.linalg.norm(pa - pb)) * abs(float((T - Q) @ d))
    apex_dist = float(np.linalg.norm(T - (P if P is not None else Q)))
    # guards
    if tent_area > 2.0 * cap_area:
        return c, False
    if np.linalg.norm(T - pa) < 0.35 * w or np.linalg.norm(T - pb) < 0.35 * w:
        return c, False
    # rebuild: segments before ia, split at pa, T, split at pb, segments after ib
    i0, t0 = meta[ia]; i1, t1 = meta[ib]
    if i0 == i1:
        if t1 <= t0:
            return c, False
        cur_pt = start
        for j in range(i0):
            s_ = segs[j]
            cur_pt = np.array(s_[1:3], float) if s_[0] == "L" else np.array(s_[-2:], float)
        head, mid, ptA = _split_seg(cur_pt, segs[i0], t0)
        # split the remaining piece again at (t1-t0)/(1-t0)
        u = (t1 - t0) / max(1e-6, 1.0 - t0)
        _, tail2, ptB = _split_seg(ptA, mid, u)
        out_segs = [s_ for s_ in segs[:i0]]
        out_segs.append(head)
        out_segs.append(("L", *T))
        out_segs.append(("L", *ptB))
        out_segs.append(tail2)
        out_segs.extend(segs[i0+1:])
        return dict(start=tuple(start), segs=out_segs), True
    out_segs = [s for s in segs[:i0]]
    cur_pt = start
    # advance cur_pt to segment i0 start
    for j in range(i0):
        s = segs[j]
        cur_pt = np.array(s[1:3], float) if s[0] == "L" else np.array(s[-2:], float)
    head, tail, ptA = _split_seg(cur_pt, segs[i0], t0)
    out_segs.append(head)
    out_segs.append(("L", *T))
    # segment i1 split
    cur_pt = start
    for j in range(i1):
        s = segs[j]
        cur_pt = np.array(s[1:3], float) if s[0] == "L" else np.array(s[-2:], float)
    _, tail1, ptB = _split_seg(cur_pt, segs[i1], t1)
    out_segs.append(("L", *ptB))
    out_segs.append(tail1)
    out_segs.extend(segs[i1+1:])
    return dict(start=tuple(start), segs=out_segs), True


def replace_all_curve(contours, frames, h_array=None, h=0.96, verbose=False):
    """Segment-preserving cap replacement with geometry guards."""
    out = []
    kept = skipped = 0
    for ci, c in enumerate(contours):
        out.append(c)
    # map each end to the contour whose polyline is nearest
    polys = [contour_poly(c) for c in contours]
    for fi, fr in enumerate(frames):
        hh = float(h_array[fi]) if h_array is not None else float(h)
        P, d, w = fr["P"], fr["d"], fr["w"]
        Q = P - d * (0.8 * w)
        best = None
        for j, poly in enumerate(polys):
            dist = np.linalg.norm(poly - P, axis=1).min()
            if best is None or dist < best[0]:
                best = (dist, j)
        if best is None:
            continue
        j = best[1]
        new, ok = replace_cap_curve(out[j], d, w, hh, Q=Q)
        if ok:
            out[j] = new
            polys[j] = contour_poly(new)
            kept += 1
        else:
            skipped += 1
    if verbose:
        print(f"  caps kept {kept}, skipped {skipped}")
    return out, kept, skipped


def _simplify(cs, eps=0.6):
    out = []
    for c in cs:
        p = contour_poly(c)
        if len(p) < 3:
            out.append(c); continue
        ap = cv2.approxPolyDP(p.reshape(-1, 1, 2).astype(np.float32), eps, True).reshape(-1, 2)
        if len(ap) < 3:
            out.append(c); continue
        out.append(dict(start=(float(ap[0][0]), float(ap[0][1])),
                        segs=[("L", float(x), float(y)) for x, y in ap[1:]]))
    return out


def replace_all_v2(contours, frames, h_array=None, h=0.96, max_apex=1.2, eps=0.6):
    """Polyline cap replacement + apex guard + Douglas-Peucker simplification.

    Returns (contours, kept, skipped).  Caller must still run a per-glyph hole check.
    """
    polys = [contour_poly(c) for c in contours]
    kept = skipped = 0
    for fi, fr in enumerate(frames):
        hh = float(h_array[fi]) if h_array is not None else float(h)
        P, d, w = fr["P"], fr["d"], fr["w"]
        Q = P - d * (0.8 * w)
        best = None
        for j, poly in enumerate(polys):
            dist = np.linalg.norm(poly - P, axis=1).min()
            if best is None or dist < best[0]:
                best = (dist, j)
        if best is None:
            continue
        j = best[1]
        cand = replace_cap(polys[j], Q, d, hh, 0.0, w)
        if cand is polys[j] or len(cand) == len(polys[j]):
            skipped += 1
            continue
        apex = cand[np.argmax((cand - P) @ d)]
        if np.linalg.norm(apex - P) > max_apex * w:
            skipped += 1
            continue
        polys[j] = cand
        kept += 1
    cs = [dict(start=tuple(p[0]), segs=[("L", float(x), float(y)) for x, y in p[1:]]) for p in polys]
    cs = _simplify(cs, eps)
    return cs, kept, skipped


def raster_contours(cs, S=256):
    from PIL import Image, ImageDraw
    acc = np.zeros((S, S), np.uint8)
    for c in cs:
        p = contour_poly(c)
        q = np.stack([p[:, 0] / (1000 / S), (880 - p[:, 1]) / (1000 / S)], 1)
        m = Image.new("L", (S, S), 0)
        ImageDraw.Draw(m).polygon([tuple(x) for x in q], fill=1)
        acc ^= np.array(m)
    return acc > 0


def _holes(m):
    cnts, hier = cv2.findContours(m.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    return 0 if hier is None else int((hier[0, :, 3] >= 0).sum())


def apply_caps(contours, mask, h_dist, seed_key, clip=1.8, eps=0.6, max_apex=1.2):
    """Full cap pass with per-glyph topology gate. Returns original contours on failure."""
    fr = frames_em(mask)
    if not fr:
        return contours
    rng = np.random.RandomState((seed_key % (2 ** 31)))
    harr = np.clip(rng.choice(h_dist, size=len(fr), replace=True), 0.3, clip)
    out, kept, skipped = replace_all_v2(contours, fr, h_array=harr, eps=eps, max_apex=max_apex)
    if kept == 0:
        return contours
    before = raster_contours(contours)
    after = raster_contours(out)
    if _holes(after) != _holes(before):
        return contours
    return out
