#!/usr/bin/env python3
"""B-line quality card: per-layer (real / gan / gan_ht / ribbon) measurements.

The shipped font mixes four sources (see release-b/provenance.json).  A single
font-level average hides any layer that drifted, so this script renders a fixed
sample of each layer from the *shipped* font and reports the same quantities
per layer:

    ink      ink area / WenKai ink for the same character (removes the "rare
             characters are denser" confound; cf. E34/E35)
    bbox     glyph bbox width / WenKai bbox width
    cap_mid  median terminal-width profile (18_eval.cap_profiles)

It also reports the fraction of each layer that falls outside the real layer's
p5-p95 band (the "tail" question: a layer can have the right median and still be
wrong for 10% of its glyphs) and splits the real layer by n_samples.

  python3 scripts/78_quality_card_b.py --n 300 --out work-b/quality_card_b.json
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

_m68 = importlib.import_module("68_accept_b")          # render_em / ink_and_centroid
_e18 = importlib.import_module("18_eval")              # cap_profiles

WK = str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf")
LAYERS = ("real", "gan", "gan_ht", "ribbon_fb")


def measure(ch: str, font: str) -> dict | None:
    try:
        m = _m68.render_em(ch, font)
        n, _, _ = _m68.ink_and_centroid(m)
        mw = _m68.render_em(ch, WK)
        nw, _, _ = _m68.ink_and_centroid(mw)
    except Exception:
        return None
    if n < 200 or nw < 200:
        return None
    ys, xs = np.nonzero(m)
    yw, xw = np.nonzero(mw)
    bw = (xs.max() - xs.min() + 1) / max(1, (xw.max() - xw.min() + 1))
    caps = []
    for pr in _e18.cap_profiles(m):
        if len(pr) > 2 and pr[-1] > 0:
            caps.append(float(pr[2] / pr[-1]))
    return {"ink": n / nw, "bbox": float(bw),
            "cap_mid": float(np.median(caps)) if caps else None}


def q(v, p):
    return float(np.percentile(np.asarray(v, dtype=float), p)) if v else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--release", default=str(ROOT / "release-b"))
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-B-Regular.ttf"))
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    wd, rel = Path(args.work), Path(args.release)
    prov = json.loads((rel / "provenance.json").read_text())
    by_layer: dict[str, list[str]] = {k: [] for k in LAYERS}
    for ch, src in prov.items():
        if src in by_layer:
            by_layer[src].append(ch)

    rng = np.random.RandomState(args.seed)
    rows: dict[str, list[dict]] = {}
    for name in LAYERS:
        chars = sorted(by_layer[name])
        if not chars:
            continue
        pick = [chars[i] for i in rng.choice(len(chars), min(args.n, len(chars)), replace=False)]
        out = [r for r in (measure(c, args.font) for c in pick) if r]
        rows[name] = out
        print(f"{name:10s} avail {len(chars):6d}  measured {len(out):4d}", flush=True)

    real = rows.get("real", [])
    rink = [r["ink"] for r in real]
    lo, hi = q(rink, 5), q(rink, 95)
    r_med = q(rink, 50)
    r_sd = float(np.std(rink)) if rink else 0.0

    card: dict[str, object] = {
        "font": str(Path(args.font).relative_to(ROOT)),
        "n_per_layer": args.n, "seed": args.seed,
        "note": ("ink = glyph ink / WenKai ink at 256px em; bbox = glyph bbox width / WenKai bbox width; "
                 "cap_mid = median terminal profile (18_eval.cap_profiles). "
                 "outside_real_band = fraction of the layer outside the real layer's p5-p95 ink band."),
    }
    for name, out in rows.items():
        ink = [r["ink"] for r in out]
        bbox = [r["bbox"] for r in out]
        cap = [r["cap_mid"] for r in out if r["cap_mid"] is not None]
        card[name] = {
            "n": len(out),
            "ink_med": q(ink, 50), "ink_p10": q(ink, 10), "ink_p90": q(ink, 90),
            "ink_vs_real": round(q(ink, 50) / r_med, 4) if r_med else None,
            "outside_real_band": round(sum(1 for v in ink if v < lo or v > hi) / len(ink), 4) if ink else None,
            "outside_2sigma": (round(sum(1 for v in ink if abs(v - r_med) > 2 * r_sd) / len(ink), 4)
                               if ink and r_sd else None),
            "bbox_med": q(bbox, 50),
            "cap_mid_med": q(cap, 50) if cap else None,
        }

    # real layer split by n_samples (single-sample glyphs are the weakest evidence)
    chosen = {json.loads(l)["label"]: json.loads(l) for l in open(wd / "chosen.jsonl")}
    singles = [c for c in sorted(by_layer["real"]) if chosen.get(c, {}).get("singleton")]
    card["real_by_samples"] = {
        "singleton_n": len(singles),
        "note": "singleton=true 的真迹只有一个图像样本；其 ink 分布应与多样本子集一致",
    }
    single_ink = []
    for c in singles[: args.n]:
        m = measure(c, args.font)
        if m:
            single_ink.append(m["ink"])
    if single_ink:
        card["real_by_samples"].update({
            "singleton_measured": len(single_ink),
            "ink_med": q(single_ink, 50),
            "ink_vs_real": round(q(single_ink, 50) / r_med, 4) if r_med else None,
        })

    print("\nlayer      n    ink_med  vs_real  p10-p90        outside  bbox   cap")
    for name in LAYERS:
        if name not in card:
            continue
        c = card[name]
        print(f"{name:10s} {c['n']:4d}  {c['ink_med']:.3f}   {c['ink_vs_real']:.3f}   "
              f"{c['ink_p10']:.3f}-{c['ink_p90']:.3f}   {c['outside_real_band']:.1%}   "
              f"{c['bbox_med']:.3f}  {c['cap_mid_med'] if c['cap_mid_med'] else float('nan'):.3f}")
    if single_ink:
        print(f"real·singleton {len(single_ink):3d}  {card['real_by_samples']['ink_med']:.3f}   "
              f"{card['real_by_samples']['ink_vs_real']:.3f}   (n_samples=1)")

    if args.out:
        Path(args.out).write_text(json.dumps(card, ensure_ascii=False, indent=1))
        print(f"\n-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
