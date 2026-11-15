#!/usr/bin/env python3
"""B-Q13: label consistency — do the samples that carry the same label look like the same character?

A label error shows up as "several samples of one label disagree with each other": the
same codepoint should be the same character, so cross-sample IoU inside a label must be
much higher than across labels.  Pairwise IoU on bbox-normalised masks (8 samples per
label, seeded) gives a per-label consistency score without any OCR.

  python3 scripts/86_label_consistency_b.py --workers 8 --out work-b/label_consistency_b.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
S = 96
PER_LABEL = 8


def norm(path: str) -> np.ndarray | None:
    try:
        m = np.asarray(Image.open(path).convert("L")) > 127
    except Exception:  # noqa: BLE001
        return None
    ys, xs = np.nonzero(m)
    if len(xs) < 50:
        return None
    c = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    k = min(S / c.shape[0], S / c.shape[1])
    r = cv2.resize(c.astype(np.uint8), (max(1, int(c.shape[1] * k)), max(1, int(c.shape[0] * k))),
                   interpolation=cv2.INTER_NEAREST)
    out = np.zeros((S, S), np.uint8)
    y, x = (S - r.shape[0]) // 2, (S - r.shape[1]) // 2
    out[y:y + r.shape[0], x:x + r.shape[1]] = r
    return cv2.dilate(out, np.ones((3, 3), np.uint8)) > 0


def iou(a, b) -> float:
    return float((a & b).sum() / max(1, (a | b).sum()))


def work(args):
    wd, items = args
    out = []
    for lab, files in items:
        ms = [m for m in (norm(str(wd / "masks" / f)) for f in files) if m is not None]
        if len(ms) < 2:
            continue
        sc = [iou(ms[i], ms[j]) for i in range(len(ms)) for j in range(i + 1, len(ms))]
        sc = np.asarray(sc)
        out.append({"char": lab, "n": len(ms), "files": files,
                    "median": round(float(np.median(sc)), 3),
                    "p10": round(float(np.percentile(sc, 10)), 3),
                    "min": round(float(sc.min()), 3),
                    "frac_low": round(float((sc < 0.30).mean()), 3)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=str(ROOT / "work-b" / "label_consistency_b.json"))
    args = ap.parse_args()
    if not 1 <= args.workers <= 8:
        ap.error("workers must be 1..8")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    wd = ROOT / "work-b"
    by = collections.defaultdict(list)
    for line in open(wd / "labeled.jsonl"):
        r = json.loads(line)
        if r.get("label"):
            by[r["label"]].append(r["file"])
    rnd = random.Random(0)
    items = []
    for lab, files in by.items():
        files = sorted(files)
        if len(files) > PER_LABEL:
            files = rnd.sample(files, PER_LABEL)
        items.append((lab, files))
    print(f"{len(items)} labels, up to {PER_LABEL} samples each", flush=True)

    import multiprocessing as mp
    chunks = [items[i::args.workers * 2] for i in range(args.workers * 2)]
    rows = []
    with mp.get_context("fork").Pool(args.workers) as pool:
        for part in pool.imap_unordered(work, [(wd, c) for c in chunks]):
            rows.extend(part)
    rows.sort(key=lambda r: r["median"])
    med = np.array([r["median"] for r in rows])
    res = {"n_labels": len(rows), "median_of_medians": round(float(np.median(med)), 3),
           "labels_below_0.40": int((med < 0.40).sum()),
           "labels_below_0.30": int((med < 0.30).sum()),
           "rows": rows}
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"labels {len(rows)}; median IoU of label-medians {np.median(med):.3f}; "
          f"<0.40 {(med<0.40).sum()}, <0.30 {(med<0.30).sum()}")
    print("worst:", [(r["char"], r["median"], r["frac_low"]) for r in rows[:12]])
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
