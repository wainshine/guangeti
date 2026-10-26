"""B-line stage 2: PP-OCRv6 transcription of the *rectified* 《史記》 pages.

OCR runs on the dewarped image so that its line boxes live in the same coordinate
system as the character cells (segmentation is done on the rectified page too).
Skipping the page-level rectify-and-scale dance that `04_label.py` needs keeps the
cell↔line mapping exact.

  python3 scripts/52_ocr_b.py --workers 8
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shiji_page import dewarp_page  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "史记.二十四册.传姜立纲抄本.新加坡国立大学藏.水印.pdf"
ENGINE = None


def get_engine():
    """Single-threaded onnxruntime: the concurrency budget is 8 workers x 1 thread."""
    global ENGINE
    if ENGINE is None:
        from rapidocr import RapidOCR
        ENGINE = RapidOCR(params={
            "EngineConfig.onnxruntime.intra_op_num_threads": 1,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        })
    return ENGINE


def process_page(args):
    page_no, dpi, dump = args
    cv2.setNumThreads(1)
    try:
        import os
        c0 = sum(os.times()[:2])
        doc = pymupdf.open(PDF)
        pix = doc[page_no].get_pixmap(dpi=dpi)
        rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
        warped = dewarp_page(rgb)["image"]
        if dump:
            Path(dump).mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(Path(dump) / f"p{page_no:04d}.png"), cv2.cvtColor(warped, cv2.COLOR_RGB2BGR))
        e = get_engine()
        r = e(warped)
        lines = []
        if r is not None and r.boxes is not None:
            for box, txt, sc in zip(r.boxes, r.txts, r.scores):
                lines.append(dict(box=[[float(x), float(y)] for x, y in box],
                                  text=txt, score=float(sc)))
        return page_no, lines, sum(os.times()[:2]) - c0
    except Exception:
        import traceback
        return page_no, [], traceback.format_exc()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="")
    ap.add_argument("--dpi", type=int, default=150,
                    help="OCR render dpi; the detector resizes to 2000 px anyway, so 150 "
                         "costs a third of the dewarp time for identical accuracy")
    ap.add_argument("--coord-scale", type=float, default=2.0,
                    help="multiply emitted boxes by this to reach the cell coordinate space")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=str(ROOT / "work-b" / "ocr_pages.jsonl"))
    ap.add_argument("--skip-empty", action="store_true", default=True,
                    help="skip pages whose segmentation produced no cells")
    ap.add_argument("--stats", default=str(ROOT / "work-b" / "page_stats.jsonl"))
    ap.add_argument("--dump-dir", default="")
    args = ap.parse_args()

    doc = pymupdf.open(PDF)
    n = doc.page_count
    if args.pages:
        pages = []
        for part in args.pages.split(","):
            if "-" in part:
                a, b = part.split("-")
                pages.extend(range(int(a), int(b) + 1))
            else:
                pages.append(int(part))
    else:
        pages = list(range(n))
    st = Path(args.stats)
    n_stats = sum(1 for _ in open(st)) if st.exists() else 0
    if args.skip_empty and n_stats >= 1000:
        keep = set()
        for line in open(st):
            r = json.loads(line)
            if r.get("cells", 0) > 0:
                keep.add(r["page"])
        skipped = [p for p in pages if p not in keep]
        pages = [p for p in pages if p in keep]
        print(f"skip {len(skipped)} pages with no cells: {skipped[:20]}", flush=True)
    elif args.skip_empty:
        print(f"WARNING: {st} has {n_stats} rows (<1000); not skipping any page", flush=True)

    tasks = [(p, args.dpi, args.dump_dir) for p in pages]
    t0 = time.time()
    out = []
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    cpu = 0.0
    with ctx.Pool(args.workers) as pool:
        for i, (pno, lines, cerr) in enumerate(pool.imap_unordered(process_page, tasks)):
            if isinstance(cerr, str):
                print("[ERR]", pno, cerr.splitlines()[-1], flush=True)
            else:
                cpu += cerr
            sc = args.coord_scale
            lines = [dict(box=[[x * sc, y * sc] for x, y in ln["box"]], text=ln["text"],
                          score=ln["score"]) for ln in lines]
            out.append(dict(page=pno, dpi=args.dpi, coord_scale=sc, lines=lines))
            if i % 20 == 0:
                print(f"{i+1}/{len(tasks)} {time.time()-t0:.0f}s", flush=True)
    out.sort(key=lambda r: r["page"])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    nlines = sum(len(r["lines"]) for r in out)
    wall = time.time() - t0
    print(f"done {len(out)} pages, {nlines} lines -> {args.out}")
    print(f"cpu {cpu:.0f}s / wall {wall:.0f}s = {cpu/max(1.0,wall):.2f} cores "
          f"(budget: {args.workers} workers x 1 thread)")


if __name__ == "__main__":
    main()
