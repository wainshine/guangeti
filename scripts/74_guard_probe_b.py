#!/usr/bin/env python3
"""Why do 6.7% of the glyphs fall back to ribbon, and would a looser guard help?

The guard (`ink` inside [0.6, 1.5] of WenKai + component count within 3) was calibrated
*before* the counter repair made the GAN output thicker.  For every character that
shipped as `base` (ribbon fallback) this probe recomputes, with the released
post-processing, the three guard quantities and then asks:

  * how far outside the band they are (a handful just outside ⇒ cheap win)
  * what the GAN output would look like structurally (chamfer to WenKai) versus the
    ribbon that actually shipped

  python3 scripts/74_guard_probe_b.py            # report only
  python3 scripts/74_guard_probe_b.py --n 200    # sample
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
GAN_RES = 256


def load_gan(path):
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("train_gan", ROOT / "scripts" / "21_train_gan.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    import torch as t
    ck = t.load(path, map_location="cpu")
    g = mod.Generator().eval()
    g.load_state_dict(ck["G"])
    return g


def chamfer(a: np.ndarray, b: np.ndarray) -> float:
    from scipy.ndimage import distance_transform_edt
    from skimage.morphology import skeletonize
    sa, sb = skeletonize(a), skeletonize(b)
    if not sa.any() or not sb.any():
        return float("nan")
    da = distance_transform_edt(~sa)
    db = distance_transform_edt(~sb)
    return float((db[sa].mean() + da[sb].mean()) / 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=0, help="0 = all fallbacks")
    ap.add_argument("--ckpt", default="",
                    help="checkpoint to probe (default: the released one in "
                         "data/release-b.json)")
    ap.add_argument("--json", default=str(WD / "guard_probe.json"))
    args = ap.parse_args()

    base = [json.loads(l)["char"] for l in open(WD / "generated.jsonl")]
    src = {json.loads(l)["char"]: json.loads(l).get("src") for l in open(WD / "generated.jsonl")}
    fb = [c for c in base if src[c] != "gen"]
    if args.n:
        fb = fb[: args.n]
    print(f"fallback glyphs: {len(fb)}")

    gan = load_gan(Path(args.ckpt) if args.ckpt else ROOT / REL["checkpoint"])
    rel_w = np.load(WD / "stroke_rel_width.npy")
    font = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S)
    font256 = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), GAN_RES)
    lo, hi = REL["threshold"], None
    band = (0.6, 1.5)
    rows = []
    for ch in fb:
        base_img = render_base(font, ch, S)
        wm = base_img > 127
        gin = render_base(font256, ch, GAN_RES)
        a = (gin.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            g = gan(torch.from_numpy(a).float()).numpy()[0, 0] > lo
        g = cv2.resize(g.astype(np.uint8) * 255, (S, S), interpolation=cv2.INTER_LINEAR) > 127
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (REL["close"], REL["close"]))
        g = cv2.morphologyEx(g.astype(np.uint8), cv2.MORPH_CLOSE, k) > 0
        if REL["hole_repair"]:
            g, _ = repair_counters(g, ch, base_close=REL["close"])
        n, _l, st, _ = cv2.connectedComponentsWithStats(g.astype(np.uint8), 8)
        amin = max(6, int(round(20 * (S / 256.0) ** 2)))
        comps = sum(1 for i in range(1, n) if st[i, 4] >= amin)
        nw, _l2, sw, _ = cv2.connectedComponentsWithStats(wm.astype(np.uint8), 8)
        comps_w = sum(1 for i in range(1, nw) if sw[i, 4] >= amin)
        ink = float(g.sum()) / max(1.0, float(wm.sum()))
        rows.append(dict(char=ch, ink=ink, comps=comps - comps_w,
                         cm_gan=chamfer(g, wm)))
    ink = np.array([r["ink"] for r in rows])
    dc = np.array([abs(r["comps"]) for r in rows])
    print(f"ink ratio  p10 {np.percentile(ink,10):.2f}  median {np.median(ink):.2f}  "
          f"p90 {np.percentile(ink,90):.2f}")
    print(f"  inside {band}: {((ink>=band[0])&(ink<=band[1])).mean()*100:.1f}%")
    for b in ((0.55, 1.65), (0.5, 1.8), (0.45, 2.0)):
        print(f"  inside {b}: {((ink>=b[0])&(ink<=b[1])).mean()*100:.1f}%")
    print(f"|dcomponents| <=3: {(dc<=3).mean()*100:.1f}%   <=6: {(dc<=6).mean()*100:.1f}%")
    both = ((ink >= 0.5) & (ink <= 1.8) & (dc <= 6)).mean()
    print(f"pass with band 0.5–1.8 + comps<=6: {both*100:.1f}%")
    cm = np.array([r["cm_gan"] for r in rows])
    print(f"GAN chamfer to WenKai  median {np.nanmedian(cm):.2f}")
    Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("->", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
