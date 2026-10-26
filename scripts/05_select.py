"""Choose the best instance for every character (robust per-label medoid)."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
CELLS = WORK / "cells"
S = 48


def norm_glyph(path: Path):
    img = np.array(Image.open(path).convert("L"))
    # one decode per glyph: the sharpness term used to re-open the same PNG
    sharp = float(cv2.Laplacian(img.astype(np.float32), cv2.CV_32F).var())
    # binarize (glyph is dark on paper)
    thr = max(80, int(np.percentile(img, 50)) - 40)
    m = img < thr
    if m.sum() < 30:
        return None, None, None
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    h, w = y1 - y0, x1 - x0
    if h < 10 or w < 10:
        return None, None, None
    side = max(h, w) * 1.08
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    xa, ya = int(cx - side / 2), int(cy - side / 2)
    xb, yb = int(cx + side / 2), int(cy + side / 2)
    pad = max(0, -xa) + max(0, -ya) + max(0, xb - img.shape[1]) + max(0, yb - img.shape[0])
    if pad:
        img = cv2.copyMakeBorder(img, max(0, -ya), max(0, yb - img.shape[0]),
                                 max(0, -xa), max(0, xb - img.shape[1]),
                                 cv2.BORDER_CONSTANT, value=245)
        xa, ya, xb, yb = max(0, xa), max(0, ya), min(img.shape[1], xb), min(img.shape[0], yb)
    crop = img[ya:yb, xa:xb]
    if crop.size == 0:
        return None, None, None
    small = cv2.resize(crop, (S, S), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    return small, dict(w=int(w), h=int(h), fill=float(m.mean())), sharp


def sharpness(path: Path) -> float:
    img = np.array(Image.open(path).convert("L"), dtype=np.float32)
    return float(cv2.Laplacian(img, cv2.CV_32F).var())


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-samples", type=int, default=2,
                    help="drop characters whose label occurs fewer times (cannot be cross-validated)")
    ap.add_argument("--work", default=str(ROOT / "work"),
                    help="working directory (the B line uses work-b)")
    ap.add_argument("--drop-flag", default="",
                    help="drop rows whose named boolean field is truthy "
                         "(B line: low_align — cells on pages whose page-level "
                         "reference alignment failed, e.g. the 表 tables and the "
                         "library bookplate)")
    args = ap.parse_args()
    global CELLS
    wd = Path(args.work)
    CELLS = wd / "cells"
    rows = [json.loads(l) for l in open(wd / "labeled.jsonl")]
    rows = [r for r in rows if r["label"]]
    if args.drop_flag:
        n0 = len(rows)
        rows = [r for r in rows if not r.get(args.drop_flag)]
        print(f"dropped {n0-len(rows)} rows with {args.drop_flag}=true")
    groups = defaultdict(list)
    vecs = {}
    for _i, r in enumerate(rows):
        if _i and _i % 100000 == 0:
            print(f"  loaded {_i}/{len(rows)} cells", flush=True)
        p = CELLS / r["file"]
        v, meta, sharp = norm_glyph(p)
        if v is None:
            continue
        vecs[r["file"]] = v
        r["meta"] = meta
        r["sharp"] = sharp
        groups[r["label"]].append(r)
    print("labels", len(groups), "glyphs", len(vecs), flush=True)

    chosen = {}
    second = {}
    dropped = 0
    for lab, items in groups.items():
        if len(items) < args.min_samples:
            dropped += 1
            continue
        V = np.stack([vecs[r["file"]] for r in items])
        F = V.reshape(len(items), -1)
        # robust medoid: start from the mean, drop the worst 35%, recompute
        keep = np.ones(len(items), bool)
        for _ in range(3):
            mu = F[keep].mean(0)
            d = ((F - mu) ** 2).sum(1)
            thr = np.percentile(d[keep], 75)
            keep = d <= thr
        mu = F[keep].mean(0)
        d = ((F - mu) ** 2).sum(1)
        d = d / (d.max() + 1e-9)
        # quality term: prefer crisp, well-filled, square-ish glyphs
        q = np.array([r["sharp"] for r in items])
        q = np.clip(q / (np.percentile(q, 90) + 1e-9), 0, 1.5)
        m = np.array([min(r["meta"]["w"], r["meta"]["h"]) / max(r["meta"]["w"], r["meta"]["h"]) for r in items])
        # size prior: ink area relative to the character cell, penalise outliers
        size = np.array([(r["meta"]["w"] * r["meta"]["h"]) / max(1.0, r["pitch"]) ** 2 for r in items])
        med = float(np.median(size))
        sz = np.abs(size - med) / (med + 1e-6)
        red = np.array([r.get("redness", 0.0) for r in items])
        red = np.clip(red / 25.0, 0, 1)
        score = d - 0.25 * q - 0.15 * m + 0.35 * np.clip(sz, 0, 2) + 0.15 * red
        order = np.argsort(score)
        def build(i):
            r = dict(items[i])
            r["n_samples"] = len(items)
            r["medoid_dist"] = round(float(d[i]), 4)
            r["sharp"] = round(float(q[i]), 3)
            return r
        chosen[lab] = build(int(order[0]))
        if len(order) > 1:
            second[lab] = build(int(order[1]))
    print(f"chosen {len(chosen)} (dropped {dropped} labels with <{args.min_samples} samples)")
    with open(wd / "chosen.jsonl", "w") as f:
        for lab, r in sorted(chosen.items()):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(wd / "second.jsonl", "w") as f:
        for lab, r in sorted(second.items()):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts = sorted((v["n_samples"] for v in chosen.values()))
    print("sample count per char: min/median/max", counts[0], counts[len(counts) // 2], counts[-1])
    low = sorted(chosen.items(), key=lambda kv: kv[1]["n_samples"])[:30]
    print("rare:", [(k, v["n_samples"]) for k, v in low])


if __name__ == "__main__":
    main()
