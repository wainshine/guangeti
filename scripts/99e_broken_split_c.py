"""Decompose the clean-set "broken" rate with max-over-K targets (C/E22).

For every character that has two genuine samples (`pairs_clean.npz` and
`pairs_clean_second.npz`), score the shipped glyph against *both* targets:

  one-broken   Dice < 0.30 against one target, >= 0.30 against the other
               -> target variance / one bad sample, not a font defect
  both-broken  Dice < 0.30 against both
               -> the glyph does not look like either genuine sample

Also reports the same-character floor (Dice between the two targets).  The output
is the evidence for the Q4 retrain decision; it is *not* a release gate until the
targets pass `99_validate_targets_c.py`.

  python3 scripts/99e_broken_split_c.py --clean work-c/pairs_clean.npz \
      --second work-c/pairs_clean_second.npz --font build/GuanGeKai-C-Regular.ttf
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
S = 256


def render(font: ImageFont.FreeTypeFont, ch: str) -> np.ndarray:
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).text((0, 225), ch, fill=255, font=font, anchor="ls")
    return np.array(im) > 127


def dice(a: np.ndarray, b: np.ndarray) -> float:
    return float(2.0 * (a & b).sum() / max(1, a.sum() + b.sum()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", default=str(ROOT / "work-c" / "pairs_clean.npz"))
    ap.add_argument("--second", default=str(ROOT / "work-c" / "pairs_clean_second.npz"))
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-C-Regular.ttf"))
    ap.add_argument("--out", default=str(ROOT / "work-c" / "eval_broken_split.json"))
    ap.add_argument("--sheet", default=str(ROOT / "work-c" / "eval_broken_split.png"))
    ap.add_argument("--thr", type=float, default=0.30)
    args = ap.parse_args()
    d1 = np.load(args.clean, allow_pickle=True)
    d2 = np.load(args.second, allow_pickle=True)
    c1 = [str(c) for c in d1["chars"]]
    c2 = [str(c) for c in d2["chars"]]
    pos = {c: i for i, c in enumerate(c2)}
    font = ImageFont.truetype(args.font, S)
    rows = []
    for i, ch in enumerate(c1):
        if ch not in pos:
            continue
        g = render(font, ch)
        y1 = d1["Y"][i] > 127
        y2 = d2["Y"][pos[ch]] > 127
        d1v, d2v, floor = dice(g, y1), dice(g, y2), dice(y1, y2)
        if d1v < args.thr and d2v < args.thr:
            cls = "both"
        elif d1v < args.thr or d2v < args.thr:
            cls = "one"
        else:
            cls = "ok"
        rows.append(dict(char=ch, font_y1=round(d1v, 3), font_y2=round(d2v, 3),
                         floor=round(floor, 3), cls=cls))
    n = len(rows)
    cnt = {k: sum(1 for r in rows if r["cls"] == k) for k in ("ok", "one", "both")}
    print(f"n={n}  ok={cnt['ok']} ({cnt['ok']/n:.1%})  "
          f"one-broken={cnt['one']} ({cnt['one']/n:.1%})  "
          f"both-broken={cnt['both']} ({cnt['both']/n:.1%})")
    print("max-over-K defect rate (both-broken): %.1f%%" % (100.0 * cnt["both"] / n))
    Path(args.out).write_text(json.dumps(dict(n=n, thr=args.thr, counts=cnt, rows=rows),
                                         ensure_ascii=False, indent=1))
    print(f"-> {args.out}")
    both = [r for r in rows if r["cls"] == "both"]
    cols = 8
    cell = 100
    rows_n = max(1, (len(both) + cols - 1) // cols)
    sheet = Image.new("L", (cols * 3 * cell, rows_n * cell), 255)
    dr = ImageDraw.Draw(sheet)
    for k, r in enumerate(both[:64]):
        i = c1.index(r["char"])
        j = pos[r["char"]]
        row, col = divmod(k, cols)
        for q, arr in enumerate((render(font, r["char"]), d1["Y"][i] > 127, d2["Y"][j] > 127)):
            im = Image.fromarray((arr * 255).astype(np.uint8)).resize((cell - 4, cell - 4))
            sheet.paste(im, ((col * 3 + q) * cell + 2, row * cell + 2))
        dr.text((col * 3 * cell + 4, row * cell + cell - 12), r["char"], fill=128)
    sheet.save(args.sheet)
    print(f"-> {args.sheet}")


if __name__ == "__main__":
    main()
