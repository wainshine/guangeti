"""Page-level OCR with PP-OCR (rapidocr) for later cell labelling."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "四书白文.18卷.旧传明.姜立纲.pdf"

ENGINE = None


def get_engine():
    global ENGINE
    if ENGINE is None:
        from rapidocr import RapidOCR
        ENGINE = RapidOCR()
    return ENGINE


def process_page(args):
    page_no, dpi = args
    doc = pymupdf.open(PDF)
    pix = doc[page_no].get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
    e = get_engine()
    r = e(img)
    lines = []
    if r is not None and r.boxes is not None:
        for box, txt, sc in zip(r.boxes, r.txts, r.scores):
            lines.append(dict(box=[[float(x), float(y)] for x, y in box],
                              text=txt, score=float(sc)))
    return page_no, lines, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
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
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    t0 = time.time()
    out = []
    with ctx.Pool(args.workers) as pool:
        for i, (pno, lines, err) in enumerate(pool.imap_unordered(process_page, [(p, args.dpi) for p in pages])):
            if err:
                print("[ERR]", pno, err.splitlines()[-1])
            out.append(dict(page=pno, dpi=args.dpi, lines=lines))
            if i % 20 == 0:
                print(f"{i+1}/{len(pages)} {time.time()-t0:.0f}s", flush=True)
    out.sort(key=lambda r: r["page"])
    with open(ROOT / "work" / "ocr_pages.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("done", len(out))


if __name__ == "__main__":
    main()
