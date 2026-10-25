"""Evaluate methods on the 617 single-occurrence glyphs (never used in training)."""
import json, sys
from pathlib import Path
import numpy as np
import torch
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B
from generate_lib import ribbon_scale as _rs
from importlib import import_module
ev = import_module("18_eval")
from importlib.util import spec_from_file_location, module_from_spec


def main():
    d = np.load(ROOT / "work/pairs_single.npz", allow_pickle=True)
    X, Y = d["X"], d["Y"]
    sel = list(range(0, len(X), 5))[:120]
    REL = np.load(ROOT / "work/stroke_rel_width.npy")

    spec = spec_from_file_location("gan", ROOT / "scripts/21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    import argparse as _ap
    _p = _ap.ArgumentParser(); _p.add_argument("--gan", default=str(ROOT / "work" / "zi2zi_gan.pt"))
    _p.add_argument("--label", default="GAN"); _a = _p.parse_args()
    G = gan.Generator(); G.load_state_dict(torch.load(_a.gan, map_location="cpu")["G"]); G.eval()

    def ribbon(i):
        wm = X[i] > 127
        fr = B.glyph_frames(wm)
        rng = np.random.RandomState(i); raw = rng.choice(REL, size=len(fr), replace=True)
        w = np.power(raw, 1.4); w = w / max(1e-6, float(w.mean()))
        return B.render_ribbon(fr, scale=_rs(float(wm.sum())), dips=w, end_skew=0.9, taper=0.2)

    def gan_fn(i):
        a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            return G(torch.from_numpy(a).float()).numpy()[0, 0] > 0

    real_cap = []
    for i in sel:
        real_cap += [p[2] / p[-1] for p in ev.cap_profiles(Y[i] > 127)]
    rows = {}
    for name, fn in (("霞鹜文楷", lambda i: X[i] > 127), ("ribbon", ribbon), (f"GAN {Path(_a.gan).stem}", gan_fn)):
        D, ink, cap = [], [], []
        for i in sel:
            m = fn(i); t = Y[i] > 127
            D.append(B.dice(m, t)); ink.append(m.sum() / max(1, t.sum()))
            cap += [p[2] / p[-1] for p in ev.cap_profiles(m)]
        rows[name] = dict(dice=round(float(np.mean(D)), 3), ink=round(float(np.mean(ink)), 3),
                          cap_mid=round(float(np.median(cap)), 3),
                          cap_ks=round(float(ks_2samp(real_cap, cap).statistic), 3), n=len(sel))
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    json.dump(rows, open(ROOT / "work/eval_singles.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
