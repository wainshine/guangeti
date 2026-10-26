#!/usr/bin/env python3
"""Counters (孔洞) audit — generic for both lines (A and B).

For every glyph we render at 256px and count holes with RETR_CCOMP, then compare
with the same character in WenKai (the content font we learn from).  A hole that
exists in WenKai but not in our font is a defect the five shape metrics cannot
see: Dice / ink / cap / chamfer are all blind to a filled counter.

Two failure modes are reported separately:
  * `lost`   — WenKai has N>0 holes, we have 0            (fully fused)
  * `fewer`  — we have 0 < holes < WenKai's N            (partly fused)

Usage:
  python3 scripts/71_holes.py --font build/GuanGeKai-B-Regular.ttf --n 300
  python3 scripts/71_holes.py --font build/GuanGeKai-B-Real.ttf --n 0      # every glyph
  python3 scripts/71_holes.py --font build/GuanGeKai-Regular.ttf --n 300 --json work/holes_a.json
  python3 scripts/71_holes.py --font build/GuanGeKai-B-Regular.ttf --n 0 --json work-b/holes.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/base/LXGWWenKai-Regular.ttf"
S = 256
TOP = 880.0
BLOCK = (0x4E00, 0x9FFF)


def holes_of(mask: np.ndarray) -> int:
    out = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    hier = out[-1]                      # OpenCV 4/5 use different arities
    if hier is None:
        return 0
    return int(sum(1 for h in hier[0] if h[3] != -1))


def raster(font: ImageFont.FreeTypeFont, ch: str) -> np.ndarray:
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).text((S // 2, int(TOP * S / 1000.0)), ch, fill=255, font=font,
                            anchor="ms")
    return np.array(im) > 127


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=str(ROOT / "build/GuanGeKai-B-Regular.ttf"))
    ap.add_argument("--n", type=int, default=300,
                    help="sample size; 0 = every glyph in the font's cmap")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", default="")
    ap.add_argument("--list", type=int, default=15, help="how many offenders to print")
    args = ap.parse_args()

    f = ImageFont.truetype(args.font, S)
    b = ImageFont.truetype(str(BASE), S)
    from fontTools.ttLib import TTFont
    cps = sorted(TTFont(args.font).getBestCmap())
    cps = [c for c in cps if BLOCK[0] <= c <= BLOCK[1]]

    if args.n and args.n < len(cps):
        rng = np.random.RandomState(args.seed)
        cps = sorted(rng.choice(cps, args.n, replace=False).tolist())

    rows = []
    for cp in cps:
        ch = chr(cp)
        hb = holes_of(raster(b, ch))
        if hb == 0:
            continue  # WenKai has no counter here either; nothing to lose
        ho = holes_of(raster(f, ch))
        rows.append((ch, ho, hb))

    lost = [r for r in rows if r[1] == 0]
    fewer = [r for r in rows if 0 < r[1] < r[2]]
    same = [r for r in rows if r[1] == r[2]]
    n_tested = len(cps)
    print(f"font {args.font.split('/')[-1]}  tested {n_tested} glyphs  "
          f"(WenKai has a counter in {len(rows)})")
    if not rows:
        print("no comparable glyphs")
        return 0
    print(f"  holes equal   {len(same):4d} / {len(rows)}  ({100*len(same)/len(rows):.1f}%)")
    print(f"  holes fewer   {len(fewer):4d} / {len(rows)}  ({100*len(fewer)/len(rows):.1f}%)")
    print(f"  holes lost    {len(lost):4d} / {len(rows)}  ({100*len(lost)/len(rows):.1f}%)")
    bad = sorted(lost + fewer)[: args.list]
    if bad:
        print("  worst:", " ".join(f"{c}({a}/{b_})" for c, a, b_ in bad))
    if args.json:
        Path(args.json).write_text(json.dumps({
            "font": args.font, "tested": n_tested, "comparable": len(rows),
            "same": len(same), "fewer": len(fewer), "lost": len(lost),
            "lost_chars": "".join(r[0] for r in lost),
            "worse_chars": "".join(r[0] for r in sorted(lost + fewer)),
        }, ensure_ascii=False, indent=1))
        print(f"-> {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
