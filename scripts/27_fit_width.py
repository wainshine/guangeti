"""Refit the per-stroke relative-width distribution from many more real glyphs.

The shipped model was fitted on ~120 glyphs (2,490 strokes). With 617 single-occurrence
glyphs plus the 1,675 chosen ones we have thousands of glyphs available, so the
distribution can be estimated much more tightly.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B


def collect(chars, Y, idx):
    out = []
    for i in idx:
        m = Y[i] > 127
        frames = B.glyph_frames(m)
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
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=str(ROOT / "work/stroke_rel_width.npy"))
    args = ap.parse_args()

    d = np.load(ROOT / "work/pairs/pairs.npz", allow_pickle=True)
    Y = d["Y"]
    idx = list(range(len(Y)))
    if args.limit:
        idx = idx[: args.limit]
    v = collect(None, Y, idx)

    s = np.load(ROOT / "work/pairs_single.npz", allow_pickle=True)
    v2 = collect(None, s["Y"], range(len(s["Y"])))
    v = np.concatenate([v, v2])

    v = np.clip(v, 0.45, 2.2)
    np.save(args.out, v)
    print(f"strokes: {len(v)}  median {np.median(v):.3f}  IQR "
          f"{np.percentile(v, 25):.3f}-{np.percentile(v, 75):.3f}")


if __name__ == "__main__":
    main()
