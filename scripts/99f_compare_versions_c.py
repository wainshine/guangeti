"""Compare two GuanGeKai-C builds on the *same* targets (the only fair version test).

Two fonts (v1.0.1 archived, v1.1.0 canonical) are rendered at 256 px against the
same clean targets, so the target set and renderer are held fixed:

  python3 scripts/99f_compare_versions_c.py \
      --fonts build/archive/GuanGeKai-C-Regular-v1.0.1.ttf build/GuanGeKai-C-Regular.ttf \
      --sets work-c/pairs_clean.npz work-c/archive/v1.0.1/pairs_clean.npz

Outputs medians of Dice, broken rate (Dice<0.30), chamfer and ink/target.
The same-200-character weight comparison is in `--weight-sample`.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
S = 256


def _eval_module():
    spec = importlib.util.spec_from_file_location("e82", ROOT / "scripts" / "82_eval_c.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def eval_set(m, font_path: str, data: str):
    d = np.load(data, allow_pickle=True)
    chars = [str(c) for c in d["chars"]]
    Y = d["Y"]
    font = ImageFont.truetype(font_path, S)
    ds, chs, inkr = [], [], []
    for i, ch in enumerate(chars):
        im = Image.new("L", (S, S), 0)
        ImageDraw.Draw(im).text((0, 225), ch, fill=255, font=font, anchor="ls")
        g = np.array(im) > 127
        y = Y[i] > 127
        if g.sum() < 10:
            continue
        ds.append(2 * (g & y).sum() / max(1, g.sum() + y.sum()))
        inkr.append(g.sum() / max(1, y.sum()))
        v = m.chamfer(g, y)
        if v is not None:
            chs.append(v)
    ds = np.array(ds)
    chs = np.array(chs)
    return dict(n=int(len(ds)), dice=float(np.median(ds)),
                broken=float((ds < 0.30).mean()),
                chamfer=float(np.median(chs)) if len(chs) else None,
                ink_over_target=float(np.median(inkr)))


def weight_ratio(font_path: str, chars, wk_path: str):
    def ink(fp, ch):
        f = ImageFont.truetype(fp, 128)
        im = Image.new("L", (128, 128), 0)
        ImageDraw.Draw(im).text((0, 880 * 128 / 1000), ch, fill=255, font=f, anchor="ls")
        return int((np.array(im) > 127).sum())

    rs = []
    for ch in chars:
        a = ink(wk_path, ch)
        b = ink(font_path, ch)
        if a > 200:
            rs.append(b / a)
    return float(np.median(rs)), len(rs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", nargs="+", required=True)
    ap.add_argument("--sets", nargs="+", default=[])
    ap.add_argument("--weight-sample", default="",
                    help="npz with chars= to compute the 200-char ink/WK ratio")
    ap.add_argument("--out", default=str(ROOT / "work-c" / "version_compare.json"))
    args = ap.parse_args()
    m = _eval_module()
    out = {"sets": {}, "weights": {}}
    for data in args.sets:
        out["sets"][f"{Path(data).parent.name}/{Path(data).name}"] = {
            Path(fp).name: eval_set(m, fp, data) for fp in args.fonts}
    if args.weight_sample:
        chars = [str(c) for c in np.load(args.weight_sample, allow_pickle=True)["chars"]]
        for fp in args.fonts:
            med, n = weight_ratio(fp, chars, str(ROOT / "data/base/LXGWWenKai-Regular.ttf"))
            out["weights"][Path(fp).name] = dict(ink_over_wenkai=med, n=n)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
