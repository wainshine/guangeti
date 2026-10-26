"""B-line evaluation: the five required metrics + graded skeleton distance.

Every number is measured against **this book's own** genuine glyphs
(work-b/pairs_single.npz: characters that occur exactly once in the 史記 copy and were
therefore never used for training).  No 四書 asset enters the acceptance criteria — the
two books are different hands and comparing across them measures the wrong thing.

Reported together (a single number always misleads: Dice rewards weight):
    dice          binarised overlap with the genuine glyph
    ink           ink area ratio  method / genuine
    cap_mid       median terminal-width profile at 1.6 widths inward (genuine: ~0.52)
    cap_ks        KS between the method's terminal profile and the genuine one
    stroke_std    median within-stroke width variation
    chamfer       mean skeleton distance (px at 256) to the genuine skeleton

  python3 scripts/65_eval_b.py --gan work-b/ckpt/b_ep080.pt --n 200
"""
from __future__ import annotations

import argparse
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import torch
torch.set_num_threads(1)   # audit 3-25: CPU inference must stay single-threaded
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402
from generate_lib import ribbon_scale_b  # noqa: E402

S = 256


def load_gan(path):
    spec = spec_from_file_location("ganlib", ROOT / "scripts" / "21_train_gan.py")
    m = module_from_spec(spec)
    spec.loader.exec_module(m)
    g = m.Generator()
    g.load_state_dict(torch.load(path, map_location="cpu")["G"])
    g.eval()
    return g


def skel_stats(sk):
    import cv2
    k = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], np.uint8)
    nb = cv2.filter2D(sk.astype(np.uint8), -1, k)
    n1, _ = cv2.connectedComponents((sk & (nb == 1)).astype(np.uint8), 8)
    n2, _ = cv2.connectedComponents((sk & (nb >= 3)).astype(np.uint8), 8)
    return max(0, n1 - 1), max(0, n2 - 1)


def shift_to_centroid(mask, ref):
    import cv2
    mask = mask.astype(bool)
    ref = ref.astype(bool)
    ys, xs = np.nonzero(mask)
    ys2, xs2 = np.nonzero(ref)
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


