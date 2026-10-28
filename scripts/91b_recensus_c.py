"""C-line stage 1b: recompute page geometry from the cached 150 dpi copies.

`91_render_c.py` stores both the rectified copy and the census row, so when the rule
detector improves there is no reason to re-render the PDFs (10 GB of writes).  This
utility re-reads `pages150/*.jpg`, re-runs rule detection and the content classifier,
and merges the new geometry into `page_stats.jsonl`.  The deskew angle is kept: the
cached JPEG is already rectified.

  python3 scripts/91b_recensus_c.py --workers 6
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yongle_page import detect_rules, red_masks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"


def one(task):
    key, path, angle = task
    cv2.setNumThreads(1)
    img = cv2.imread(str(path))
    if img is None:
        return key, None, "cannot read"
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    try:
        rules = detect_rules(rgb, dpi=150)
    except Exception:
        import traceback
        return key, None, traceback.format_exc()
    h, w = gray.shape
    x0, y0, x1, y1 = rules["frame"]
    band = gray[max(0, y0):max(1, y1), max(0, x0):max(1, x1)]
    p2, p50 = (np.percentile(band, 2), np.percentile(band, 50)) if band.size else (0.0, 200.0)
    thr = p2 + 0.34 * max(1.0, p50 - p2)
    ink_frac = float((band < thr).mean()) if band.size else 0.0
    dark_leaf = bool(p50 < 120)
    n_lines = len(rules["lines"])
    pitch = float(rules["pitch"])
    content = "text"
    if dark_leaf:
        content = "cover"
    elif ink_frac < 0.004 or n_lines < 2 or pitch < 40:
        content = "blank"
    return key, dict(content=content, pitch150=round(pitch, 1), n_lines=n_lines,
                     frame=[int(v) for v in rules["frame"]],
                     ink_frac=round(ink_frac, 5),
                     red_frac=round(float(red_masks(rgb)[1].mean()), 5)), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(WORK / "page_stats.jsonl")]
    tasks = [(r["key"], WORK / "pages150" / (r["key"] + ".jpg"), r["angle"]) for r in rows]
    t0 = time.time()
    upd = {}
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    changed = 0
    with ctx.Pool(args.workers) as pool:
        for i, (key, d, err) in enumerate(pool.imap_unordered(one, tasks)):
            if err:
                print(f"[ERR] {key}: {err.splitlines()[-1]}", flush=True)
                continue
            if d:
                upd[key] = d
            if i % 200 == 0:
                print(f"{i}/{len(tasks)} {time.time()-t0:.0f}s", flush=True)
    for r in rows:
        d = upd.get(r["key"])
        if not d:
            continue
        if d["content"] != r["content"]:
            changed += 1
        r.update(d)
    with open(WORK / "page_stats.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"updated {len(upd)} pages ({changed} content reclassed) in {time.time()-t0:.0f}s")
    print(Counter(r["content"] for r in rows))


if __name__ == "__main__":
    main()
