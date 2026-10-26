#!/usr/bin/env python3
"""B line: the curated page-level figure `docs/images/book-vs-font-b.jpg`.

Left: a page of the manuscript (p1000, 《平原君虞卿列傳》) rendered from the PDF.
Right: the *same passage* typeset vertically with `GuanGeKai-B-Real.ttf`.

The figure is a manual asset (audit trail: it is not a pipeline product, so it is not
in the rebuild chain), but it does have to be regenerated whenever the real-glyph
font changes — the previous copy was made before the counter fix (E6).

  python3 scripts/72_book_vs_font_b.py --page 1000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from shiji_page import flatten, ink_mask, paper_mask  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "史记.二十四册.传姜立纲抄本.新加坡国立大学藏.水印.pdf"
COL = "#2b2b2b"
HL = "#8a6d3b"


def page_text(page: int, ncols: int = 4, nrows: int = 20) -> str:
    """The labels actually assigned to this page, in reading order."""
    rows = [json.loads(l) for l in open(ROOT / "work-b" / "labeled.jsonl")]
    rows = [r for r in rows if r["page"] == page and r.get("label")]
    rows.sort(key=lambda r: (-r["col"], r["row"]))
    cols = []
    for c in sorted({r["col"] for r in rows}, reverse=True)[:ncols]:
        chs = "".join(r["label"] for r in sorted(rows, key=lambda r: r["row"]) if r["col"] == c)
        if len(chs) >= nrows // 2:
            cols.append(chs[:nrows])
    return "\n".join(cols)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", type=int, default=1000)
    ap.add_argument("--height", type=int, default=1400)
    ap.add_argument("--out", default=str(ROOT / "docs/images/book-vs-font-b.jpg"))
    args = ap.parse_args()

    doc = pymupdf.open(PDF)
    pix = doc[args.page].get_pixmap(dpi=150)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)[:, :, :3].copy()
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    pm = paper_mask(g)
    ys, xs = np.where(pm)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    book = Image.fromarray(rgb[y0:y1, x0:x1])
    H = args.height
    book = book.resize((round(book.width * H / book.height), H), Image.LANCZOS)

    txt = page_text(args.page)
    ncol = txt.count("\n") + 1
    nrow = max(len(s) for s in txt.split("\n"))
    fs = int(H / (nrow + 0.6))
    font = ImageFont.truetype(str(ROOT / "build/GuanGeKai-B-Real.ttf"), fs)
    pad, gap = 40, 18
    pw = ncol * (fs + gap) + 2 * pad
    right = Image.new("RGB", (pw, H), "white")
    d = ImageDraw.Draw(right)
    for j, colstr in enumerate(txt.split("\n")):
        x = pw - pad - (j + 1) * (fs + gap) + gap // 2
        for i, ch in enumerate(colstr):
            d.text((x, pad * 0.4 + i * fs), ch, font=font, fill=COL, anchor="mt")

    top = 70
    capf = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 26)
    cap_r = "同段文字用 GuanGeKai-B-Real 豎排（4,070 真跡字之一部）"
    W = max(book.width + pw + 24, book.width + 40 + int(capf.getlength(cap_r)) + 20)
    out = Image.new("RGB", (W, H + top), "white")
    d = ImageDraw.Draw(out)
    d.text((16, 16), f"原書《史記》抄本 p{args.page}（《平原君虞卿列傳》）", font=capf, fill=COL)
    d.text((book.width + 40, 16), cap_r, font=capf, fill=HL)
    out.paste(book, (0, top))
    out.paste(right, (book.width + 24, top))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.save(args.out, "JPEG", quality=90, optimize=True, progressive=True)
    kb = Path(args.out).stat().st_size / 1e6
    print(f"figure -> {args.out}  {out.size}  {kb:.2f} MB  "
          f"passage {ncol} columns x {nrow} chars")


if __name__ == "__main__":
    main()
