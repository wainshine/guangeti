"""C-line: resolve simplified/variant codepoints against the glyph that was chosen.

OCR sometimes returns the simplified codepoint for a traditional glyph (飞 for 飛,
书 for 書, 岗 for 崗).  Blind OpenCC s2t would be wrong in the other direction —
云, 后, 里, 干, 余, 台 are legitimate traditional characters and would be converted
to 雲/後/裡/乾/餘/臺.  The glyph itself settles it: render the chosen glyph and both
candidate codepoints with WenKai, and keep the candidate the glyph resembles.

Only relabels when the traditional candidate is clearly closer (Dice margin 0.08 and
a lower skeleton distance).  Writes `work-c/variant_map.json`; the caller then
re-runs `06_norm.py`, `76_build_real_c.py` and `08_make_pairs.py`.

  python3 scripts/88_variants_c.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402

S = 256
BOS = 880.0
BASE = ROOT / "data/base/LXGWWenKai-Regular.ttf"
BLOCK = (0x4E00, 0x9FFF)


def render(font_path, ch):
    f = ImageFont.truetype(str(font_path), S)
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).text((0, BOS * S / 1000.0), ch, fill=255, font=f, anchor="ls")
    return np.array(im) > 127


def chamfer(a, b):
    from scipy.ndimage import distance_transform_edt
    sa, sb = B.skeleton_of(a), B.skeleton_of(b)
    if sa.sum() < 10 or sb.sum() < 10:
        return 99.0
    return 0.5 * (float(distance_transform_edt(~sb)[sa].mean())
                  + float(distance_transform_edt(~sa)[sb].mean()))


def dice(a, b):
    return 2 * float((a & b).sum()) / max(1.0, float(a.sum() + b.sum()))


def load_candidates():
    from opencc import OpenCC
    cc = OpenCC("s2t")
    trad = defaultdict(list)
    for line in open(ROOT / "data/ids/Unihan_Variants.txt"):
        if "kTraditionalVariant" not in line:
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        cp = int(parts[0][2:], 16)
        for v in parts[2].split():
            if v.startswith("U+"):
                trad[cp].append(int(v[2:], 16))
    return cc, trad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-C-Real.ttf"))
    ap.add_argument("--chosen", default=str(ROOT / "work-c" / "chosen.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "work-c" / "variant_map.json"))
    args = ap.parse_args()
    cc, trad = load_candidates()
    rows = [json.loads(l) for l in open(args.chosen)]
    labels = {r["label"] for r in rows}
    mapping, report = {}, []
    for r in rows:
        ch = r["label"]
        cands = set()
        s2 = cc.convert(ch)
        if s2 and s2 != ch and len(s2) == 1:
            cands.add(s2)
        for cp in trad.get(ord(ch), []):
            if BLOCK[0] <= cp <= BLOCK[1]:
                cands.add(chr(cp))
        cands = [c for c in cands if c != ch and c not in labels]
        if not cands:
            continue
        book = render(args.font, ch)
        if book.sum() < 50:
            continue
        ref = render(BASE, ch)
        d0, c0 = dice(book, ref), chamfer(book, ref)
        best = None
        for c in cands:
            rc = render(BASE, c)
            if rc.sum() < 50:
                continue
            d1, c1 = dice(book, rc), chamfer(book, rc)
            if best is None or d1 > best[1]:
                best = (c, d1, c1)
        if best and best[1] >= d0 + 0.08 and best[2] < c0 - 0.5:
            mapping[ch] = best[0]
            report.append(dict(old=ch, new=best[0], dice_old=round(d0, 3),
                               dice_new=round(best[1], 3),
                               chamfer_old=round(c0, 2), chamfer_new=round(best[2], 2)))
    Path(args.out).write_text(json.dumps(mapping, ensure_ascii=False, indent=1))
    print(f"variant relabels: {len(mapping)}")
    for x in sorted(report, key=lambda z: -z["dice_new"])[:60]:
        print(f"  {x['old']} -> {x['new']}  dice {x['dice_old']:.2f}->{x['dice_new']:.2f}  "
              f"ch {x['chamfer_old']:.1f}->{x['chamfer_new']:.1f}")
    (ROOT / "work-c" / "variant_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
