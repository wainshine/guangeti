#!/usr/bin/env python3
"""B-Q14: contaminated cells — samples whose ink is not the labelled character.

`08_make_pairs` builds training pairs from **chosen** only (one sample per character), so
contaminated siblings do not pollute training directly.  They matter because `05_select`
picks the medoid from the whole pool: a contaminated cell can win and ship as the glyph
(that is how 茈 -> 此, 竅 -> 敷, 簦 -> 落 happened).

This script flags, per label, the samples whose median bbox-normalised IoU against the
label's other samples is below --thr.  The output is meant as an exclusion list for the
next selection run (needs 05_select to accept it; see the note in DATA-B).

  python3 scripts/87_contaminated_cells_b.py --workers 8 --out work-b/contaminated_b.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
S = 96
CAP = 40          # samples per label used for the consistency estimate


def norm(path: Path) -> np.ndarray | None:
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


def work(args):
    wd, thr, items = args
    flagged, seen = [], 0
    for lab, files in items:
        ms = []
        for f in files:
            m = norm(wd / "masks" / f)
            if m is not None:
                ms.append((f, m))
        if len(ms) < 3:
            continue
        seen += len(ms)
        for i, (f, m) in enumerate(ms):
            sc = [(m & m2).sum() / max(1, (m | m2).sum()) for j, (f2, m2) in enumerate(ms) if j != i]
            med = float(np.median(sc))
            if med < thr:
                flagged.append({"label": lab, "file": f, "iou": round(med, 3), "n": len(ms)})
    return flagged, seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--thr", type=float, default=0.30)
    ap.add_argument("--out", default=str(ROOT / "work-b" / "contaminated_b.json"))
    args = ap.parse_args()
    if not 1 <= args.workers <= 8:
        ap.error("workers must be 1..8")
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(k, "1")

    wd = ROOT / "work-b"
    by = collections.defaultdict(list)
    for line in open(wd / "labeled.jsonl"):
        r = json.loads(line)
        if r.get("label"):
            by[r["label"]].append(r["file"])
    items = [(lab, sorted(files)[:CAP]) for lab, files in by.items() if len(files) >= 3]
    print(f"{len(items)} labels with >=3 samples (cap {CAP})", flush=True)

    import multiprocessing as mp
    chunks = [items[i::args.workers * 2] for i in range(args.workers * 2)]
    flagged, seen = [], 0
    with mp.get_context("fork").Pool(args.workers) as pool:
        for fl, sn in pool.imap_unordered(work, [(wd, args.thr, c) for c in chunks]):
            flagged.extend(fl)
            seen += sn
    flagged.sort(key=lambda r: r["iou"])
    res = {"threshold": args.thr, "sampled_cells": seen, "flagged": len(flagged),
           "flagged_frac": round(len(flagged) / max(1, seen), 4),
           "labels_affected": len({r["label"] for r in flagged}), "cells": flagged}
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"sampled {seen} cells; flagged {len(flagged)} ({len(flagged)/max(1,seen):.1%}) "
          f"across {res['labels_affected']} labels")
    print("worst:", [(r["label"], r["iou"]) for r in flagged[:10]])
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
