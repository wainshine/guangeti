"""C-line: flag chosen glyphs whose *structure* disagrees with their label.

There is no ground truth for the labels, but there is an independent structural
prior: the same character drawn by LXGW WenKai.  A correct label usually lands within
a modest skeleton distance (hand vs modern type differ, but not wildly); a wrong or
fragmentary label is an outlier.  This does not prove a label right — it only ranks
the ~6,000 shipped real glyphs so a human reviews dozens instead of all.

The comparison uses the built `GuanGeKai-C-Real.ttf`, i.e. exactly the outlines that
ship, not an intermediate raster.

  python3 scripts/87_check_choices_c.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402

S = 256
BOS = 880.0
BASE = ROOT / "data/base/LXGWWenKai-Regular.ttf"


def render(font_path, ch, size=S):
    f = ImageFont.truetype(str(font_path), size)
    im = Image.new("L", (size, size), 0)
    ImageDraw.Draw(im).text((0, BOS * size / 1000.0), ch, fill=255, font=f, anchor="ls")
    return np.array(im) > 127


def skel_chamfer(a, b):
    from scipy.ndimage import distance_transform_edt
    sa, sb = B.skeleton_of(a), B.skeleton_of(b)
    if sa.sum() < 10 or sb.sum() < 10:
        return 99.0
    d_b = distance_transform_edt(~sb)
    d_a = distance_transform_edt(~sa)
    return 0.5 * (float(d_b[sa].mean()) + float(d_a[sb].mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-C-Real.ttf"))
    ap.add_argument("--work", default=str(ROOT / "work-c"))
    ap.add_argument("--chosen", default=str(ROOT / "work-c" / "chosen.jsonl"))
    ap.add_argument("--n", type=int, default=72)
    args = ap.parse_args()
    wd = Path(args.work)
    chosen = [json.loads(l) for l in open(args.chosen)]
    rows = []
    for i, r in enumerate(chosen):
        ch = r["label"]
        book = render(args.font, ch)
        ref = render(BASE, ch)
        if book.sum() < 50 or ref.sum() < 50:
            continue
        dice = 2 * float((book & ref).sum()) / max(1.0, float(book.sum() + ref.sum()))
        rows.append(dict(char=ch, file=r["file"], dice=round(dice, 3),
                         chamfer=round(skel_chamfer(book, ref), 2),
                         ink=round(float(book.sum()) / max(1.0, float(ref.sum())), 3),
                         n_samples=r.get("n_samples"), edge=r.get("edge")))
        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/{len(chosen)}", flush=True)
    rows.sort(key=lambda r: (r["dice"], -r["chamfer"]))
    (wd / "choice_check.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    arr = np.array([r["dice"] for r in rows])
    print(f"checked {len(rows)}  dice p5 {np.percentile(arr,5):.3f} "
          f"median {np.median(arr):.3f}  dice<0.25: {(arr<0.25).sum()}")
    n = min(args.n, len(rows))
    cols = 12
    cell = 110
    im = Image.new("RGB", (cols * cell * 3, ((n + cols - 1) // cols) * (cell + 16)), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(BASE), 13)
    fb = ImageFont.truetype(args.font, int(cell * 0.8))
    for k in range(n):
        r = rows[k]
        c, rr = divmod(k, cols)
        d.text((c * cell * 3 + 10, rr * (cell + 16) + 10), r["char"], font=fb, fill="black")
        d.text((c * cell * 3 + cell + 4, rr * (cell + 16) + 12), r["char"], font=f, fill="#333")
        d.text((c * cell * 3 + cell + 4, rr * (cell + 16) + 44),
               f"dice {r['dice']:.2f}\nch {r['chamfer']:.1f}", font=f, fill="#a00")
        ref = render(BASE, r["char"], size=cell)
        im.paste(Image.fromarray((ref * 255).astype(np.uint8)).convert("RGB"),
                 (c * cell * 3 + cell * 2, rr * (cell + 16)))
    im.save(wd / "choice_flagged.png")
    print("sheet ->", wd / "choice_flagged.png")


if __name__ == "__main__":
    main()
