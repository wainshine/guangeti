#!/usr/bin/env python3
"""B-Q12: per-cell horizontal squeeze (gutter compression).

The 史记 scan is a bound book: pages near the middle of a volume, and columns near the
gutter, are compressed horizontally.  The page dewarp (E1) only removes column bend/tilt,
so this distortion survives; `05_select` has no term for it.

squeeze(cell) = median ink aspect (w/h) of its column / median ink aspect of its page
    1.00 = normal, 0.85 = 15 % narrower than the rest of the page

  python3 scripts/85_squeeze_b.py --workers 8 --out work-b/squeeze_b.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def aspect(path: str) -> float | None:
    try:
        m = np.asarray(Image.open(path).convert("L")) > 127
    except Exception:  # noqa: BLE001
        return None
    ys, xs = np.nonzero(m)
    if len(xs) < 50:
        return None
    return float((xs.max() - xs.min() + 1) / max(1, (ys.max() - ys.min() + 1)))


def work(args):
    wd, chunk = args
    return [(c["file"], c["page"], c["col"], aspect(str(wd / "masks" / c["file"])))
            for c in chunk]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=str(ROOT / "work-b" / "squeeze_b.json"))
    args = ap.parse_args()
    if not 1 <= args.workers <= 8:
        ap.error("workers must be 1..8")

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    wd = ROOT / "work-b"
    cells = [json.loads(l) for l in open(wd / "cells.jsonl")]
    chunks = [(wd, cells[i::args.workers * 3]) for i in range(args.workers * 3)]
    vals: dict[str, float] = {}
    import multiprocessing as mp
    with mp.get_context("fork").Pool(args.workers) as pool:
        for part in pool.imap_unordered(work, chunks):
            for f, _p, _c, a in part:
                if a is not None:
                    vals[f] = a
    print(f"aspect for {len(vals)}/{len(cells)} cells", flush=True)

    bycol = collections.defaultdict(list)
    bypage = collections.defaultdict(list)
    meta = {}
    for c in cells:
        a = vals.get(c["file"])
        if a is None:
            continue
        bycol[(c["page"], c["col"])].append(a)
        bypage[c["page"]].append(a)
        meta[c["file"]] = (c["page"], c["col"])
    colmed = {k: float(np.median(v)) for k, v in bycol.items() if len(v) >= 5}
    pagemed = {p: float(np.median(v)) for p, v in bypage.items() if len(v) >= 20}

    chosen = [json.loads(l) for l in open(wd / "chosen.jsonl")]
    rows = []
    for r in chosen:
        k = meta.get(r["file"])
        if not k:
            continue
        cm, pm = colmed.get(k), pagemed.get(k[0])
        if not cm or not pm:
            continue
        rows.append({"char": r["label"], "file": r["file"], "page": k[0], "col": k[1],
                     "squeeze": round(cm / pm, 3)})
    rows.sort(key=lambda x: x["squeeze"])
    sq = np.array([r["squeeze"] for r in rows])
    res = {"n": len(rows),
           "n_below_0.90": int((sq < 0.90).sum()), "n_below_0.80": int((sq < 0.80).sum()),
           "n_below_0.70": int((sq < 0.70).sum()),
           "median": round(float(np.median(sq)), 3),
           "rows": rows}
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    # 全部 cell 的宽高比，供后续按样本比较（jsonl，一行一个）
    with open(str(args.out).replace(".json", "_aspects.jsonl"), "w") as fh:
        for f, a in vals.items():
            fh.write(json.dumps({"file": f, "page": meta.get(f, (None, None))[0],
                                 "col": meta.get(f, (None, None))[1], "aspect": round(a, 4)},
                                ensure_ascii=False) + "\n")
    print(f"chosen {len(rows)}: squeeze median {np.median(sq):.3f}; "
          f"<0.90 {(sq<0.90).sum()}, <0.80 {(sq<0.80).sum()}, <0.70 {(sq<0.70).sum()}")
    print("worst:", [(r["char"], r["squeeze"], f'p{r["page"]}c{r["col"]}') for r in rows[:12]])
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
