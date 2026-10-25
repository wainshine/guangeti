"""Per-glyph structural agreement with the print, graded instead of all-or-nothing.

The old metric ("counter count equals WenKai") is binary, circular for line A and
has no discriminative power against the print (everything lands at ~11%). This one
compares skeletons:

  skel_chamfer   mean distance (px) from one skeleton to the other, both directions
  end_delta      difference in skeleton endpoints (free stroke ends)
  junc_delta     difference in skeleton junctions (stroke crossings)
  len_ratio      skeleton length ratio

All measured after aligning the two masks by their ink centroid.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location

import numpy as np
import torch
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402
import cv2  # noqa: E402
from generate_lib import render_base, ribbon_scale  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402

S = 256


def shift_to_centroid(mask, ref):
    """Translate mask so its ink centroid matches ref's. Inputs may be bool or 0-255."""
    mask = mask.astype(bool)
    ref = ref.astype(bool)
    ys, xs = np.nonzero(mask)
    ys2, xs2 = np.nonzero(ref)
    if len(xs) == 0 or len(xs2) == 0:
        return mask
    dx = xs2.mean() - xs.mean()
    dy = ys2.mean() - ys.mean()
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(mask.astype(np.uint8), M, (mask.shape[1], mask.shape[0])) > 0


def _clusters(mask, min_size=1):
    if mask.sum() == 0:
        return 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    return sum(1 for i in range(1, n) if st[i, 4] >= min_size)


def skel_stats(sk):
    """Number of free stroke ends and of stroke junctions (clustered, not pixels)."""
    k = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], np.uint8)
    nb = cv2.filter2D(sk.astype(np.uint8), -1, k)
    ends = _clusters(sk & (nb == 1))
    junc = _clusters(sk & (nb >= 3))
    return ends, junc


def score(mask, ref):
    a = shift_to_centroid(mask, ref)
    b = ref.astype(bool)
    sks = B.skeleton_of(a)
    skr = B.skeleton_of(b)
    if sks.sum() < 10 or skr.sum() < 10:
        return None
    d_to_r = distance_transform_edt(~skr)
    d_to_s = distance_transform_edt(~sks)
    chamfer = 0.5 * (float(d_to_r[sks].mean()) + float(d_to_s[skr].mean()))
    ea, ja = skel_stats(sks)
    eb, jb = skel_stats(skr)
    return {
        "skel_chamfer_px": chamfer,
        "end_delta": abs(ea - eb),
        "junc_delta": abs(ja - jb),
        "len_ratio": float(sks.sum()) / max(1.0, float(skr.sum())),
        "dice": 2 * float((a & b).sum()) / max(1.0, float(a.sum() + b.sum())),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--gan", default=str(ROOT / "work" / "ckpt" / "m2_ep080.pt"))
    ap.add_argument("--out", default=str(ROOT / "work" / "struct_score.json"))
    args = ap.parse_args()

    d = np.load(ROOT / "work" / "pairs_single.npz", allow_pickle=True)
    X, Y = d["X"], d["Y"]
    sel = np.random.RandomState(0).choice(len(X), args.n, replace=False)

    spec = spec_from_file_location("gan", ROOT / "scripts" / "21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    G = gan.Generator(); G.load_state_dict(torch.load(args.gan, map_location="cpu")["G"]); G.eval()

    font = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S)
    rel = np.load(ROOT / "work" / "stroke_rel_width.npy")

    def ribbon(i):
        wm = X[i] > 127
        fr = B.glyph_frames(wm, S)
        r = np.random.RandomState(int(i))
        raw = r.choice(rel, size=len(fr), replace=True); raw /= max(1e-6, raw.mean())
        w = np.power(raw, 1.4); w /= max(1e-6, w.mean())
        return B.render_ribbon(fr, scale=ribbon_scale(float(wm.sum())), dips=w,
                               end_skew=0.9, taper=0.2, size=S, ss=2)

    def gan_out(i):
        a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            return G(torch.from_numpy(a).float()).numpy()[0, 0] > 0

    rows = {}
    for name, fn in (("霞鹜文楷", lambda i: X[i] > 127), ("ribbon", ribbon), ("GAN", gan_out)):
        vals = []
        for i in sel:
            s = score(fn(i), Y[i])
            if s:
                vals.append(s)
        agg = {k: round(float(np.median([v[k] for v in vals])), 3) for k in vals[0]}
        agg["n"] = len(vals)
        rows[name] = agg
        print(f"{name:8s} " + "  ".join(f"{k} {agg[k]}" for k in agg))
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("->", args.out)


if __name__ == "__main__":
    main()
