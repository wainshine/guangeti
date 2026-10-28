"""Validate the C-line clean-set targets (`pairs_clean.npz`) against their labels.

The clean set was built from held-out pages, but the cells were labelled by the OCR
line sequence — an occasional cell holds a different character (e.g. the target for
`表` is actually `之`).  Every Dice/chamfer/broken number computed against such a
target is meaningless, so this script audits the targets before they are used as
ground truth.

Outputs:
  work-c/eval_target_audit.json   per-character scores + flags
  work-c/eval_target_sheet.png    contact sheet (X = WenKai label, Y = book target,
                                  F = shipped font) for the flagged characters

  python3 scripts/99_validate_targets_c.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BLOCK = (0x4E00, 0x9FFF)


def dice(a: np.ndarray, b: np.ndarray) -> float:
    return float(2.0 * (a & b).sum() / max(1, a.sum() + b.sum()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "work-c" / "pairs_clean.npz"))
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-C-Regular.ttf"))
    ap.add_argument("--out", default=str(ROOT / "work-c" / "eval_target_audit.json"))
    ap.add_argument("--sheet", default=str(ROOT / "work-c" / "eval_target_sheet.png"))
    ap.add_argument("--thr", type=float, default=0.15,
                    help="X-Y Dice below this is flagged for review")
    args = ap.parse_args()

    d = np.load(args.data, allow_pickle=True)
    chars = [str(c) for c in d["chars"]]
    X, Y = d["X"], d["Y"]
    font = ImageFont.truetype(args.font, 256)

    def render(ch: str) -> np.ndarray:
        im = Image.new("L", (256, 256), 0)
        ImageDraw.Draw(im).text((0, 225), ch, fill=255, font=font, anchor="ls")
        return np.array(im) > 127

    rows = []
    for i, ch in enumerate(chars):
        x = X[i] > 127
        y = Y[i] > 127
        f = render(ch)
        rows.append(dict(char=ch, x_y=round(dice(x, y), 3),
                         font_y=round(dice(f, y), 3),
                         x_ink=int(x.sum()), y_ink=int(y.sum()),
                         flag=bool(dice(x, y) < args.thr or y.sum() < 500)))
    flagged = [r for r in rows if r["flag"]]
    n = len(rows)
    print(f"targets {n}; flagged {len(flagged)} "
          f"(X-Y < {args.thr} or Y ink < 500)")
    for t in (0.05, 0.10, 0.15, 0.20):
        print(f"  X-Y < {t:.2f}: {sum(1 for r in rows if r['x_y'] < t)}")
    Path(args.out).write_text(json.dumps(
        dict(n=n, thr=args.thr, flagged=flagged, all=rows), ensure_ascii=False, indent=1))
    print(f"-> {args.out}")

    # contact sheet: X | Y | font, 8 columns
    cols = 8
    cell = 128
    items = flagged[:96]
    rows_n = max(1, (len(items) + cols - 1) // cols)
    sheet = Image.new("L", (cols * cell * 3, rows_n * cell), 255)
    draw = ImageDraw.Draw(sheet)
    for k, r in enumerate(items):
        i = chars.index(r["char"])
        row, col = divmod(k, cols)
        for j, img in enumerate((X[i] > 127, Y[i] > 127, render(r["char"]))):
            im = Image.fromarray((img * 255).astype(np.uint8)).resize((cell - 4, cell - 4))
            sheet.paste(im, ((col * 3 + j) * cell + 2, row * cell + 2))
        draw.text((col * 3 * cell + 4, row * cell + cell - 14), r["char"], fill=128)
    sheet.save(args.sheet)
    print(f"-> {args.sheet}  ({len(items)} flagged shown)")


if __name__ == "__main__":
    main()
