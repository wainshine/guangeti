"""Compare the trained zi2zi-GAN against the shipped renderer on the held-out set."""
import argparse, json, sys
from pathlib import Path
import importlib.util
import numpy as np
import torch
from scipy.stats import ks_2samp

sys.path.insert(0, str(Path(__file__).parent))
import brush_lib as B
ev = __import__("importlib").import_module("18_eval")
ROOT = Path(__file__).resolve().parents[1]


def load_gen(ckpt):
    spec = importlib.util.spec_from_file_location("gan", ROOT / "scripts/21_train_gan.py")
    gan = importlib.util.module_from_spec(spec); spec.loader.exec_module(gan)
    G = gan.Generator()
    ck = torch.load(ckpt, map_location="cpu")
    G.load_state_dict(ck["G"]); G.eval()
    return G


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default=str(ROOT / "work/zi2zi_gan.pt"))
    ap.add_argument("--n", type=int, default=142)
    args = ap.parse_args()
    d = np.load(ROOT / "work/pairs/pairs.npz", allow_pickle=True)
    chars = [str(c) for c in d["chars"]]; Y = d["Y"]; X = d["X"]
    pos = {c: i for i, c in enumerate(chars)}
    clean = json.load(open(ROOT / "work/eval_clean.json"))[:args.n]
    G = load_gen(args.ckpt)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    G.to(dev)
    dice, cap, real_cap, std = [], [], [], []
    for ch in clean:
        i = pos[ch]
        a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            out = G(torch.from_numpy(a).float().to(dev)).cpu().numpy()[0, 0]
        m = out > 0; t = Y[i] > 127
        dice.append(float(2 * (m & t).sum() / max(1, (m.sum() + t.sum()))))
        cap += [p[2] / p[-1] for p in ev.cap_profiles(m)]
        real_cap += [p[2] / p[-1] for p in ev.cap_profiles(t)]
        for f in B.glyph_frames(m):
            n = len(f["pts"])
            if n < 24: continue
            r = f["r_obs"]; med = float(np.median(r[n//3:2*n//3]))
            if med >= 2: std.append(float(np.std(r / med)))
    res = {"n": len(clean), "dice": round(float(np.mean(dice)), 3),
           "cap_mid": round(float(np.median(cap)), 3),
           "cap_real": round(float(np.median(real_cap)), 3),
           "cap_ks": round(float(ks_2samp(real_cap, cap).statistic), 3),
           "stroke_std": round(float(np.median(std)), 3)}
    print(json.dumps(res, indent=1))
    (ROOT / "work/eval_gan.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
