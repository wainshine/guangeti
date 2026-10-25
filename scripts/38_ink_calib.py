"""E35: can a constant ink offset make synthetic glyphs match the print's weight?

The GAN output is uniformly ~17% heavier than the print (E34). This measures what a
sub-pixel erosion of the binarised output does to ink, Dice, chamfer and the cap metrics.
"""
from __future__ import annotations

import sys
from pathlib import Path
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location

import cv2
import numpy as np
import torch
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
ev = import_module("18_eval")
ss = import_module("34_struct_score")


def main():
    d = np.load(ROOT / "work/pairs_single.npz", allow_pickle=True)
    X, Y = d["X"], d["Y"]
    sel = np.random.RandomState(7).choice(len(X), 150, replace=False)
    spec = spec_from_file_location("gan", ROOT / "scripts/21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    G = gan.Generator()
    G.load_state_dict(torch.load(ROOT / "work/ckpt/m2_ep080.pt", map_location="cpu")["G"])
    G.eval()

    outs = {}
    for i in sel:
        a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            outs[i] = G(torch.from_numpy(a).float()).numpy()[0, 0]

    real_cap = []
    for i in sel:
        real_cap += [p[2] / p[-1] for p in ev.cap_profiles(Y[i] > 127)]

    print(f"{'r(px)':>6s} {'墨量比':>7s} {'Dice':>6s} {'chamfer':>8s} {'capKS':>6s} {'capMid':>7s}")
    for r in (0.0, 0.3, 0.5, 0.7, 1.0, 1.3, 1.6):
        D, ink, cap, ch = [], [], [], []
        for i in sel:
            m = outs[i] > -0.05
            if r > 0:
                dt = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
                m = dt > r
            t = Y[i] > 127
            D.append(2 * float((m & t).sum()) / max(1.0, float(m.sum() + t.sum())))
            ink.append(float(m.sum()) / max(1.0, float(t.sum())))
            cap += [p[2] / p[-1] for p in ev.cap_profiles(m)]
            s = ss.score(m, Y[i])
            if s:
                ch.append(s["skel_chamfer_px"])
        print(f"{r:6.1f} {np.median(ink):7.3f} {np.mean(D):6.3f} {np.median(ch):8.2f} "
              f"{ks_2samp(real_cap, cap).statistic:6.3f} {np.median(cap):7.3f}", flush=True)


if __name__ == "__main__":
    main()
