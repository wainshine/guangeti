"""Structure metrics measured against the *print*, not against the content font.

The old "topology equals WenKai" metric is circular for line A (the ribbon skeleton
is WenKai's) and has no discriminative power against the print (real, WenKai and GAN
all land at ~11%). This script reports dimensioned structure instead:

  centroid offset   -- where the ink sits inside the em box
  aspect ratio      -- how open the glyph is
  horizontal angle  -- KS of the 横画 inclination distribution
  counter diff      -- how many counters differ (0 = same count)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
S = 256


def h_angles(mask, min_len=40):
    m = (mask > 127).astype(np.uint8)
    lines = cv2.HoughLinesP(m, 1, np.pi / 360, threshold=28,
                            minLineLength=min_len, maxLineGap=6)
    if lines is None:
        return []
    out = []
    for l in lines.reshape(-1, 4):
        x1, y1, x2, y2 = [int(v) for v in l]
        a = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if a > 90:
            a -= 180
        if a < -90:
            a += 180
        if abs(a) <= 20:
            out.append(abs(a))
    return out


def counters(mask, minarea=20):
    mb = mask.astype(bool)
    n, _l, st, _ = cv2.connectedComponentsWithStats((~mb).astype(np.uint8), 8)
    return sum(1 for i in range(1, n) if st[i, 4] >= minarea
               and st[i, 0] > 1 and st[i, 1] > 1
               and st[i, 0] + st[i, 2] < mb.shape[1] - 1
               and st[i, 1] + st[i, 3] < mb.shape[0] - 1)


def centroid(mask):
    ys, xs = np.nonzero(mask > 127)
    if len(xs) == 0:
        return 0.5, 0.5
    return float(xs.mean()) / mask.shape[1], float(ys.mean()) / mask.shape[0]


def aspect(mask):
    ys, xs = np.nonzero(mask > 127)
    if len(xs) == 0:
        return 1.0
    return float(xs.max() - xs.min() + 1) / max(1.0, float(ys.max() - ys.min() + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--out", default=str(ROOT / "work" / "struct_metrics.json"))
    args = ap.parse_args()

    d = np.load(ROOT / "work" / "pairs" / "pairs.npz", allow_pickle=True)
    X, Y = d["X"], d["Y"]
    sel = np.random.RandomState(0).choice(len(X), args.n, replace=False)

    res = {"n": len(sel), "reference": "print (Y)"}
    for name, data in (("霞鹜文楷", X), ("真迹(自参照)", Y)):
        ang, cx, cy, ar = [], [], [], []
        for i in sel:
            m = data[i]
            ang += h_angles(m)
            a, b = centroid(m)
            cx.append(a); cy.append(b); ar.append(aspect(m))
        res[name] = {
            "h_angle_median": round(float(np.median(ang)), 2),
            "h_angle_iqr": [round(float(np.percentile(ang, 25)), 2),
                            round(float(np.percentile(ang, 75)), 2)],
            "centroid_dx": round(float(np.median(cx)) - 0.5, 4),
            "centroid_dy": round(float(np.median(cy)) - 0.5, 4),
            "aspect": round(float(np.median(ar)), 3),
        }
    # KS between WenKai and print
    kw, pr = [], []
    for i in sel:
        kw += h_angles(X[i]); pr += h_angles(Y[i])
    res["h_angle_KS_wenkai_vs_print"] = round(float(ks_2samp(kw, pr).statistic), 3)
    # counter agreement with the print
    same = sum(1 for i in sel if counters(X[i]) == counters(Y[i]))
    res["counter_equal_wenkai_vs_print"] = f"{same}/{len(sel)}"
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
