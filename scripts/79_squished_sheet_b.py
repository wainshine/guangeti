#!/usr/bin/env python3
"""Review sheet for the squished glyphs that have no accepted replacement (B-Q12).

Left: the sample currently used (compressed column).  Middle: the most upright
alternative among the character's other samples (blank when there is none).
Right: the shipped glyph.
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"
COLS, CW, CH, PER = 5, 420, 300, 50


def main():
    rows = json.load(open(ROOT / "work-b" / "squished_39.json"))
    alt = {r["char"]: r.get("alt") for r in rows}
    sq = {r["char"]: r["squeeze"] for r in rows}
    chosen = {json.loads(l)["label"]: json.loads(l) for l in open(ROOT / "work-b" / "chosen.jsonl")}
    lab = ImageFont.truetype(str(REF), 13)
    out = ROOT / "work-b" / "qa" / "review-b-squished"; out.mkdir(parents=True, exist_ok=True)
    pages = [rows[i:i + PER] for i in range(0, len(rows), PER)]
    for pi, page in enumerate(pages):
        nrows = max(1, (len(page) + COLS - 1) // COLS)
        S = Image.new("RGB", (COLS * CW, nrows * CH), (255, 255, 255)); d = ImageDraw.Draw(S)
        for i, r in enumerate(page):
            x, y = (i % COLS) * CW, (i // COLS) * CH
            d.rectangle([x, y, x + CW - 1, y + CH - 1], outline=(215, 215, 215))
            cur = Image.open(ROOT / "work-b" / "cells" / chosen[r["char"]]["file"]).convert("L")
            cur.thumbnail((120, 120)); S.paste(cur, (x + 6, y + 16))
            d.text((x + 6, y + 2), "当前(压)", font=lab, fill=(150, 150, 150))
            a = r.get("alt")
            if a:
                im = Image.open(ROOT / "work-b" / "cells" / a).convert("L")
                im.thumbnail((120, 120)); S.paste(im, (x + 140, y + 16))
                d.text((x + 140, y + 2), "备选", font=lab, fill=(0, 110, 200))
            f = ImageFont.truetype(str(ROOT / "build" / "GuanGeKai-B-Real.ttf"), 100)
            g = Image.new("L", (120, 120), 255)
            ImageDraw.Draw(g).text((60, 108), r["char"], font=f, fill=0, anchor="ms")
            S.paste(g, (x + 274, y + 16))
            d.text((x + 274, y + 2), "成品", font=lab, fill=(0, 0, 0))
            d.text((x + 6, y + 146), r["char"], font=lab, fill=(0, 0, 0))
            d.text((x + 6, y + 166), f"squeeze {sq[r['char']]:.2f}  n={r['n_samples']}", font=lab, fill=(0, 110, 200))
            d.text((x + 6, y + 186), r["reason"][:18], font=lab, fill=(120, 120, 120))
        p = out / f"sheet-{pi + 1}.png"; S.save(p); print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
