"""Same-character chamfer floor for the A line (E32's "5.16" made reproducible).

Why this exists: E32 quotes a floor of 5.16 px ("two genuine samples of the same
character"), and every claim of the form "GAN is only 15% worse than the floor"
depends on it.  Until now no script and no artifact produced that number, so the
denominator of the headline metric could not be re-derived by anyone.

Input:  work/pairs_multi.npz  (1,675 chars, 2-4 genuine samples each)
Metric: identical to 65_eval_b.chamfer() / 34_struct_score: centroid-aligned
        bidirectional skeleton chamfer, in px at 256.
Output: work/chamfer_floor.json  (median, 95% bootstrap CI, n, seed, KS/MW vs GAN)

Usage:
    python3 scripts/43_chamfer_floor.py                 # floor only
    python3 scripts/43_chamfer_floor.py --gan work/ckpt/m2wt_ep090.pt --n-gan 300
                                                        # + KS/MW against GAN outputs
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402

SEED = 7
N_PAIRS = 800


def shift_to_centroid(mask, ref):
    import cv2
    ys, xs = np.where(mask)
    ys2, xs2 = np.where(ref)
    if len(xs) == 0 or len(xs2) == 0:
        return mask
    M = np.float32([[1, 0, xs2.mean() - xs.mean()], [0, 1, ys2.mean() - ys.mean()]])
    return cv2.warpAffine(mask.astype(np.uint8), M, (mask.shape[1], mask.shape[0])) > 0


def chamfer(mask, ref):
    from scipy.ndimage import distance_transform_edt
    a = shift_to_centroid(mask, ref)
    sks = B.skeleton_of(a)
    skr = B.skeleton_of(ref.astype(bool))
    if sks.sum() < 10 or skr.sum() < 10:
        return None
    d_to_r = distance_transform_edt(~skr)
    d_to_s = distance_transform_edt(~sks)
    return 0.5 * (float(d_to_r[sks].mean()) + float(d_to_s[skr].mean()))


def floor_pairs(seed=SEED, n=N_PAIRS):
    d = np.load(ROOT / "work" / "pairs_multi.npz", allow_pickle=True)
    Y = d["Y"]
    chars = [str(c) for c in d["chars"]]
    by = {}
    for i, c in enumerate(chars):
        by.setdefault(c, []).append(i)
    rng = np.random.RandomState(seed)
    cand = [(c, idx) for c, idx in by.items() if len(idx) >= 2]
    rng.shuffle(cand)
    vals = []
    for c, idx in cand:
        if len(vals) >= n:
            break
        i, j = rng.choice(idx, 2, replace=False)
        v = chamfer(Y[i] > 0, Y[j] > 0)
        if v is not None:
            vals.append(v)
    return np.array(vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gan", default=None, help="checkpoint for the KS/MW comparison")
    ap.add_argument("--n-gan", type=int, default=300)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--n", type=int, default=N_PAIRS)
    ap.add_argument("--out", default=str(ROOT / "work" / "chamfer_floor.json"))
    ap.add_argument("--reset", action="store_true",
                    help="drop hand-written keys from an existing output file (default: keep them)")
    ap.add_argument("--clean617", default="", help="pairs_single.npz to measure GAN on unseen singles")
    ap.add_argument("--gan-ckpt", default=str(ROOT / "work" / "ckpt" / "m2wt_ep090.pt"),
                    help="checkpoint used with --clean617 / --gan")
    args = ap.parse_args()

    v = floor_pairs(args.seed, args.n)
    rng = np.random.RandomState(args.seed)
    boots = [np.median(rng.choice(v, len(v), replace=True)) for _ in range(2000)]
    out = {
        "metric": "skeleton chamfer, centroid-aligned, bidirectional, px@256",
        "source": "work/pairs_multi.npz (two distinct genuine samples of the same char)",
        "seed": args.seed, "n_pairs": int(len(v)),
        "median": round(float(np.median(v)), 3),
        "mean": round(float(v.mean()), 3),
        "p10": round(float(np.percentile(v, 10)), 3),
        "p90": round(float(np.percentile(v, 90)), 3),
        "ci95_bootstrap": [round(float(np.percentile(boots, 2.5)), 3),
                           round(float(np.percentile(boots, 97.5)), 3)],
        "cmd": f"python3 scripts/43_chamfer_floor.py --seed {args.seed} --n {args.n}",
    }

    if args.clean617:
        import torch
        from importlib.util import module_from_spec, spec_from_file_location
        spec = spec_from_file_location("ganlib", ROOT / "scripts" / "21_train_gan.py")
        m21 = module_from_spec(spec); spec.loader.exec_module(m21)
        G = m21.Generator()
        sd = torch.load(args.gan_ckpt, map_location="cpu")
        G.load_state_dict(sd["G"] if isinstance(sd, dict) and "G" in sd else sd)
        G.eval()
        d617 = np.load(ROOT / args.clean617, allow_pickle=True)
        X6, Y6 = d617["X"], d617["Y"]
        vals = []
        for i in range(len(d617["chars"])):
            a = (X6[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
            with torch.no_grad():
                m = G(torch.from_numpy(a).float()).numpy()[0, 0] > -0.05
            c = chamfer(m, Y6[i] > 0)
            if c is not None:
                vals.append(c)
        v6 = np.array(vals)
        out["gan_clean617"] = {
            "ckpt": args.gan_ckpt, "n": int(len(v6)),
            "median": round(float(np.median(v6)), 3),
            "mean": round(float(v6.mean()), 3),
            "cmd": (f"python3 scripts/43_chamfer_floor.py --clean617 {args.clean617} "
                    f"--gan-ckpt {args.gan_ckpt}"),
            "note": "unseen single-occurrence chars; floor is from repeated chars, do not divide",
        }

    if args.gan:
        import torch
        from importlib.util import module_from_spec, spec_from_file_location
        from scipy.stats import ks_2samp, mannwhitneyu
        spec = spec_from_file_location("ganlib", ROOT / "scripts" / "21_train_gan.py")
        m21 = module_from_spec(spec); spec.loader.exec_module(m21)
        G = m21.Generator()
        sd = torch.load(args.gan, map_location="cpu")
        G.load_state_dict(sd["G"] if isinstance(sd, dict) and "G" in sd else sd)
        G.eval()
        d = np.load(ROOT / "work" / "pairs_multi.npz", allow_pickle=True)
        X, Y, chars = d["X"], d["Y"], [str(c) for c in d["chars"]]
        idx = rng.choice(len(chars), min(args.n_gan, len(chars)), replace=False)
        gv = []
        for i in idx:
            a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
            with torch.no_grad():
                m = G(torch.from_numpy(a).float()).numpy()[0, 0] > -0.05
            c = chamfer(m, Y[i] > 0)
            if c is not None:
                gv.append(c)
        gv = np.array(gv)
        out["gan"] = {
            "ckpt": str(args.gan), "n": int(len(gv)),
            "median": round(float(np.median(gv)), 3),
            "ks_stat": round(float(ks_2samp(v, gv).statistic), 4),
            "ks_p": float(ks_2samp(v, gv).pvalue),
            "mw_p": float(mannwhitneyu(v, gv, alternative="two-sided").pvalue),
            "ratio_to_floor": round(float(np.median(gv) / np.median(v)), 4),
        }

    # keep hand-written annotations (population_note / ratio_caveat / measured blocks):
    # a plain rerun used to erase the very caveats that E9 depends on.
    out_p = Path(args.out)
    if out_p.exists() and not args.reset:
        try:
            old = json.loads(out_p.read_text())
        except Exception:
            old = {}
        for k in ("population_note", "ratio_caveat", "gan_clean617", "gan_in_sample"):
            if k in old and k not in out:
                out[k] = old[k]
        out["preserved_keys"] = sorted(k for k in out if k in
                                       ("population_note", "ratio_caveat", "gan_clean617", "gan_in_sample"))

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
