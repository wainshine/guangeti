"""Render glyph pairs (book raster vs font glyph).

NOTE: do NOT overwrite book-vs-font.png — that is a curated page-level figure
(book page on the left, the same passage typeset with this font on the right).
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
S = 256


def main():
    d = np.load(ROOT / "work/pairs/pairs.npz", allow_pickle=True)
    chars = [str(c) for c in d["chars"]]
    Y = d["Y"]
    font = ImageFont.truetype(str(ROOT / "build/GuanGeKai-Regular.ttf"), S)
    rng = np.random.RandomState(7)
    sel = [chars[i] for i in rng.choice(len(chars), 8, replace=False)]
    sheet = Image.new("L", (S * len(sel), S * 2), 0)
    for j, ch in enumerate(sel):
        i = chars.index(ch)
        sheet.paste(Image.fromarray(Y[i]), (j * S, 0))
        im = Image.new("L", (S, S), 0)
        ImageDraw.Draw(im).text((0, 880 * S / 1000), ch, fill=255, font=font, anchor="ls")
        sheet.paste(im, (j * S, S))
    out = ROOT / "docs" / "images" / "glyph-pairs.png"
    sheet.resize((S * len(sel) // 2, S)).save(out)
    print("figure ->", out, "chars:", "".join(sel))


if __name__ == "__main__":
    main()
