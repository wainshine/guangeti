"""M0: pick the binarisation threshold for the GAN and record failure rates.

The GAN's tanh output is thresholded at >0. Because its skeletons come out ~16%
thinner than the print (len_ratio 0.84), we sweep the threshold and look for a
value that restores length without hurting Dice or the cap distribution.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location

import numpy as np
import torch
from PIL import ImageFont
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402
from generate_lib import ribbon_scale  # noqa: E402
ev = import_module("18_eval")
ss = import_module("34_struct_score")

S = 256


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gan", default=str(ROOT / "work" / "ckpt" / "attr_single_patch_ep015.pt"))
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--out", default=str(ROOT / "work" / "threshold_sweep.json"))
    args = ap.parse_args()

    d = np.load(ROOT / "work" / "pairs_single.npz", allow_pickle=True)
    X, Y = d["X"], d["Y"]
    sel = np.random.RandomState(7).choice(len(X), min(args.n, len(X)), replace=False)

    spec = spec_from_file_location("gan", ROOT / "scripts" / "21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    G = gan.Generator(); G.load_state_dict(torch.load(args.gan, map_location="cpu")["G"]); G.eval()
    rel = np.load(ROOT / "work" / "stroke_rel_width.npy")

    # cache the raw tanh outputs and the ribbon draws once
    raw, ribs, refs = {}, {}, {}
    for i in sel:
        a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            raw[i] = G(torch.from_numpy(a).float()).numpy()[0, 0]
        wm = X[i] > 127
        fr = B.glyph_frames(wm, S)
        r = np.random.RandomState(int(i))
        q = r.choice(rel, size=len(fr), replace=True); q /= max(1e-6, q.mean())
        w = np.power(q, 1.4); w /= max(1e-6, w.mean())
        ribs[i] = B.render_ribbon(fr, scale=ribbon_scale(float(wm.sum())), dips=w,
                                  end_skew=0.9, taper=0.2, size=S, ss=2)
        refs[i] = Y[i] > 127

    real_cap = []
    for i in sel:
        real_cap += [p[2] / p[-1] for p in ev.cap_profiles(refs[i])]

    rows = {}
    for t in np.arange(-0.15, 0.051, 0.025):
        D, ink, cap, cham, lr = [], [], [], [], []
        for i in sel:
            m = raw[i] > t
            tgt = refs[i]
            D.append(2 * float((m & tgt).sum()) / max(1.0, float(m.sum() + tgt.sum())))
            ink.append(float(m.sum()) / max(1.0, float(tgt.sum())))
            cap += [p[2] / p[-1] for p in ev.cap_profiles(m)]
            sc = ss.score(m, tgt)
            if sc:
                cham.append(sc["skel_chamfer_px"]); lr.append(sc["len_ratio"])
        rows[f"{t:+.3f}"] = {
            "dice": round(float(np.mean(D)), 3),
            "ink": round(float(np.median(ink)), 3),
            "len_ratio": round(float(np.median(lr)), 3),
            "chamfer": round(float(np.median(cham)), 3),
            "cap_ks": round(float(ks_2samp(real_cap, cap).statistic), 3),
            "cap_mid": round(float(np.median(cap)), 3),
        }
        print(f"t={t:+.3f}  " + "  ".join(f"{k} {v}" for k, v in rows[f'{t:+.3f}'].items()), flush=True)

    # failure rates for GAN at t=0 and for ribbon, for reference
    rib_dice = []
    for i in sel:
        m, tgt = ribs[i], refs[i]
        rib_dice.append(2 * float((m & tgt).sum()) / max(1.0, float(m.sum() + tgt.sum())))
    Dg = []
    for i in sel:
        m = raw[i] > 0
        tgt = refs[i]
        Dg.append(2 * float((m & tgt).sum()) / max(1.0, float(m.sum() + tgt.sum())))
    fail = {
        "n": len(sel),
        "ribbon": {"mean": round(float(np.mean(rib_dice)), 4),
                   "p5": round(float(np.percentile(rib_dice, 5)), 4),
                   "min": round(float(np.min(rib_dice)), 4),
                   "frac_below_0.30": round(float(np.mean(np.array(rib_dice) < 0.30)), 4)},
        "gan_t0": {"mean": round(float(np.mean(Dg)), 4),
                   "p5": round(float(np.percentile(Dg, 5)), 4),
                   "min": round(float(np.min(Dg)), 4),
                   "frac_below_0.30": round(float(np.mean(np.array(Dg) < 0.30)), 4)},
    }
    Path(ROOT / "work" / "failure_rates.json").write_text(json.dumps(fail, ensure_ascii=False, indent=1))
    Path(args.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("\nfailure_rates:", json.dumps(fail, ensure_ascii=False))
    print("->", args.out)


if __name__ == "__main__":
    main()
