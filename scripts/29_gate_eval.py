"""Evaluate the topology gate for the GAN: raw vs gated, plus the cost of the anchor.

The gate uses the content font (WenKai) as its structural anchor: if the GAN's
counter count differs from WenKai's, the whole glyph falls back to ribbon.
This script reports what that costs -- for every reverted character that has a
real print sample, it says whether GAN or ribbon was actually closer to the print.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402
from generate_lib import render_base, ribbon_scale  # noqa: E402
from importlib.util import module_from_spec, spec_from_file_location  # noqa: E402

S = 256


def load_gan(path):
    spec = spec_from_file_location("gan", ROOT / "scripts" / "21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    g = gan.Generator()
    g.load_state_dict(torch.load(path, map_location="cpu")["G"]); g.eval()
    return g


def counters(mask, minarea=20):
    """(connected components, enclosed counters) -- the same pair the gate uses."""
    mb = mask.astype(bool)
    n, _lab, st, _ = cv2.connectedComponentsWithStats(mb.astype(np.uint8), 8)
    comps = sum(1 for i in range(1, n) if st[i, 4] >= minarea)
    nh, _l2, hs, _ = cv2.connectedComponentsWithStats((~mb).astype(np.uint8), 8)
    holes = sum(1 for i in range(1, nh) if hs[i, 4] >= minarea
                and hs[i, 0] > 1 and hs[i, 1] > 1
                and hs[i, 0] + hs[i, 2] < mb.shape[1] - 1
                and hs[i, 1] + hs[i, 3] < mb.shape[0] - 1)
    return comps, holes


def dice(a, b):
    return 2 * float((a & b).sum()) / max(1, float(a.sum() + b.sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gan", default=str(ROOT / "work" / "ckpt" / "zi2zi_gan_multi_ep040.pt"))
    ap.add_argument("--out", default=str(ROOT / "work" / "gate_eval.json"))
    args = ap.parse_args()

    G = load_gan(args.gan)
    font = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S)
    rel = np.load(ROOT / "work" / "stroke_rel_width.npy")
    pairs = np.load(ROOT / "work" / "pairs" / "pairs.npz", allow_pickle=True)
    chars = [str(c) for c in pairs["chars"]]
    Y = pairs["Y"]; pos = {c: i for i, c in enumerate(chars)}

    def wk(ch):
        return render_base(font, ch, S) > 127

    def gan_fn(ch):
        x = render_base(font, ch, S)
        a = (x.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            return G(torch.from_numpy(a).float()).numpy()[0, 0] > 0

    def rib(ch):
        bm = wk(ch); fr = B.glyph_frames(bm, S)
        rng = np.random.RandomState(ord(ch) % (2 ** 31))
        ds = rng.choice(rel, size=len(fr), replace=True); ds /= max(1e-6, ds.mean())
        w = np.power(ds, 1.4); w /= max(1e-6, w.mean())
        return B.render_ribbon(fr, scale=ribbon_scale(float(bm.sum())), dips=w,
                               end_skew=0.9, taper=0.2, size=S, ss=2)

    out = {"gan": Path(args.gan).name, "classes": {}}
    for cls, path in (("B", ROOT / "work" / "bench_unseen.json"),
                      ("C", ROOT / "work" / "bench_noreal.json")):
        sel = json.load(open(path))
        rows = {"n": len(sel)}
        raw_ok = gated_ok = reverted = 0
        d_raw, d_gate, d_rib = [], [], []
        wrong = worse = 0
        for ch in sel:
            g = gan_fn(ch); r = rib(ch); ref = wk(ch)
            same = counters(g) == counters(ref)
            raw_ok += same
            if same:
                m = g
            else:
                m = r; reverted += 1
                if ch in pos:                      # has a real print sample
                    t = Y[pos[ch]] > 127
                    if dice(g, t) < dice(r, t):
                        wrong += 1                 # gate replaced the better glyph
                    else:
                        worse += 1
            gated_ok += (counters(m) == counters(ref))
            if ch in pos:
                t = Y[pos[ch]] > 127
                d_raw.append(dice(g, t)); d_gate.append(dice(m, t)); d_rib.append(dice(r, t))
        rows.update({
            "raw_topology_agree": f"{raw_ok}/{len(sel)}",
            "gated_topology_agree": f"{gated_ok}/{len(sel)}",
            "reverted": reverted,
            "gate_replaced_better_glyph": wrong,
            "gate_picked_better_glyph": worse,
        })
        if d_raw:
            rows.update({"dice_gan": round(float(np.mean(d_raw)), 3),
                         "dice_gated": round(float(np.mean(d_gate)), 3),
                         "dice_ribbon": round(float(np.mean(d_rib)), 3)})
        out["classes"][cls] = rows
        print(cls, json.dumps(rows, ensure_ascii=False))
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("->", args.out)


if __name__ == "__main__":
    main()
