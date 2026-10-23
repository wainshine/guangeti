"""Evaluation harness for v1.3 (M1).

Metrics per glyph: ink ratio, vert/horiz width ratio, hole count, filled-mask IoU
against a reference, and terminal shape descriptors (apex angle + roundness).

Usage:
  python3 scripts/18_eval.py --build-eval-set          # write data/eval_set.json
  python3 scripts/18_eval.py --self-check              # metric stability on real glyphs
  python3 scripts/18_eval.py --compare real synth      # KS between two populations
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.stats import ks_2samp
from skimage.morphology import skeletonize

sys.path.insert(0, str(Path(__file__).parent))
import brush_lib as B  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PAIRS = ROOT / "work/pairs/pairs.npz"
EVAL_SET = ROOT / "data/eval_set.json"
FONT = str(ROOT / "data/base/LXGWWenKai-Regular.ttf")


def load_pairs():
    d = np.load(PAIRS, allow_pickle=True)
    return [str(c) for c in d["chars"]], d["X"], d["Y"]


def brush_v121(mask: np.ndarray) -> np.ndarray:
    b = mask.astype(np.uint8)
    b = cv2.erode(b, np.ones((1, 3), np.uint8))
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return b > 0


def synth_of(ch: str) -> np.ndarray:
    return brush_v121(B.render_char(ch, FONT))


# ------------------------------------------------------------------ metrics
def ink_ratio(m, ref):
    return float(m.sum()) / max(1.0, ref.sum())


def width_ratio(m):
    mm = m.astype(np.uint8)
    dt = cv2.distanceTransform(mm, cv2.DIST_L2, 5)
    sk = skeletonize(m)
    if sk.sum() < 20:
        return None
    gx = cv2.Sobel(dt, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(dt, cv2.CV_32F, 0, 1, ksize=3)
    ys, xs = np.nonzero(sk)
    t = np.hypot(gx[ys, xs], gy[ys, xs]) + 1e-6
    v = np.abs(gx[ys, xs] / t)
    r = dt[ys, xs]
    vert, hor = r[v > 0.8], r[v < 0.3]
    if len(vert) < 30 or len(hor) < 30:
        return None
    return float(np.median(vert) / max(1e-3, np.median(hor)))


def hole_count(m):
    cnts, hier = cv2.findContours(m.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    return 0 if hier is None else int((hier[0, :, 3] >= 0).sum())


def cap_profiles(m, n=8, depth=1.6):
    """Cap shape: perpendicular width at t*w inward from each free end, /body width.

    Returns one (n,) array per usable stroke end.  Ends are rejected when the
    profile never reaches body width (near a junction or mis-oriented) -- r_obs at
    the skeleton endpoint itself is unreliable (it sits on the tip, DT ~1 px).
    """
    out = []
    for f in B.glyph_frames(m):
        npts = len(f["pts"])
        k = max(5, npts // 6)
        for idx, junc in ((0, f.get("start_junction")), (-1, f.get("end_junction"))):
            if junc:
                continue
            body = f["r_obs"][k:2 * k] if idx == 0 else f["r_obs"][-2 * k:-k]
            w = float(np.median(body)) if len(body) else float(f["r_obs"][idx])
            if w < 2.5:
                continue
            pts = f["pts"]
            kk = min(5, npts - 1)
            P = pts[idx].astype(np.float32)
            dd = pts[idx] - pts[kk if idx == 0 else -1 - kk]
            dd = dd / (np.linalg.norm(dd) + 1e-6)
            nrm = np.array([-dd[1], dd[0]])
            prof = []
            for t in np.linspace(0, depth, n):
                c = P - dd * (t * w)          # inward
                hit = 0.0
                for ss in np.arange(0.2 * w, 2.4 * w, 0.25):
                    for sg in (1, -1):
                        y = int(round(c[0] + sg * ss * nrm[0]))
                        x = int(round(c[1] + sg * ss * nrm[1]))
                        if 0 <= y < m.shape[0] and 0 <= x < m.shape[1] and m[y, x]:
                            hit = max(hit, ss)
                prof.append(hit / max(1e-6, w))
            p = np.array(prof)
            if p[-1] >= 0.7 and p[0] <= 0.9:
                out.append(p)
    return out


def cap_stats(m):
    ps = cap_profiles(m)
    if not ps:
        return None
    P = np.stack(ps)
    return {"cap_mid": float(np.median(P[:, 2] / P[:, -1])),
            "cap_near": float(np.median(P[:, 1] / P[:, -1])),
            "n_ends": int(len(P))}


def metrics(m, ref=None):
    d = {"ink": float(m.sum()),
         "holes": hole_count(m),
         "wratio": width_ratio(m)}
    if ref is not None:
        d["ink_ratio"] = ink_ratio(m, ref)
        inter = (m & ref).sum()
        d["iou"] = float(inter / max(1, (m | ref).sum()))
    cs = cap_stats(m)
    if cs:
        d.update(cs)
    return d


# ------------------------------------------------------------------ modes
def build_eval_set(out_path=None):
    chars, X, Y = load_pairs()
    ends = [len(cap_profiles(Y[i] > 127)) for i in range(len(chars))]
    order = np.argsort(ends)
    q = np.array_split(order, 4)
    rng = np.random.RandomState(2026)
    sel = []
    for part in q:
        sel.extend(rng.choice(part, 50, replace=False).tolist())
    out_p = Path(out_path) if out_path else EVAL_SET
    if out_p.exists() and not os.environ.get("EVAL_SET_FORCE"):
        raise SystemExit(f"refusing to overwrite {out_p}; set EVAL_SET_FORCE=1 to replace it")
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps({
        "seed": 2026,
        "n": len(sel),
        "note": "stratified by number of free stroke ends; fit on the remaining characters only",
        "chars": [chars[i] for i in sel],
        "indices": sel,
    }, ensure_ascii=False, indent=1))
    print(f"eval set: {len(sel)} chars -> {out_p}")


def run_compare(kind_a="real", kind_b="synth", limit=None):
    chars, X, Y = load_pairs()
    ev = json.loads(EVAL_SET.read_text())["indices"]
    if limit:
        ev = ev[:limit]
    rows = []
    for i in ev:
        real = Y[i] > 127
        syn = synth_of(chars[i])
        A = metrics(real)
        Bm = metrics(syn, ref=real)
        rows.append({"char": chars[i], "real": A, "synth": Bm})
    def vals(key, which):
        return [r[which][key] for r in rows if key in r[which]]
    ra, rs = vals("cap_mid", "real"), vals("cap_mid", "synth")
    out = {
        "n": len(rows),
        "cap_mid_real": float(np.median(ra)) if ra else None,
        "cap_mid_synth": float(np.median(rs)) if rs else None,
        "cap_mid_ks": float(ks_2samp(ra, rs).statistic) if ra and rs else None,
        "cap_near_ks": float(ks_2samp(vals("cap_near", "real"), vals("cap_near", "synth")).statistic),
        "ends_real": len(ra), "ends_synth": len(rs),
        "ink_ratio_med": float(np.median([r["synth"]["ink_ratio"] for r in rows])),
        "wratio_real_med": float(np.nanmedian([r["real"]["wratio"] for r in rows if r["real"]["wratio"]])),
        "wratio_syn_med": float(np.nanmedian([r["synth"]["wratio"] for r in rows if r["synth"]["wratio"]])),
        "holes_equal": float(np.mean([r["real"]["holes"] == r["synth"]["holes"] for r in rows])),
        "iou_med": float(np.median([r["synth"]["iou"] for r in rows])),
    }
    (ROOT / "work/eval_baseline.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))


def self_check():
    """Split the real glyphs in two halves; KS between halves = metric noise floor."""
    chars, X, Y = load_pairs()
    ev = set(json.loads(EVAL_SET.read_text())["indices"])
    fit_idx = [i for i in range(len(chars)) if i not in ev]
    rng = np.random.RandomState(7); rng.shuffle(fit_idx)
    h1, h2 = fit_idx[:len(fit_idx)//2], fit_idx[len(fit_idx)//2:]
    def collect(ids):
        v = []
        for i in ids:
            ps = cap_profiles(Y[i] > 127)
            if ps:
                v.extend((np.array(ps)[:, 2] / np.array(ps)[:, -1]).tolist())
        return np.array(v)
    a1, a2 = collect(h1), collect(h2)
    out = {"n_half": len(h1), "ends_h1": len(a1), "ends_h2": len(a2),
           "cap_mid_ks_between_halves": float(ks_2samp(a1, a2).statistic),
           "cap_mid_h1": float(np.median(a1)), "cap_mid_h2": float(np.median(a2))}
    (ROOT / "work/eval_stability.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-eval-set", action="store_true")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--compare", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    if a.build_eval_set: build_eval_set()
    elif a.self_check: self_check()
    elif a.compare is not None: run_compare(limit=a.limit)
    else: ap.print_help()
