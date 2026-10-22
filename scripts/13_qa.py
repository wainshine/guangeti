"""Quality checks + contact sheets for a built font."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BLOCK = (0x4E00, 0x9FFF)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=str(ROOT / "build" / "GuangeKai-Regular.ttf"))
    ap.add_argument("--outdir", default=str(ROOT / "work" / "qa"))
    args = ap.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    f = TTFont(args.font)
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    have = [c for c in range(BLOCK[0], BLOCK[1] + 1) if c in cmap]
    print(f"coverage {len(have)}/{BLOCK[1]-BLOCK[0]+1} = {len(have)/(BLOCK[1]-BLOCK[0]+1):.4%}")
    empty, tiny, huge = [], [], []
    for cp in have:
        bp = BoundsPen(gs)
        gs[cmap[cp]].draw(bp)
        if not bp.bounds:
            empty.append(cp)
            continue
        x0, y0, x1, y1 = bp.bounds
        w, h = x1 - x0, y1 - y0
        if w < 60 or h < 60:
            tiny.append((chr(cp), round(w), round(h)))
        if w > 1000 or h > 1000:
            huge.append((chr(cp), round(w), round(h)))
    print("empty", len(empty), "tiny", len(tiny), "huge", len(huge))
    print("tiny sample", tiny[:20])
    print("huge sample", huge[:20])

    # contact sheets: 40x25 chars per sheet
    cols, rows = 40, 25
    per = cols * rows
    chars = [chr(c) for c in have]
    fnt = ImageFont.truetype(args.font, 55)
    for s in range(0, len(chars), per):
        chunk = chars[s:s + per]
        sheet = Image.new("RGB", (cols * 60, rows * 66), "white")
        d = ImageDraw.Draw(sheet)
        for i, ch in enumerate(chunk):
            x, y = (i % cols) * 60, (i // cols) * 66
            d.text((x + 2, y), ch, font=fnt, fill="black")
        sheet.save(out / f"sheet_{s//per:03d}.png")
    print("sheets:", (len(chars) + per - 1) // per, "->", out)
    stats = dict(coverage=len(have), empty=len(empty), tiny=tiny[:50], huge=huge[:50])
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
