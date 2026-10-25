"""E37: contour-level area compensation.

potrace expands the traced outline by roughly half a pixel; at 512 that is a larger
relative tax on thin strokes than on thick ones. This measures the expansion as a
function of stroke width and finds the distance-transform erosion that cancels it.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import glyphvec as gv  # noqa: E402
gl = import_module("generate_lib")


def poly_area_em(cs):
    """Signed area of em-space contours (y-up), in font units squared."""
    total = 0.0
    for c in cs:
        pts = [c["start"]]
        for s in c["segs"]:
            pts.append([s[1], s[2]] if s[0] == "L" else [s[-2], s[-1]])
        if len(pts) < 3:
            continue
        p = np.asarray(pts, float)
        x, y = p[:, 0], p[:, 1]
        total += 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    return total


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
    S = 512
    k = 1000.0 / S

    masks = {}
    for i in sel:
        base = gl.render_base(f256, str(chars[i]), 256)
        a = (base.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            m = G(torch.from_numpy(a).float()).numpy()[0, 0] > -0.05
        masks[i] = (cv2.resize(m.astype(np.uint8) * 255, (S, S), interpolation=cv2.INTER_LINEAR) > 127)

    print(f"{'trace@':>7s} {'轮廓/掩膜':>10s} {'膨胀':>8s}")
    for T in (512, 1024, 2048):
        ratios = []
        for i, m0 in masks.items():
            m = m0
            if T != S:
                m = cv2.resize(m0.astype(np.uint8) * 255, (T, T), interpolation=cv2.INTER_LINEAR) > 127
            cs = gv.trace(m.astype(bool), turdsize=4, alphamax=0.4, opttol=0.5)
            em = gl.raster_to_em(cs, T)
            ratios.append(poly_area_em(em) / (float(m0.sum()) * (1000.0 / S) ** 2))
        print(f"{T:7d} {np.median(ratios):10.4f} {np.median(ratios)-1:8.1%}", flush=True)
    return
    print(f"{'r(px)':>6s} {'轮廓/掩膜':>10s} {'中位面积损失':>12s}")
    for r in (0.0, 0.3, 0.5, 0.7, 0.9, 1.1):
        ratios = []
        for i, m0 in masks.items():
            m = m0
            if r > 0:
                dt = cv2.distanceTransform(m0.astype(np.uint8), cv2.DIST_L2, 5)
                m = dt > r
            if m.sum() < 50:
                continue
            cs = gv.trace(m.astype(bool), turdsize=4, alphamax=0.4, opttol=0.5)
            em = gl.raster_to_em(cs, S)
            # 分母固定为【未腐蚀】的掩膜，才能看出绝对变化
            ratios.append(poly_area_em(em) / (float(m0.sum()) * k * k))
        print(f"{r:6.1f} {np.median(ratios):10.4f} {1-np.median(ratios):12.1%}", flush=True)


if __name__ == "__main__":
    main()
