"""C-line: fit the stroke-width distribution and the ribbon ink curve on this corpus.

`ribbon_scale` in the A line and `ribbon_scale_b` in the B line are fitted curves of
"how thick must the ribbon renderer be so that its ink matches the book's ink".  The
大典's ink density is its own (red rules removed, 300 dpi, smaller glyphs), so neither
curve may be reused.  This script fits both constants from the C training pairs and
writes `work-c/ribbon_fit.json`; no source file is edited.

  python3 scripts/73_fit_width_c.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402

WORK = ROOT / "work-c"


def rel_widths(Y, idx):
    out = []
    for i in idx:
        m = Y[i] > 127
        frames = B.glyph_frames(m, 256)
        rs = []
        for f in frames:
            n = len(f["pts"])
            if n < 20:
                continue
            r = f["r_obs"]
            med = float(np.median(r[n // 3:2 * n // 3]))
            if med >= 2:
                rs.append(float(np.median(r)))
        if len(rs) >= 2:
            med = float(np.median(rs))
            out += [x / med for x in rs]
        elif len(rs) == 1:
            out.append(1.0)
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=str(WORK / "pairs" / "pairs.npz"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    d = np.load(args.pairs, allow_pickle=True)
    X, Y, chars = d["X"], d["Y"], d["chars"]
    idx = list(range(len(Y)))
    if args.limit:
        idx = idx[: args.limit]
    print(f"pairs {len(Y)}")

    v = rel_widths(Y, idx)
    v = np.clip(v, 0.45, 2.2)
    np.save(WORK / "stroke_rel_width.npy", v)
    print(f"strokes {len(v)} median {np.median(v):.3f} IQR "
          f"{np.percentile(v,25):.3f}-{np.percentile(v,75):.3f}")

    # ---- ink ratio curve: book / WenKai as a function of WenKai ink at 256
    comp = np.array([(X[i] > 127).sum() for i in idx], np.float64)
    ratio = np.array([max(1.0, (Y[i] > 127).sum()) / max(1.0, comp[k])
                      for k, i in enumerate(idx)], np.float64)
    ok = (comp > 500) & (ratio > 0.2) & (ratio < 3.0)
    # np.polyfit returns [slope, intercept] (highest degree first) — the first
    # version read them the other way round and produced a negative exponent
    slope, intercept = np.polyfit(np.log(comp[ok]), np.log(ratio[ok]), 1)
    A = float(np.exp(intercept))
    EXP = float(-slope)
    print(f"ink ratio = {A:.4f} * comp^-{EXP:.4f}  (median ratio {np.median(ratio[ok]):.3f})")

    # ---- ribbon base: ink of ribbon at scale 1 / WenKai ink, on a sample
    rng = np.random.RandomState(0)
    samp = rng.choice(len(idx), min(200, len(idx)), replace=False)
    rel = np.load(WORK / "stroke_rel_width.npy")
    bases = []
    import cv2
    for j in samp:
        i = idx[j]
        wm = X[i] > 127
        fr = B.glyph_frames(wm, 256)
        if not fr:
            continue
        r = np.random.RandomState(int(i))
        raw = r.choice(rel, size=len(fr), replace=True)
        raw /= max(1e-6, raw.mean())
        w = np.power(raw, 1.4)
        w /= max(1e-6, w.mean())
        m = B.render_ribbon(fr, scale=1.0, dips=w, end_skew=0.9, taper=0.2, size=256, ss=2)
        bases.append(float(m.sum()) / max(1.0, float(wm.sum())))
    base = float(np.median(bases)) if bases else 1.06
    print(f"ribbon base (ink at scale 1 / WenKai ink) = {base:.4f}")
    fit = dict(a=A, exp=EXP, base=base, n_pairs=int(len(Y)),
               median_ratio=float(np.median(ratio[ok])),
               rel_widths=int(len(v)))
    (WORK / "ribbon_fit.json").write_text(json.dumps(fit, ensure_ascii=False, indent=1))
    print(json.dumps(fit, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
