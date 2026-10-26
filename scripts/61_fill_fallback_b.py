"""B-line: fill characters the GAN pass skipped, using the ribbon renderer.

Forked from `36_fill_fallback.py`; work-b paths only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402
from generate_lib import raster_to_em, render_base, ribbon_scale_b  # noqa: E402
from glyphvec import normalize_to_base, trace  # noqa: E402

WB = ROOT / "work-b"
S = 512


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(WB))
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    wd = Path(args.work)
    fb = json.loads((wd / "gan_fallback.json").read_text())
    out = Path(args.out) if args.out else wd / "generated.jsonl"
    have = set()
    for line in open(out):
        have.add(json.loads(line)["char"])
    todo = [c for c in fb if c not in have]
    print(f"fallback {len(fb)}, still missing {len(todo)}")
    if not todo:
        return
    font = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S)
    rel = np.load(wd / "stroke_rel_width.npy")
    with open(out, "a") as fh:
        for i, ch in enumerate(todo):
            wm = render_base(font, ch, S) > 127
            fr = B.glyph_frames(wm, S)
            rng = np.random.RandomState(ord(ch) % (2 ** 31))
            raw = rng.choice(rel, size=len(fr), replace=True)
            raw /= max(1e-6, raw.mean())
            w = np.power(raw, 1.4)
            w /= max(1e-6, w.mean())
            comp256 = float(wm.sum()) * (256.0 / S) ** 2
            m = B.render_ribbon(fr, scale=ribbon_scale_b(comp256), dips=w,
                                end_skew=0.9, taper=0.2, size=S, ss=2)
            cs = trace(m.astype(bool), turdsize=4, alphamax=0.4, opttol=0.5)
            if not cs:
                continue
            em = raster_to_em(cs, S)
            em = normalize_to_base(em, ch, blend=1.0, min_scale=0.8, max_scale=1.25)
            fh.write(json.dumps({"char": ch, "contours": em, "src": "base"},
                                ensure_ascii=False) + "\n")
            if i % 200 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
    print("done; total lines", sum(1 for _ in open(out)))


if __name__ == "__main__":
    main()
