"""Compare candidate gate rules for the GAN.

The current gate falls back to ribbon whenever the GAN's counter count differs
from WenKai's. On class B that rejects 58/91 glyphs, 57 of which were actually
closer to the print than ribbon -- the anchor (WenKai) is the problem, not the
threshold. This script scores alternative rules:

  accept  -> keep the GAN glyph
  reject  -> fall back to ribbon

For class B (has print truth) we report Dice of the gated output and how many
accepted glyphs are actually worse than ribbon (false accepts). For class C (no
truth) we report how often the gated output matches WenKai's topology.
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
from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402
from generate_lib import render_base, ribbon_scale  # noqa: E402

S = 256


def load_gan(path):
    spec = spec_from_file_location("gan", ROOT / "scripts" / "21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    g = gan.Generator()
    g.load_state_dict(torch.load(path, map_location="cpu")["G"]); g.eval()
    return g


def comps_holes(mask, minarea=20):
    mb = mask.astype(bool)
    n, _l, st, _ = cv2.connectedComponentsWithStats(mb.astype(np.uint8), 8)
    comps = sum(1 for i in range(1, n) if st[i, 4] >= minarea)
    nh, _l2, hs, _ = cv2.connectedComponentsWithStats((~mb).astype(np.uint8), 8)
    holes = sum(1 for i in range(1, nh) if hs[i, 4] >= minarea
                and hs[i, 0] > 1 and hs[i, 1] > 1
                and hs[i, 0] + hs[i, 2] < mb.shape[1] - 1
                and hs[i, 1] + hs[i, 3] < mb.shape[0] - 1)
    return comps, holes


def iou(a, b):
    return float((a & b).sum()) / max(1.0, float((a | b).sum()))


def dice(a, b):
    return 2 * float((a & b).sum()) / max(1.0, float(a.sum() + b.sum()))


# each rule: (gan_mask, wenkai_mask, gan_comps_holes, wenkai_comps_holes) -> keep?
RULES = {
    "R0 exact (comps,holes)": lambda g, w, gc, wc: gc == wc,
    "R0b exact holes":       lambda g, w, gc, wc: gc[1] == wc[1],
    "R1 holes +-1":          lambda g, w, gc, wc: abs(gc[1] - wc[1]) <= 1,
    "R2 comps equal":        lambda g, w, gc, wc: gc[0] == wc[0],
    "R3 comps+1hole":        lambda g, w, gc, wc: gc[0] == wc[0] and abs(gc[1] - wc[1]) <= 1,
    "R4 iou>=0.55":          lambda g, w, gc, wc: iou(g, w) >= 0.55,
    "R5 iou>=0.45":          lambda g, w, gc, wc: iou(g, w) >= 0.45,
    "R6 comps+1 & iou>=.45": lambda g, w, gc, wc: gc[0] == wc[0] and abs(gc[1] - wc[1]) <= 1 and iou(g, w) >= 0.45,
    "R7 ink in [.7,1.3]":    lambda g, w, gc, wc: 0.7 <= float(g.sum()) / max(1.0, float(w.sum())) <= 1.3,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gan", default=str(ROOT / "work" / "ckpt" / "zi2zi_gan_multi_ep040.pt"))
    ap.add_argument("--out", default=str(ROOT / "work" / "gate_rules.json"))
    args = ap.parse_args()

    G = load_gan(args.gan)
    font = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S)
    rel = np.load(ROOT / "work" / "stroke_rel_width.npy")
    pairs = np.load(ROOT / "work" / "pairs" / "pairs.npz", allow_pickle=True)
    pchars = [str(c) for c in pairs["chars"]]
    Y = pairs["Y"]; pos = {c: i for i, c in enumerate(pchars)}

    cache = {}

    def get(ch):
        if ch in cache:
            return cache[ch]
        base = render_base(font, ch, S)
        wm = base > 127
        fr = B.glyph_frames(wm, S)
        rng = np.random.RandomState(ord(ch) % (2 ** 31))
        ds = rng.choice(rel, size=len(fr), replace=True); ds /= max(1e-6, ds.mean())
        w = np.power(ds, 1.4); w /= max(1e-6, w.mean())
        rib = B.render_ribbon(fr, scale=ribbon_scale(float(wm.sum())), dips=w,
                              end_skew=0.9, taper=0.2, size=S, ss=2)
        a = (base.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            gan = G(torch.from_numpy(a).float()).numpy()[0, 0] > 0
        cache[ch] = (wm, rib, gan, comps_holes(wm), comps_holes(gan))
        return cache[ch]

    out = {"gan": Path(args.gan).name, "rules": {}}
    B_sel = json.load(open(ROOT / "work" / "bench_unseen.json"))
    C_sel = json.load(open(ROOT / "work" / "bench_noreal.json"))
    for name, rule in RULES.items():
        b_dice, rej, false_acc, false_rej = [], 0, 0, 0
        for ch in B_sel:
            wm, rib, gan, rc, gc = get(ch)
            keep = bool(rule(gan, wm, gc, rc))
            m = gan if keep else rib
            if not keep:
                rej += 1
            t = Y[pos[ch]] > 127
            b_dice.append(dice(m, t))
            if keep and dice(gan, t) < dice(rib, t):
                false_acc += 1
            if (not keep) and dice(gan, t) >= dice(rib, t):
                false_rej += 1
        c_ok = 0
        for ch in C_sel:
            wm, rib, gan, rc, gc = get(ch)
            m = gan if bool(rule(gan, wm, gc, rc)) else rib
            c_ok += (comps_holes(m) == rc)
        out["rules"][name] = {
            "B_dice": round(float(np.mean(b_dice)), 3),
            "B_rejected": rej,
            "B_false_accept": false_acc,
            "B_false_reject": false_rej,
            "C_topology_agree": f"{c_ok}/{len(C_sel)}",
        }
        print(f"{name:24s} B Dice {out['rules'][name]['B_dice']:.3f}  "
              f"回退 {rej:3d}  误放行 {false_acc:2d}  误回退 {false_rej:2d}  "
              f"C 拓扑 {c_ok}/{len(C_sel)}")
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("->", args.out)


if __name__ == "__main__":
    main()
