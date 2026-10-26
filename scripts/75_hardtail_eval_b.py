#!/usr/bin/env python3
"""Systematic evaluation of the hard tail (the chars that fall back to ribbon).

The ~1,135 fallback characters never appear in the manuscript, so there is no glyph to
compare against — Dice/chamfer can't be computed.  What *can* be measured is whether the
ink looks like the manuscript's ink: the 4,078 genuine glyphs define a stroke-width
distribution, and a synthetic glyph should sit inside it.

Three quantities per glyph, all scale-free (divided by the em box):
  sw_med   median stroke half-width        (too low = spidery, too high = bold)
  sw_p99   99th percentile half-width      (large = a blob / fused strokes)
  blob     area fraction of pixels thicker than the genuine p99 (the visible defect)

`blob` is the metric that matches what the eye sees on 儷/傻/廬: fused ink in one place.

  python3 scripts/75_hardtail_eval_b.py --ckpts work-b/ckpt/b_ep080.pt \\
             work-b/ckpt/b_wt_ep090.pt work-b/ckpt/b_wt_ep100.pt --n 400
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

sys.path.insert(0, str(Path(__file__).parent))
torch.set_num_threads(1)
import brush_lib as B  # noqa: E402
from generate_lib import render_base, ribbon_scale_b  # noqa: E402
from shiji_page import repair_counters  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WD = ROOT / "work-b"
REL = json.loads((ROOT / "data" / "release-b.json").read_text())
S = 512
GR = 256


def load_gan(path):
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("train_gan", ROOT / "scripts" / "21_train_gan.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    ck = torch.load(path, map_location="cpu")
    g = mod.Generator().eval()
    g.load_state_dict(ck["G"])
    return g


def metrics(m: np.ndarray) -> dict:
    m = m.astype(np.uint8)
    ys, xs = np.nonzero(m)
    if len(xs) < 80:
        return dict(sw_med=float("nan"), sw_p99=float("nan"), blob=float("nan"))
    w = max(1, xs.max() - xs.min())
    dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    v = dt[m > 0]
    return dict(sw_med=float(np.median(v)) / w,
                sw_p99=float(np.percentile(v, 99)) / w,
                blob=None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpts", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=400, help="0 = every fallback")
    ap.add_argument("--json", default=str(WD / "hardtail_eval.json"))
    args = ap.parse_args()

    src = {json.loads(l)["char"]: json.loads(l).get("src") for l in open(WD / "generated.jsonl")}
    fb = [c for c, s in src.items() if s != "gen"]
    if args.n:
        fb = fb[: args.n]
    print(f"fallback glyphs tested: {len(fb)}")

    font = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S)
    f256 = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), GR)
    rel_w = np.load(WD / "stroke_rel_width.npy")

    # ---- reference: the genuine glyphs, measured the same way
    from fontTools.ttLib import TTFont
    real_font = str(ROOT / "build" / "GuanGeKai-B-Real.ttf")
    rf = ImageFont.truetype(real_font, S)
    real_cps = sorted(TTFont(real_font).getBestCmap())
    ref = []
    for cp in real_cps:
        ch = chr(cp)
        m = np.zeros((S, S), np.uint8)
        from PIL import Image, ImageDraw
        im = Image.new("L", (S, S), 0)
        ImageDraw.Draw(im).text((S // 2, int(0.88 * S)), ch, fill=255, font=rf, anchor="ms")
        m = (np.array(im) > 127).astype(np.uint8)
        if m.sum() < 200:
            continue
        ys, xs = np.nonzero(m)
        w = max(1, xs.max() - xs.min())
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        ref.append((float(np.median(dt[m > 0])) / w, float(np.percentile(dt[m > 0], 99)) / w))
    R = np.array(ref)
    p99 = np.percentile(R[:, 1], 99)
    med_lo, med_hi = np.percentile(R[:, 0], 5), np.percentile(R[:, 0], 95)
    print(f"reference (genuine, n={len(R)}): sw_med 5–95% = {med_lo:.3f}–{med_hi:.3f}, "
          f"sw_p99 = {p99:.3f}")

    def blob_frac(m):
        """Local fusing: share of ink thicker than 2.5x this glyph's own median half-width.

        A merged junction or a smeared component creates a locally very thick region, which
        is exactly what the eye reads as "糊".  Normalising by the glyph's own median makes
        the measure independent of how bold the whole glyph is.
        """
        m = m.astype(np.uint8)
        if m.sum() < 80:
            return float("nan")
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        v = dt[m > 0]
        med = float(np.median(v))
        if med <= 0:
            return float("nan")
        return float((v > 2.5 * med).sum()) / max(1, len(v))

    rows = {Path(c).stem: [] for c in args.ckpts}
    ribbon_rows = []
    Gs = {Path(c).stem: load_gan(c) for c in args.ckpts}
    for ch in fb:
        base_img = render_base(font, ch, S)
        wm = base_img > 127
        gin = render_base(f256, ch, GR)
        a = (gin.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        for name, G in Gs.items():
            with torch.no_grad():
                g = G(torch.from_numpy(a).float()).numpy()[0, 0] > REL["threshold"]
            g = cv2.resize(g.astype(np.uint8) * 255, (S, S), interpolation=cv2.INTER_LINEAR) > 127
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (REL["close"], REL["close"]))
            g = cv2.morphologyEx(g.astype(np.uint8), cv2.MORPH_CLOSE, k) > 0
            if REL["hole_repair"]:
                g, _ = repair_counters(g, ch, base_close=REL["close"])
            rows[name].append((ch, blob_frac(g), metrics(g)))
        fr = B.glyph_frames(wm, S)
        rng = np.random.RandomState(ord(ch) % (2 ** 31))
        raw = rng.choice(rel_w, size=len(fr), replace=True)
        raw /= max(1e-6, raw.mean())
        w = np.power(raw, 1.4)
        w /= max(1e-6, w.mean())
        rib = B.render_ribbon(fr, scale=ribbon_scale_b(float(wm.sum()) * (256.0 / S) ** 2),
                              dips=w, end_skew=0.9, taper=0.2, size=S, ss=2)
        rib = np.asarray(rib)
        rib = rib > 0 if rib.max() <= 1 else rib > 127
        ribbon_rows.append((ch, blob_frac(rib), metrics(rib)))

    print("\n  blob = share of ink >2.5x the glyph's own median half-width (local fusing)")
    def summarise(name, rs):
        bl = np.array([r[1] for r in rs], float)
        md = np.array([r[2]["sw_med"] for r in rs], float)
        p = np.array([r[2]["sw_p99"] for r in rs], float)
        out = 0 if np.all(np.isnan(md)) else int(((md < med_lo) | (md > med_hi)).sum())
        print(f"  {name:16s} blob {np.nanmean(bl)*100:5.2f}%   "
              f"sw_med {np.nanmedian(md):.3f}   sw_p99 {np.nanmedian(p):.3f}   "
              f"out-of-range {out}/{len(md)} ({100*out/len(md):.1f}%)")
        return bl, md

    print("\nper model, over the same fallback glyphs:")
    res = {}
    for name in rows:
        res[name] = summarise(name, rows[name])
    rb = summarise("ribbon (shipped)", ribbon_rows)

    print("\npaired win-rate (lower blob = less local fusing):")
    names = list(rows)

    def pair(a, b, na, nb):
        A = np.array([r[1] for r in a], float)
        Bv = np.array([r[1] for r in b], float)
        ok = ~(np.isnan(A) | np.isnan(Bv))
        win = (A[ok] < Bv[ok]).mean()
        print(f"  {na} better than {nb}: {win*100:5.1f}%  (n={ok.sum()})")

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pair(rows[names[i]], rows[names[j]], names[i], names[j])
    for n in names:
        pair(rows[n], ribbon_rows, n, "ribbon")

    Path(args.json).write_text(json.dumps({k: [[r[0], r[1]] for r in v] for k, v in rows.items()},
                                          ensure_ascii=False))
    print("->", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
