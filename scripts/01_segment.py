"""Batch glyph-cell extraction from the PDF.

Outputs:
  work/cells/pXXXX_cYY_rZZ.png   grayscale glyph crops (neighbours masked out)
  work/cells.jsonl               metadata (one row per cell)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from pageproc import analyze_page  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "四书白文.18卷.旧传明.姜立纲.pdf"


def process_page(args):
    page_no, dpi, outdir, pad = args
    try:
        doc = pymupdf.open(PDF)
        page = doc[page_no]
        pix = page.get_pixmap(dpi=dpi)
        rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
        res = analyze_page(rgb)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        mask, lab = res["mask"], res["lab"]
        rows = []
        pitch = res["pitch"]
        for c in res["cells"]:
            x0, y0, x1, y1 = c["x0"], c["y0"], c["x1"], c["y1"]
            w, h = x1 - x0, y1 - y0
            if w < pitch * 0.28 and h < pitch * 0.28:
                continue
            if w > pitch * 1.8 or h > pitch * 1.8:
                continue
            if c["ink"] < 0.025:
                continue
            sub_rgb = rgb[y0:y1, x0:x1]
            m = lab[y0:y1, x0:x1] > 0
            if not m.any():
                continue
            px = sub_rgb[m].astype(np.int16)
            redness = float((px[:, 0] - (px[:, 1] + px[:, 2]) / 2).mean())
            if redness > 18:
                continue
            gx0, gy0 = max(0, x0 - pad), max(0, y0 - pad)
            gx1, gy1 = min(gray.shape[1], x1 + pad), min(gray.shape[0], y1 + pad)
            crop = gray[gy0:gy1, gx0:gx1].copy()
            name = f"p{page_no:04d}_c{c['col']:02d}_r{c['row']:02d}.png"
            Image.fromarray(crop).save(outdir / name, compress_level=6)
            rows.append(dict(
                file=name, page=page_no, col=c["col"], row=c["row"],
                x0=x0, y0=y0, x1=x1, y1=y1, w=w, h=h,
                ink=round(c["ink"], 4), redness=round(redness, 2),
                slot=(c["slot_y0"], c["slot_y1"]),
                angle=round(res["angle"], 3), pitch=round(pitch, 1),
            ))
        return page_no, rows, None
    except Exception:
        import traceback
        return page_no, [], traceback.format_exc()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=str(ROOT / "work"))
    args = ap.parse_args()

    out = Path(args.out)
    cells_dir = out / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    if args.pages:
        pages = []
        for part in args.pages.split(","):
            if "-" in part:
                a, b = part.split("-")
                pages.extend(range(int(a), int(b) + 1))
            else:
                pages.append(int(part))
    else:
        pages = list(range(410))

    tasks = [(p, args.dpi, cells_dir, 6) for p in pages]
    t0 = time.time()
    all_rows = []
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ctx.Pool(args.workers) as pool:
        for i, (pno, rows, err) in enumerate(pool.imap_unordered(process_page, tasks)):
            if err:
                print(f"[ERR] page {pno}: {err.splitlines()[-1]}")
            all_rows.extend(rows)
            if i % 20 == 0:
                print(f"{i+1}/{len(tasks)} pages, {len(all_rows)} cells, {time.time()-t0:.0f}s", flush=True)
    all_rows.sort(key=lambda r: (r["page"], r["col"], r["row"]))
    with open(out / "cells.jsonl", "w") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"done: {len(all_rows)} cells in {time.time()-t0:.0f}s -> {out/'cells.jsonl'}")


if __name__ == "__main__":
    main()
