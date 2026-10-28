"""C-line stage 1: page census + rectified 150 dpi copies for OCR.

Until now the 大典 corpus had only been described from a handful of leaves.  This
stage walks all 3,538 pages and records, per page, the quantities segmentation
depends on:

  * deskew angle, measured on the red rules (the rules are the only reliable straight
    feature on these leaves; paper edges are trimmed unevenly);
  * column pitch and the 朱丝栏 frame from the red mask;
  * a content class (text / blank / cover) so blank versos and bindings never reach
    OCR;
  * ink and red coverage, effective dpi of the embedded raster.

It also writes a rectified 150 dpi JPEG per page.  OCR runs on that copy, so the
150 dpi OCR boxes and the 300 dpi segmentation share one coordinate system exactly
(p300 = 2 * p150, both after the same rotation).  Keeping the 300 dpi pages on disk
cost ~70 GB; re-rendering them in stage 3 costs 20 minutes, so only the 150 copy is
kept.

  python3 scripts/91_render_c.py --workers 6
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yongle_page import deskew, detect_rules, red_masks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "永乐大典美国藏本"
WORK = ROOT / "work-c"


def book_key(pdf: Path) -> str:
    """Stable short id from the volume number, e.g. 卷10934-10935 -> 10934_10935."""
    try:
        return pdf.stem.split(".")[1].replace("卷", "").replace("-", "_")
    except IndexError:
        return pdf.stem[:12]


def process_pdf(task):
    pdf, idx, pages = task
    pdf = Path(pdf)
    cv2.setNumThreads(1)
    rows, err = [], None
    try:
        doc = pymupdf.open(pdf)
        for pno in pages:
            page = doc[pno]
            t0 = time.time()
            pix = page.get_pixmap(dpi=150)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n)[:, :, :3].copy()
            rect = page.rect
            imgs = page.get_images(full=True)
            iw, ih = (imgs[0][2], imgs[0][3]) if imgs else (0, 0)
            eff_dpi = round(max(iw / max(1.0, rect.width / 72.0),
                                ih / max(1.0, rect.height / 72.0)), 1) if iw else 0.0
            rgb, angle = deskew(rgb)
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            rules = detect_rules(rgb, dpi=150)
            h, w = gray.shape
            x0, y0, x1, y1 = rules["frame"]
            band = gray[max(0, y0):max(1, y1), max(0, x0):max(1, x1)]
            p2, p50 = (np.percentile(band, 2), np.percentile(band, 50)) if band.size \
                else (0.0, 200.0)
            dark_leaf = bool(p50 < 120)
            thr = p2 + 0.34 * max(1.0, p50 - p2)
            ink_frac = float((band < thr).mean()) if band.size else 0.0
            red_frac = float(red_masks(rgb)[1].mean())
            n_lines = len(rules["lines"])
            pitch = float(rules["pitch"])
            content = "text"
            if dark_leaf:
                content = "cover"
            elif ink_frac < 0.004 or n_lines < 2 or pitch < 40:
                content = "blank"
            name = f"p{idx:02d}_{pno:04d}"
            cv2.imwrite(str(WORK / "pages150" / (name + ".jpg")),
                        cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            rows.append(dict(
                key=name, book=pdf.name, book_idx=idx, page=pno, content=content,
                angle=round(float(angle), 3), shape=[int(h), int(w)],
                page_wh=[round(rect.width, 1), round(rect.height, 1)], eff_dpi=eff_dpi,
                img_wh=[iw, ih], pitch150=round(pitch, 1), n_lines=n_lines,
                frame=[int(v) for v in rules["frame"]],
                ink_frac=round(ink_frac, 5), red_frac=round(red_frac, 5),
                t=round(time.time() - t0, 2)))
        doc.close()
    except Exception:
        import traceback
        err = traceback.format_exc()
    return pdf.name, rows, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=str(WORK))
    ap.add_argument("--pdfs", default="")
    ap.add_argument("--pages", default="")
    ap.add_argument("--chunk", type=int, default=8)
    args = ap.parse_args()
    work = Path(args.out)
    (work / "pages150").mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(str(CORPUS / "*.pdf")))
    if args.pdfs:
        keep = args.pdfs.split(",")
        files = [f for f in files if any(k in f for k in keep)]
    tasks = []
    for idx, f in enumerate(files):
        doc = pymupdf.open(f)
        n = doc.page_count
        doc.close()
        pages = list(range(n))
        if args.pages:
            sel = []
            for part in args.pages.split(","):
                if "-" in part:
                    a, b = part.split("-")
                    sel.extend(range(int(a), int(b) + 1))
                else:
                    sel.append(int(part))
            pages = [p for p in pages if p in set(sel)]
        for i in range(0, len(pages), args.chunk):
            tasks.append((f, idx, pages[i:i + args.chunk]))

    t0 = time.time()
    rows = []
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ctx.Pool(args.workers) as pool:
        for i, (name, rr, err) in enumerate(pool.imap_unordered(process_pdf, tasks)):
            if err:
                print(f"[ERR] {name}: {err.splitlines()[-1]}", flush=True)
            rows.extend(rr)
            if i % 25 == 0:
                print(f"{i}/{len(tasks)} chunks, {len(rows)} pages, {time.time()-t0:.0f}s",
                      flush=True)
    rows.sort(key=lambda r: (r["book_idx"], r["page"]))
    outp = work / "page_stats.jsonl"
    old = [json.loads(l) for l in open(outp)] if outp.exists() else []
    have = {(r["book_idx"], r["page"]) for r in rows}
    rows = sorted([r for r in old if (r["book_idx"], r["page"]) not in have] + rows,
                  key=lambda r: (r["book_idx"], r["page"]))
    with open(outp, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_text = sum(1 for r in rows if r["content"] == "text")
    print(f"done {len(rows)} pages ({n_text} text, {len(rows)-n_text} blank/cover) "
          f"in {time.time()-t0:.0f}s -> {outp}")


if __name__ == "__main__":
    main()
