"""Evaluate on the 617 single-occurrence characters -- the only clean generalisation set.

Every learned model in this repo was trained on characters from chosen.jsonl; the 617
chars that occur exactly once in the book were never used for training, so this set
cannot be contaminated by a train/val split mistake. Use it for any "does it generalise"
claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

import numpy as np
import torch
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402
from generate_lib import render_base, ribbon_scale  # noqa: E402
from importlib import import_module  # noqa: E402
ev = import_module("18_eval")

S = 256


def load_gan(path):
    spec = spec_from_file_location("gan", ROOT / "scripts" / "21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    g = gan.Generator()
    g.load_state_dict(torch.load(path, map_location="cpu")["G"]); g.eval()
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gan", action="append", default=[],
                    help="checkpoint to score; may be repeated")
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--out", default=str(ROOT / "work" / "eval_single.json"))
    ap.add_argument("--eval-data", default=str(ROOT / "work" / "pairs_single.npz"))
    args = ap.parse_args()

    d = np.load(args.eval_data, allow_pickle=True)
    X, Y = d["X"], d["Y"]
    rng = np.random.RandomState(0)
    sel = rng.choice(len(X), min(args.n, len(X)), replace=False)

    font = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S)
    rel = np.load(ROOT / "work" / "stroke_rel_width.npy")

    def wk(i):
        return X[i] > 127

    def ribbon(i):
        wm = wk(i)
        fr = B.glyph_frames(wm, S)
        r = np.random.RandomState(int(i))
        raw = r.choice(rel, size=len(fr), replace=True); raw /= max(1e-6, raw.mean())
        w = np.power(raw, 1.4); w /= max(1e-6, w.mean())
        return B.render_ribbon(fr, scale=ribbon_scale(float(wm.sum())), dips=w,
                               end_skew=0.9, taper=0.2, size=S, ss=2)

    rows = {}

    def score(name, fn):
        D, ink = [], []
        for i in sel:
            m = fn(i)
            t = Y[i] > 127
            D.append(2 * float((m & t).sum()) / max(1.0, float(m.sum() + t.sum())))
            ink.append(float(m.sum()) / max(1.0, float(t.sum())))
        rows[name] = {"n": len(sel), "dice": round(float(np.mean(D)), 3),
                      "ink": round(float(np.mean(ink)), 3)}
        print(f"{name:24s} Dice {rows[name]['dice']:.3f}  ink {rows[name]['ink']:.3f}")

    score("霞鹜文楷原样", wk)
    score("ribbon (v1.3.5 params)", ribbon)
    for path in args.gan:
        G = load_gan(path)

        def gan_fn(i, G=G):
            a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
            with torch.no_grad():
                return G(torch.from_numpy(a).float()).numpy()[0, 0] > 0

        score(Path(path).stem, gan_fn)
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("->", args.out)


if __name__ == "__main__":
    main()
