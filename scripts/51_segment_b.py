"""B-line stage 1: rectify each 《史記》 spread, then cut character cells.

Differs from `01_segment.py` in exactly two ways:
  * every page is dewarped first (scripts/shiji_page.py) — per-leaf skew + per-column
    straightening + fold-shadow flattening;
  * the data-side constants are rescaled for this scan (native 150 dpi, character
    pitch ~186 px at 300 dpi, i.e. s = pitch/310 = 0.6).

Outputs (all under --out, default work-b/):
  cells/pXXXX_cYY_rZZ.png   grayscale crop, neighbours masked out
  masks/pXXXX_cYY_rZZ.png   binary mask of exactly this cell's components
  cells.jsonl               one row per cell
  page_stats.jsonl          one row per page (fold position, skew, cells, timings)
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pageproc import analyze_page  # noqa: E402
from shiji_page import dewarp_page, flatten, ink_mask, paper_mask  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "史记.二十四册.传姜立纲抄本.新加坡国立大学藏.水印.pdf"


def process_page(args):
    page_no, dpi, outdir, pad, maskdir, s, plo, phi, dump, bfrac = args
    outdir, maskdir = Path(outdir), Path(maskdir)
    cv2.setNumThreads(1)
    try:
        doc = pymupdf.open(PDF)
        t0 = time.time()
        pix = doc[page_no].get_pixmap(dpi=dpi)
        rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
        dw = dewarp_page(rgb)
        warped, info = dw["image"], dw["info"]
        t1 = time.time()
        if dump:
            Path(dump).mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(Path(dump) / f"p{page_no:04d}.png"), cv2.cvtColor(warped, cv2.COLOR_RGB2BGR))
        # The scan carries a grey NUS watermark along the bottom edge; a global Otsu
        # threshold classifies it as ink.  Use a paper-relative threshold instead.
        gray = cv2.cvtColor(warped, cv2.COLOR_RGB2GRAY)
        pm = paper_mask(gray)
        ink = ink_mask(warped, flatten(gray, pm), pm)
        # --- dewarp acceptance gate (audit 2-4).  The survey showed a few leaves
        # missing the 1.5 px@100dpi / 1.5x near-spine ratio target, yet their cells
        # went straight into the pipeline with no mark.  Flag them so the selection
        # stage can drop or down-weight them.
        after = info.get("after") or []
        res300 = [a.get("res_med", 0.0) for a in after if a.get("n")]
        dew_fail = False
        dew_why = ""
        if res300:
            worst = max(res300)
            if worst / 3.0 > 1.5:            # px@100dpi
                dew_fail = True
                dew_why = f"residual {worst/3.0:.2f}px@100dpi"
            lo = max(1e-6, min(res300))
            if len(res300) > 1 and worst / lo > 1.5:
                dew_fail = True
                dew_why = (dew_why + ";" if dew_why else "") + \
                          f"leaf ratio {worst/lo:.2f}x"
        res = analyze_page(warped, s=s, pitch_range=(plo, phi), deskew=False,
                           block_frac=bfrac, mask=ink)
        mask, lab = res["mask"], res["lab"]
        pitch = res["pitch"]
        rows = []
        for c in res["cells"]:
            x0, y0, x1, y1 = c["x0"], c["y0"], c["x1"], c["y1"]
            w, h = x1 - x0, y1 - y0
            if (w < pitch * 0.28 and h < pitch * 0.28) or w > pitch * 1.8 or h > pitch * 1.8:
                continue
            if c["ink"] < 0.025:
                continue
            m = lab[y0:y1, x0:x1] > 0
            if not m.any():
                continue
            gx0, gy0 = max(0, x0 - pad), max(0, y0 - pad)
            gx1, gy1 = min(gray.shape[1], x1 + pad), min(gray.shape[0], y1 + pad)
            crop = gray[gy0:gy1, gx0:gx1].copy()
            msub = np.isin(lab[y0:y1, x0:x1], c["comp_ids"]).astype(np.uint8) * 255
            mfull = np.zeros_like(crop)
            mfull[(y0 - gy0):(y1 - gy0), (x0 - gx0):(x1 - gx0)] = msub
            name = f"p{page_no:04d}_c{c['col']:02d}_r{c['row']:02d}.png"
            Image.fromarray(crop).save(outdir / name, compress_level=6)
            Image.fromarray(mfull).save(maskdir / name, compress_level=6)
            rows.append(dict(
                file=name, page=page_no, col=c["col"], row=c["row"],
                x0=x0, y0=y0, x1=x1, y1=y1, w=w, h=h,
                ink=round(c["ink"], 4), redness=0.0,
                slot=(c["slot_y0"], c["slot_y1"]),
                angle=0.0, pitch=round(pitch, 1),
                dewarp_fail=dew_fail, dewarp_why=dew_why,
            ))
        stat = dict(page=page_no, dewarp_fail=dew_fail, dewarp_why=dew_why,
                    dewarp_res100=[round(r / 3.0, 2) for r in res300],
                    shape=[int(warped.shape[0]), int(warped.shape[1])],
                    fold=info.get("fold"), fold_depth=info.get("fold_depth"),
                    leaves=len(info.get("leaves", [])), n_cols=info.get("n_cols"),
                    pitch=round(pitch, 1), cells=len(rows),
                    max_shift=info.get("max_shift_px"),
                    t_dewarp=round(t1 - t0, 2), t_all=round(time.time() - t0, 2))
        return page_no, rows, stat, None
    except Exception:
        import traceback
        return page_no, [], {}, traceback.format_exc()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="")
    ap.add_argument("--dpi", type=int, default=300, help="render dpi (native scan is 150)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=str(ROOT / "work-b"))
    ap.add_argument("--pad", type=int, default=8)
    ap.add_argument("--scale", type=float, default=0.6,
                    help="glyph-pitch scale vs the 四書 300 dpi calibration (310 px)")
    ap.add_argument("--pitch-lo", type=int, default=110)
    ap.add_argument("--pitch-hi", type=int, default=260)
    ap.add_argument("--block-frac", type=float, default=0.14,
                    help="text-block density threshold; lower keeps short columns "
                         "(the 卷末 date column often has 3-4 characters)")
    ap.add_argument("--dump-dir", default="", help="optionally save the rectified page images")
    args = ap.parse_args()

    out = Path(args.out)
    cells_dir = out / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    mask_dir = out / "masks"
    mask_dir.mkdir(parents=True, exist_ok=True)

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

    tasks = [(p, args.dpi, cells_dir, args.pad, str(mask_dir), args.scale,
              args.pitch_lo, args.pitch_hi, args.dump_dir, args.block_frac) for p in pages]
    t0 = time.time()
    all_rows, stats = [], []
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ctx.Pool(args.workers) as pool:
        for i, (pno, rows, stat, err) in enumerate(pool.imap_unordered(process_page, tasks)):
            if err:
                print(f"[ERR] page {pno}: {err.splitlines()[-1]}", flush=True)
            all_rows.extend(rows)
            if stat:
                stats.append(stat)
            if i % 20 == 0:
                print(f"{i+1}/{len(tasks)} pages, {len(all_rows)} cells, "
                      f"{time.time()-t0:.0f}s", flush=True)
    all_rows.sort(key=lambda r: (r["page"], r["col"], r["row"]))
    with open(out / "cells.jsonl", "w") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    stats.sort(key=lambda r: r["page"])
    with open(out / "page_stats.jsonl", "w") as f:
        for r in stats:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    pitches = [r["pitch"] for r in stats if r.get("cells")]
    print(f"done: {len(all_rows)} cells from {len(stats)} pages in {time.time()-t0:.0f}s")
    if pitches:
        print(f"pitch: median {np.median(pitches):.1f} "
              f"p10 {np.percentile(pitches,10):.1f} p90 {np.percentile(pitches,90):.1f}")
    print("->", out / "cells.jsonl")


if __name__ == "__main__":
    main()
