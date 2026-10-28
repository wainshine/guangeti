"""C-line: build the genuine-glyph subset font build/GuanGeKai-C-Real.ttf.

Forked from `57_build_real_b.py`.  Two differences that matter:

  * the normalisation scale comes from the *cell* advance `cpitch`, not the column
    pitch: a 小字双行 cell advances by half a 朱丝栏 column, and using the column
    pitch would shrink every small glyph by half;
  * the potrace origin is the stored crop origin (`cx0`,`cy0`), not `x0 - pad`, so
    the 300 dpi crop and the vectoriser agree pixel for pixel.

The C corpus is 300 dpi (史記 was 150), so no upsampling is involved; that also means
counter repair needs a slightly narrower closing kernel than the 512 px B recipe.

  python3 scripts/76_build_real_c.py --close 3 --hole-repair
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from fontbuild import build_font  # noqa: E402
from glyphvec import (adjust_mask_area, clamp_em_bbox, clean_ink, denoise_mask,  # noqa: E402
                      target_ink_256, to_em, trace, transform)
from shiji_page import _holes_at, wk_holes  # noqa: E402

# 四 is deliberately absent: its 寫本 form leaves the left side open (like 园), so the
# counter cannot be sealed without redrawing the character; it is excluded from the C
# counter whitelist and documented in EXPERIMENTS-C E15.
from shiji_page import repair_counters  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"
FAMILY = "GuanGe Kai C"
def _version():
    try:
        return json.loads((ROOT / "data" / "release-c.json").read_text())["version"]
    except Exception:
        return "1.1.0"


VERSION = _version()
COPYRIGHT = ("GuanGe Kai C (館閣楷 C). Real glyphs traced from the Ming manuscript "
             "永樂大典 (嘉靖隆慶間内府重寫本), Library of Congress 藏本 / digitised by "
             "the Library of Congress, distributed by 書格 shuge.org. "
             "Generated glyphs derived from LXGW WenKai (OFL 1.1). "
             "Copyright 2026 The GuanGe Kai Project Authors. SIL OFL 1.1.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(WORK))
    ap.add_argument("--out", default=str(ROOT / "build" / "GuanGeKai-C-Real.ttf"))
    ap.add_argument("--pitch-floor", type=float, default=180.0)
    ap.add_argument("--min-glyphs", type=int, default=1000)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--hole-repair", action="store_true", default=True,
                    help="escalate the closing kernel for glyphs that still have no "
                         "counter where WenKai draws one")
    ap.add_argument("--no-hole-repair", dest="hole_repair", action="store_false")
    ap.add_argument("--close", type=int, default=3,
                    help="morphological closing before tracing (px at 300 dpi)")
    ap.add_argument("--no-denoise", dest="denoise", action="store_false",
                    help="keep paper specks and pinholes (only for A/B comparison)")
    ap.add_argument("--no-ink-normalize", dest="ink_normalize", action="store_false",
                    help="do not pull each glyph's stroke weight onto the corpus ink curve "
                         "(multi-scribe weight patchwork is then kept)")
    ap.add_argument("--ink-a", type=float, default=38.7258)
    ap.add_argument("--ink-gain", type=float, default=1.10,
                    help="compensate the ~9%% area lost by the 256 px raster threshold "
                         "and potrace smoothing (measured on the C clean set)")
    ap.add_argument("--ink-exp", type=float, default=0.5701)
    ap.add_argument("--turdsize", type=int, default=3,
                    help="potrace speck filter; C's 300 dpi scans carry paper dust, "
                         "so 8 instead of A/B's 2")
    ap.add_argument("--alphamax", type=float, default=0.4)
    ap.add_argument("--opttol", type=float, default=0.5)
    args = ap.parse_args()
    wd = Path(args.work)

    meta = {}
    for line in open(wd / "cells.jsonl"):
        r = json.loads(line)
        meta[r["file"]] = r
    chosen = [json.loads(l) for l in open(wd / "chosen.jsonl")]
    norm = json.load(open(wd / "norm.json"))
    if args.limit:
        chosen = chosen[: args.limit]

    glyphs, used = {}, {}
    n_repaired = 0
    from collections import Counter
    stop_cnt = Counter()
    for row in chosen:
        f = row["file"]
        m = meta.get(f)
        if not m:
            continue
        ch = row["label"]
        if not ch or ch in glyphs:
            continue
        mpath = wd / "masks" / f
        if not mpath.exists():
            continue
        ink = clean_ink(np.array(Image.open(mpath).convert("L")) > 127)
        if args.denoise:
            ink = denoise_mask(ink)
        if args.close:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (args.close, args.close))
            ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, k) > 0
        cpitch = float(m.get("cpitch", m["pitch"]))
        scale = 880.0 / max(args.pitch_floor, min(760.0, cpitch))
        nrm_ch = norm.get(ch)
        # counters first: the manuscript often leaves an enclosure open, and sealing that
        # gap must happen before the weight adjustment (which can erode the gap wider)
        if args.hole_repair:
            ink, shipped = repair_counters(ink, ch, base_close=args.close,
                                           extra=(5, 7, 9, 11, 15, 19, 25, 31, 39),
                                           max_ink_gain=0.18, min_hole_area=6)
            if shipped:
                n_repaired += 1
        if args.ink_normalize and nrm_ch:
            tgt256 = target_ink_256(ch, args.ink_a, args.ink_exp) * args.ink_gain
            if tgt256 > 0:
                scx = scale * nrm_ch["sx"] * 256.0 / 1000.0
                scy = scale * nrm_ch["sy"] * 256.0 / 1000.0
                st = {}
                ink = adjust_mask_area(ink, tgt256 / max(1e-6, scx * scy), stats=st)
                stop_cnt[st.get("stop", "?")] += 1
        if ink.sum() < 60:
            continue
        contours = trace(ink, turdsize=args.turdsize, alphamax=args.alphamax,
                        opttol=args.opttol)
        if not contours:
            continue
        sx0, sx1 = m.get("slot_x", (m["x0"], m["x1"]))
        em = to_em(contours, scale, m.get("cx0", m["x0"] - 8), m.get("cy0", m["y0"] - 8),
                   (sx0 + sx1) / 2, (m["slot"][0] + m["slot"][1]) / 2,
                   em_cx=500.0, em_cy=440.0)
        n = norm.get(ch)
        if n:
            em = transform(em, n["sx"], n["sy"], n["dx"], n["dy"])
            em = clamp_em_bbox(em)
        glyphs[ch] = em
        used[ch] = f
    print("glyphs", len(glyphs), f"(counter repair with a bigger kernel: {n_repaired})")
    if stop_cnt:
        print("ink-calibration stop reasons:", dict(stop_cnt.most_common()))
    ctr = wd / ("real_contours.jsonl" if not args.limit
                else f"real_contours_limit{args.limit}.jsonl")
    if len(glyphs) < args.min_glyphs:
        raise SystemExit(f"ABORT: only {len(glyphs)} real glyphs — refusing to overwrite "
                         f"{args.out} and {ctr}")
    with open(ctr, "w") as fh:
        for ch, cs in glyphs.items():
            fh.write(json.dumps({"char": ch, "contours": cs, "src": "real"},
                                ensure_ascii=False) + "\n")
    build_font(glyphs, Path(args.out), family=FAMILY, style="Real", version=VERSION,
               copyright_text=COPYRIGHT)
    if not args.limit:
        json.dump(used, open(wd / "real_glyph_sources.json", "w"), ensure_ascii=False)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
