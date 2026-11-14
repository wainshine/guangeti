#!/usr/bin/env python3
"""B-Q8: counter (hole) audit against the **source mask** instead of WenKai.

`63_qa_b` delegates counters to `71_holes.py`, which counts holes in WenKai and treats any
difference as a defect.  That is the "reference font topology" ruler the project decided to
drop (D21's principle), and for a manuscript it is wrong on both sides: the book's own
open/crossed strokes are style, and a real loss is only visible against the source ink.

This script counts, for every real glyph (chosen.jsonl):
    counters(source mask)   the cell the glyph was traced from
    counters(rendered glyph) the shipped font at 256 px
and reports lost / fewer / equal / more, plus the same comparison against WenKai so the two
rulers can be compared side by side.

  python3 scripts/81_holes_source_b.py --n 0 --out work-b/holes_source_b.json
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
sys.path.insert(0, str(ROOT / "scripts"))
from shiji_page import wk_holes  # noqa: E402

S = 256


def counters(mask: np.ndarray) -> int:
    """Enclosed background regions (a counter is a background component not touching the border)."""
    m = np.pad(mask.astype(np.uint8), 1, constant_values=0)
    n, lab = cv2.connectedComponents(1 - m, connectivity=4)
    border = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    return sum(1 for i in range(1, n) if i not in border)


def glyph_mask(font_path: str, ch: str) -> np.ndarray:
    f = ImageFont.truetype(font_path, S // 1)
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).text((S // 2, int(0.88 * S)), ch, font=f, fill=255, anchor="ms")
    return np.array(im) > 127


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-B-Real.ttf"))
    ap.add_argument("--n", type=int, default=0, help="0 = every real glyph")
    ap.add_argument("--out", default=str(ROOT / "work-b" / "holes_source_b.json"))
    args = ap.parse_args()

    wd = Path(args.work)
    rows = [json.loads(l) for l in open(wd / "chosen.jsonl")]
    rows.sort(key=lambda r: r["label"])
    if args.n:
        rows = rows[: args.n]

    out, miss = [], 0
    for r in rows:
        mp = wd / "masks" / r["file"]
        if not mp.exists():
            miss += 1
            continue
        src = counters(np.array(Image.open(mp).convert("L")) > 127)
        gl = counters(glyph_mask(args.font, r["label"]))
        wk = int(wk_holes(r["label"], S))
        out.append({"char": r["label"], "src": src, "glyph": gl, "wenkai": wk, "file": r["file"]})

    def summarise(key: str) -> dict:
        lost = sum(1 for o in out if o[key] >= 1 and o["glyph"] == 0)
        fewer = sum(1 for o in out if o["glyph"] < o[key])
        equal = sum(1 for o in out if o["glyph"] == o[key])
        more = sum(1 for o in out if o["glyph"] > o[key])
        comparable = sum(1 for o in out if o[key] >= 1)
        return {"comparable": comparable, "lost": lost, "fewer": fewer, "equal": equal,
                "more": more,
                "lost_frac": round(lost / comparable, 4) if comparable else None,
                "fewer_frac": round(fewer / comparable, 4) if comparable else None}

    res = {"n": len(out), "missing_masks": miss, "vs_source": summarise("src"),
           "vs_wenkai": summarise("wenkai"), "chars": out}
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))

    print(f"compared {len(out)} real glyphs (missing masks {miss}), counters from source mask")
    for name, s in (("vs source mask", res["vs_source"]), ("vs WenKai", res["vs_wenkai"])):
        print(f"  {name:14s} comparable {s['comparable']:4d}  lost {s['lost']:3d} ({s['lost_frac']:.1%})"
              f"  fewer {s['fewer']:4d} ({s['fewer_frac']:.1%})  equal {s['equal']:4d}  more {s['more']:3d}")
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
