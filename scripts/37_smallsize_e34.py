"""E34: settle what the small-size weight difference actually is.

Three ways of measuring, all on the shipped font:
  A  same-char self ratio   ink(size)/ink(96) -- how much ink each group *loses* as size shrinks
  B  cross-group ratio      median ink of gen chars / median ink of real chars, per size
  C  group vs content font  ink(ours)/ink(WenKai) per group, per size
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OURS = ROOT / "build" / "GuanGeKai-Regular.ttf"
WK = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"
SIZES = (12, 14, 16, 20, 32, 96)


def ink(path, ch, S):
    f = ImageFont.truetype(str(path), S)
    im = Image.new("L", (S * 3, S * 3), 0)
    ImageDraw.Draw(im).text((S * 0.5, S * 2.4), ch, fill=255, font=f, anchor="ls")
    a = np.array(im) > 127
    return int(a.sum())


def main():
    prov = json.load(open(ROOT / "release" / "provenance.json"))
    real = [c for c, v in prov.items() if v == "real"]
    gen = [c for c, v in prov.items() if v in ("gan", "ribbon_fb")]
    rng = np.random.RandomState(0)
    real_s = rng.choice(real, 120, replace=False)
    gen_s = rng.choice(gen, 120, replace=False)

    # A: self ratio at 96px
    base = {("real", c): ink(OURS, c, 96) for c in real_s}
    base.update({("gen", c): ink(OURS, c, 96) for c in gen_s})

    rows = {}
    for S in SIZES:
        A_real = [ink(OURS, c, S) / max(1, base[("real", c)]) for c in real_s]
        A_gen = [ink(OURS, c, S) / max(1, base[("gen", c)]) for c in gen_s]
        B_real = [ink(OURS, c, S) for c in real_s]
        B_gen = [ink(OURS, c, S) for c in gen_s]
        C_real = [ink(OURS, c, S) / max(1, ink(WK, c, S)) for c in real_s]
        C_gen = [ink(OURS, c, S) / max(1, ink(WK, c, S)) for c in gen_s]
        rows[str(S)] = {
            "A_selfratio_real": round(float(np.median(A_real)), 3),
            "A_selfratio_gen": round(float(np.median(A_gen)), 3),
            "A_diff": round(float(np.median(A_gen) - np.median(A_real)), 3),
            "B_ratio_of_medians": round(float(np.median(B_gen) / max(1.0, np.median(B_real))), 3),
            "C_vs_wenkai_real": round(float(np.median(C_real)), 3),
            "C_vs_wenkai_gen": round(float(np.median(C_gen)), 3),
            "C_ratio_of_medians": round(float(np.median(C_gen) / max(1e-6, np.median(C_real))), 3),
        }
        print(S, json.dumps(rows[str(S)], ensure_ascii=False), flush=True)
    (ROOT / "work" / "e34_smallsize.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("-> work/e34_smallsize.json")


if __name__ == "__main__":
    main()
