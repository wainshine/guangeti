"""C-line Phase 0: cheap census of every page in the 41 永乐大典 PDFs.

For each page it renders at a low dpi, separates red (朱丝栏 + 句读) from black ink,
and records the quantities that decide the segmentation strategy:

  page size / embedded image size      -> effective dpi
  red_frac                             -> is the red frame present at all
  ink_frac, text bbox                  -> is this a text page (vs cover / blank)
  n_vlines, col_pitch                  -> column geometry
  char_pitch (ink autocorrelation)     -> character advance
  sharpness                            -> scan quality
  big_dark_frac                        -> damage / stains / dark cover

Output: work-c/page_survey.jsonl (one row per page).

  python3 scripts/90_survey_c.py --workers 6
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "永乐大典美国藏本"


def red_mask(rgb: np.ndarray, th: int = 16) -> np.ndarray:
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    return ((r - g) > th) & ((r - b) > th)


def peak_pitch(profile: np.ndarray, lo: int, hi: int) -> float:
    """Dominant period of a 1-D profile (autocorrelation, parabolic refinement)."""
    q = profile.astype(np.float64)
    q = q - q.mean()
    if not np.any(q):
        return 0.0
    ac = np.correlate(q, q, "full")[len(q) - 1:]
    ac /= ac[0] + 1e-9
    hi = min(hi, len(ac) - 2)
    if hi <= lo + 2:
        return 0.0
    k = lo + int(np.argmax(ac[lo:hi]))
    if 0 < k < len(ac) - 1:
        y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-9:
            k = k + 0.5 * (y0 - y2) / den
    return float(k)


def analyse(rgb: np.ndarray, dpi: int):
    h, w = rgb.shape[:2]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    red = red_mask(rgb)
    red_frac = float(red.mean())
    # ink = dark and not red; a light red line must not count as ink
    pos = float(np.percentile(gray, 50))
    p2 = float(np.percentile(gray, 2))
    thr = p2 + 0.35 * max(1.0, pos - p2)
    ink = (gray < thr) & ~red
    ink_frac = float(ink.mean())

    # text block: central rows/cols carrying most of the ink
    if ink.any():
        d = cv2.blur(ink.astype(np.float32), (max(9, w // 12) | 1, max(9, h // 12) | 1))
        rows, cols = d.sum(1), d.sum(0)
        fy = np.flatnonzero(rows > rows.max() * 0.25)
        fx = np.flatnonzero(cols > cols.max() * 0.25)
        bbox = [int(fx[0]) / w, int(fy[0]) / h, (int(fx[-1]) + 1) / w, (int(fy[-1]) + 1) / h] \
            if len(fx) and len(fy) else [0, 0, 1, 1]
    else:
        bbox = [0, 0, 1, 1]

    # vertical red rules: column-wise red coverage inside the text block
    y0, y1 = int(bbox[1] * h), int(bbox[3] * h)
    x0, x1 = int(bbox[0] * w), int(bbox[2] * w)
    band = red[max(0, y0):max(1, y1), :]
    vprof = band.sum(0).astype(np.float64) / max(1, band.shape[0])
    # a rule covers most of the band; red 句读 circles cover a few percent
    n_vlines = int((vprof > 0.55).sum())
    # group adjacent columns so a 3-px line counts once
    on = vprof > 0.55
    edges = np.flatnonzero(np.diff(on.astype(np.int8)) == 1) + 1
    if on.size and on[0]:
        edges = np.r_[0, edges]
    n_vlines = int(len(edges))

    col_pitch = peak_pitch(vprof, max(30, int(w * 0.02)), max(60, int(w * 0.25)))
    ink_prof = ink[:, max(0, x0):max(1, x1)].sum(1).astype(np.float64)
    char_pitch = peak_pitch(ink_prof, max(16, int(h * 0.008)), max(40, int(h * 0.12)))

    # damage: very dark blobs that are not thin strokes
    dark = (gray < max(60, p2 + 25)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(dark, 8)
    big = 0
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        ww, hh = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
        if a > 0.01 * w * h and min(ww, hh) > 40:
            big += int(a)
    sharp = float(cv2.Laplacian(gray, cv2.CV_32F).var())

    return dict(shape=[int(h), int(w)], red_frac=round(red_frac, 5),
                ink_frac=round(ink_frac, 5), bbox=[round(v, 4) for v in bbox],
                n_vlines=n_vlines, col_pitch=round(col_pitch, 1),
                char_pitch=round(char_pitch, 1), sharp=round(sharp, 1),
                big_dark_frac=round(big / max(1, w * h), 5), dpi=dpi)


def process_pdf(task):
    pdf, dpi = task
    cv2.setNumThreads(1)
    rows = []
    try:
        doc = pymupdf.open(pdf)
        for pno in range(doc.page_count):
            page = doc[pno]
            rect = page.rect
            pix = page.get_pixmap(dpi=dpi)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n)[:, :, :3]
            st = analyse(rgb, dpi)
            imgs = page.get_images(full=True)
            iw, ih = (imgs[0][2], imgs[0][3]) if imgs else (0, 0)
            # effective dpi of the embedded raster against the page box
            edpi = round(max(iw / max(1.0, rect.width / 72.0),
                             ih / max(1.0, rect.height / 72.0)), 1) if iw else 0.0
            st.update(pdf=Path(pdf).name, page=pno,
                      page_wh=[round(rect.width, 1), round(rect.height, 1)],
                      img_wh=[iw, ih], eff_dpi=edpi)
            rows.append(st)
        doc.close()
    except Exception:
        import traceback
        return Path(pdf).name, rows, traceback.format_exc()
    return Path(pdf).name, rows, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=str(ROOT / "work-c" / "page_survey.jsonl"))
    ap.add_argument("--pdfs", default="")
    args = ap.parse_args()
    files = sorted(glob.glob(str(CORPUS / "*.pdf")))
    if args.pdfs:
        keep = set(args.pdfs.split(","))
        files = [f for f in files if any(k in f for k in keep)]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    tasks = [(f, args.dpi) for f in files]
    t0 = time.time()
    out = []
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ctx.Pool(args.workers) as pool:
        for i, (name, rows, err) in enumerate(pool.imap_unordered(process_pdf, tasks)):
            if err:
                print(f"[ERR] {name}: {err.splitlines()[-1]}", flush=True)
            out.extend(rows)
            print(f"{i+1}/{len(tasks)} {name[:30]} {len(rows)} pages "
                  f"{time.time()-t0:.0f}s", flush=True)
    out.sort(key=lambda r: (r["pdf"], r["page"]))
    with open(args.out, "w") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"done {len(out)} pages -> {args.out} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
