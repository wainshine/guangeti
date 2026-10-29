"""Absolute label check: Dice(cell mask, WenKai render of its own label).

Independent of OCR.  On the 400 blind audit: AUC 0.874 (marked<unmarked),
threshold 0.25 = recall 84.3%, FP 23.3%.
"""
from __future__ import annotations
import json, sys, argparse
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
S = 128
FONT = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S)
_CACHE = {}


def wk(ch):
    if ch not in _CACHE:
        im = Image.new("L", (S, S), 0)
        ImageDraw.Draw(im).text((0, 112), ch, fill=255, font=FONT, anchor="ls")
        _CACHE[ch] = np.array(im) > 127
    return _CACHE[ch]


def cellmask(path):
    m = np.array(Image.open(path).convert("L")) > 127
    ys, xs = np.nonzero(m)
    if not len(ys):
        return None
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return cv2.resize(m.astype(np.uint8), (S, S), interpolation=cv2.INTER_NEAREST) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-c"))
    ap.add_argument("--out", default=str(ROOT / "work-c" / "wenkai_dice_chosen.json"))
    ap.add_argument("--sheet", default=str(ROOT / "docs/images/c-wenkai-low.png"))
    args = ap.parse_args()
    wd = Path(args.work)
    chosen = [json.loads(l) for l in open(wd / "chosen.jsonl")]
    rows = []
    for i, r in enumerate(chosen):
        a = cellmask(wd / "masks" / r["file"])
        if a is None: continue
        b = wk(r["label"])
        d = 2 * (a & b).sum() / max(1, a.sum() + b.sum())
        rows.append({"label": r["label"], "file": r["file"], "dice": round(float(d), 3),
                     "w": r["w"], "h": r["h"], "n_samples": r.get("n_samples")})
        if i % 1000 == 0: print(i, len(chosen), flush=True)
    rows.sort(key=lambda r: r["dice"])
    json.dump(rows, open(args.out, "w"), ensure_ascii=False, indent=1)
    vals = np.array([r["dice"] for r in rows])
    print("n", len(rows), "median", round(float(np.median(vals)), 3),
          "p10", round(float(np.percentile(vals, 10)), 3),
          "lt0.25", int((vals < 0.25).sum()), "lt0.20", int((vals < 0.20).sum()))
    low = rows[:120]
    S2 = 140; cols = 10; rr = (len(low) + cols - 1) // cols
    im = Image.new("RGB", (cols * (S2 + 6), rr * (S2 + 24)), "white"); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 12)
    for j, r in enumerate(low):
        x = (j % cols) * (S2 + 6); y = (j // cols) * (S2 + 24)
        ci = Image.open(wd / "cells" / r["file"]).convert("L"); ci.thumbnail((S2, S2)); im.paste(ci, (x, y))
        d.text((x, y + S2), f"{r['label']} {r['dice']}", font=f, fill="red")
    im.save(args.sheet); print("sheet", args.sheet)


if __name__ == "__main__":
    main()
