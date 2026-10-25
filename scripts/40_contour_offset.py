"""E37b: cancel potrace's inflation with a polygon offset in em space.

potrace traces about 13% more area than the raster it was given, roughly independent of
resolution (E37). A uniform inward offset of d font-units removes P*d of area while barely
touching the glyph bbox, which is what we want: thinner strokes, same 字面.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location

import cv2
import numpy as np
import torch
from PIL import ImageFont
from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import glyphvec as gv  # noqa: E402
gl = import_module("generate_lib")


def to_poly(c):
    pts = [c["start"]]
    for s in c["segs"]:
        pts.append([s[1], s[2]] if s[0] == "L" else [s[-2], s[-1]])
    return np.asarray(pts, float)


def em_area(cs):
    """Signed area: outer shells and holes carry opposite winding, so they cancel."""
    a = 0.0
    for c in cs:
        p = to_poly(c)
        if len(p) < 3:
            continue
        x, y = p[:, 0], p[:, 1]
        a += 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    return abs(a)


def offset_contours(cs, d):
    """Inward offset by d font units, holes handled by containment."""
    polys = []
    for c in cs:
        p = to_poly(c)
        if len(p) < 3:
            continue
        poly = Polygon(p)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if not poly.is_empty:
            polys.append(poly)
    if not polys:
        return cs
    polys.sort(key=lambda q: -q.area)
    shells, holes = [], []
    for poly in polys:
        if any(sh.contains(poly.representative_point()) for sh in shells):
            holes.append(poly)
        else:
            shells.append(poly)
    merged = unary_union(shells).difference(unary_union(holes)) if holes else unary_union(shells)
    g = merged.buffer(-d, join_style=2, mitre_limit=3.0)
    if g.is_empty:
        return []
    geoms = list(g.geoms) if g.geom_type.startswith("Multi") else [g]
    out = []
    for gg in geoms:
        for ring in [gg.exterior, *gg.interiors]:
            pts = list(ring.coords)
            if len(pts) < 4:
                continue
            out.append({"start": [float(pts[0][0]), float(pts[0][1])],
                        "segs": [["L", float(x), float(y)] for x, y in pts[1:]]})
    return out


def main():
    d = np.load(ROOT / "work/pairs_single.npz", allow_pickle=True)
    X, Y, chars = d["X"], d["Y"], d["chars"]
    sel = np.random.RandomState(7).choice(len(X), 120, replace=False)
    spec = spec_from_file_location("gan", ROOT / "scripts/21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    G = gan.Generator()
    G.load_state_dict(torch.load(ROOT / "work/ckpt/m2_ep080.pt", map_location="cpu")["G"])
    G.eval()
    f256 = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 256)
    S, k = 512, 1000.0 / 512

    masks = {}
    for i in sel:
        base = gl.render_base(f256, str(chars[i]), 256)
        a = (base.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            m = G(torch.from_numpy(a).float()).numpy()[0, 0] > -0.05
        masks[i] = cv2.resize(m.astype(np.uint8) * 255, (S, S), interpolation=cv2.INTER_LINEAR) > 127

    print(f"{'offset':>7s} {'面积/掩膜':>10s} {'相对原轮廓':>10s}")
    for d_units in (0.0, 1.0, 2.0, 3.0, 4.0):
        ratios, rel = [], []
        for i, m0 in masks.items():
            cs = gv.trace(m0.astype(bool), turdsize=4, alphamax=0.4, opttol=0.5)
            em = gl.raster_to_em(cs, S)
            a0 = em_area(em)
            em2 = offset_contours(em, d_units) if d_units > 0 else em
            a1 = em_area(em2)
            if a0 <= 0:
                continue
            ratios.append(a1 / (float(m0.sum()) * k * k))
            rel.append(a1 / a0)
        print(f"{d_units:7.1f} {np.median(ratios):10.4f} {np.median(rel):10.3f}", flush=True)


if __name__ == "__main__":
    main()