def stroke_std(mask):
    out = []
    for f in B.glyph_frames(mask):
        n = len(f["pts"])
        if n < 24:
            continue
        r = f["r_obs"]
        med = float(np.median(r[n // 3: 2 * n // 3]))
        if med >= 2:
            out.append(float(np.std(r / med)))
    return out


def caps(mask):
    return [p[2] / p[-1] for p in __import__("importlib").import_module("18_eval").cap_profiles(mask)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--eval-data", default="")
    ap.add_argument("--gan", action="append", default=[])
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--thr", type=float, default=0.0,
                    help="GAN output threshold for the headline rows (calibrated so the "
                         "ink ratio is 1.00; see E4's threshold sweep)")
    ap.add_argument("--sweep", action="store_true",
                    help="report Dice / ink for the first --gan checkpoint at several "
                         "output thresholds (ink should land near 1.00)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    wd = Path(args.work)
    data = Path(args.eval_data) if args.eval_data else wd / "pairs_single.npz"
    d = np.load(data, allow_pickle=True)
    X, Y = d["X"], d["Y"]
    chars = [str(c) for c in d["chars"]]
    rng = np.random.RandomState(0)
    sel = np.sort(rng.choice(len(X), min(args.n, len(X)), replace=False))
    print(f"eval set {data.name}: n={len(sel)} of {len(X)} single-occurrence glyphs")

    rel = np.load(wd / "stroke_rel_width.npy")

    def wk(i):
        return X[i] > 127

    def ribbon(i, ch=None):
        wm = X[i] > 127
        fr = B.glyph_frames(wm, S)
        # audit 3-23: production seeds by ord(ch); seeding by array index here meant the
        # evaluated glyph used a different ribbon-width sample than the shipped one
        r = np.random.RandomState(int(ord(ch) % (2 ** 31)) if ch else int(i))
        raw = r.choice(rel, size=len(fr), replace=True)
        raw /= max(1e-6, raw.mean())
        w = np.power(raw, 1.4)
        w /= max(1e-6, w.mean())
        return B.render_ribbon(fr, scale=ribbon_scale_b(float(wm.sum())), dips=w,
                               end_skew=0.9, taper=0.2, size=S, ss=2)

    methods = [("霞鹜文楷原样", wk), ("ribbon", ribbon)]
    for path in args.gan:
        G = load_gan(path)
        thr = args.thr

        def gan_fn(i, G=G, thr=thr):
            a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
            with torch.no_grad():
                return G(torch.from_numpy(a).float()).numpy()[0, 0] > thr

        methods.append((Path(path).stem, gan_fn))

    if args.sweep and args.gan:
        G = load_gan(args.gan[0])
        print("\nthreshold sweep on the clean set")
        print(f"{'thr':>6s} {'dice':>6s} {'ink':>6s} {'broken':>7s}")
        for thr in (-0.30, -0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20, 0.30):
            D, ink = [], []
            for i in sel:
                a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
                with torch.no_grad():
                    m = G(torch.from_numpy(a).float()).numpy()[0, 0] > thr
                t = Y[i] > 127
                D.append(2 * float((m & t).sum()) / max(1.0, float(m.sum() + t.sum())))
                ink.append(float(m.sum()) / max(1.0, float(t.sum())))
            print(f"{thr:6.2f} {np.mean(D):6.3f} {np.median(ink):6.3f} "
                  f"{np.mean(np.array(D) < 0.30) * 100:6.1f}%")
        return

    # genuine reference statistics (computed once)
    real_cap = []
    for i in sel:
        real_cap += caps(Y[i] > 127)
    rows = {}
    print(f"\n{'method':20s} {'dice':>6s} {'ink':>6s} {'cap':>6s} {'capKS':>6s} "
          f"{'std':>6s} {'chamfer':>8s} {'崩坏率':>7s}")
    for name, fn in methods:
        D, ink, cap, std, ch = [], [], [], [], []
        for i in sel:
            m = fn(i, chars[i]) if fn is ribbon else fn(i)
            t = Y[i] > 127
            D.append(2 * float((m & t).sum()) / max(1.0, float(m.sum() + t.sum())))
            ink.append(float(m.sum()) / max(1.0, float(t.sum())))
            cap += caps(m)
            std += stroke_std(m)
            c = chamfer(m, t)
            if c is not None:
                ch.append(c)
        row = dict(n=len(sel), dice=round(float(np.mean(D)), 3),
                   ink=round(float(np.median(ink)), 3),
                   cap_mid=round(float(np.median(cap)), 3),
                   cap_ks=round(float(ks_2samp(real_cap, cap).statistic), 3),
                   stroke_std=round(float(np.median(std)), 3),
                   chamfer=round(float(np.median(ch)), 2),
                   broken=round(float(np.mean(np.array(D) < 0.30)), 3))
        rows[name] = row
        print(f"{name:20s} {row['dice']:6.3f} {row['ink']:6.3f} {row['cap_mid']:6.3f} "
              f"{row['cap_ks']:6.3f} {row['stroke_std']:6.3f} {row['chamfer']:8.2f} "
              f"{row['broken']*100:6.1f}%")
    # Same-character floor: how far apart are two genuine samples of the SAME glyph?
    # Built from pairs.npz (medoid) and pairs_second.npz (runner-up) — without it the
    # chamfer number has no scale, and pairing *different* characters (an earlier bug)
    # reports a meaningless "floor" of ~10 px.
    sec = wd / "pairs/pairs_second.npz"
    first = wd / "pairs/pairs.npz"
    fl = []
    if sec.exists() and first.exists():
        d1 = np.load(first, allow_pickle=True)
        ds = np.load(sec, allow_pickle=True)
        pos = {str(c): i for i, c in enumerate(ds["chars"])}
        chs = [str(c) for c in d1["chars"]]
        Y1, Ys = d1["Y"], ds["Y"]
        # 3,799 pairs x two distance transforms is the slowest part of the evaluation;
        # a fixed 800-pair sample gives the same median to within a few hundredths.
        idx = [i for i, c in enumerate(chs) if pos.get(c) is not None]
        rngf = np.random.RandomState(1)
        if len(idx) > 800:
            idx = list(rngf.choice(idx, 800, replace=False))
        for i in idx:
            j = pos[chs[i]]
            v = chamfer(Ys[j] > 127, Y1[i] > 127)
            if v is not None:
                fl.append(v)
        rows["_floor_same_char"] = dict(n=len(fl), chamfer=round(float(np.median(fl)), 2))
        print(f"{'真跡互比地板':17s} {'':6s} {'':6s} {'':6s} {'':6s} {'':6s} "
              f"{np.median(fl):8.2f}   (same character, two genuine samples, n={len(fl)})")
    rows["_genuine_cap_mid"] = round(float(np.median(real_cap)), 3)
    out = Path(args.out) if args.out else wd / "eval_b.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("genuine cap_mid", rows["_genuine_cap_mid"], "->", out)


if __name__ == "__main__":
    main()
