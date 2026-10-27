"""B-line: build the genuine-glyph subset font (build/GuanGeKai-B-Real.ttf).

Forked from `07_build_real.py`; differences:
  * reads/writes work-b/ instead of work/
  * family name `GuanGe Kai B` (two glyph sources must stay distinguishable)
  * the pitch guard is 100 px, not 200 (this scan's character pitch is ~175 at 300 dpi)
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
from glyphvec import clean_ink, to_em, trace, transform  # noqa: E402
from shiji_page import repair_counters  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FAMILY = "GuanGe Kai B"
VERSION = "1.2.0"
COPYRIGHT = ("GuanGe Kai B (館閣楷 B). Real glyphs traced from the Ming manuscript "
             "史記 (attributed to 姜立綱), NUS Libraries 藏本 / digitised by NUS Libraries. "
             "Generated glyphs derived from LXGW WenKai (OFL 1.1). "
             "Copyright 2026 The GuanGe Kai Project Authors. SIL OFL 1.1.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--out", default=str(ROOT / "build" / "GuanGeKai-B-Real.ttf"))
    ap.add_argument("--pitch-floor", type=float, default=100.0)
    ap.add_argument("--min-glyphs", type=int, default=1000)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--hole-repair", action="store_true",
                    help="escalate the closing kernel for glyphs that still have no counter "
                         "where WenKai draws one (audit rev3 2-3)")
    ap.add_argument("--close", type=int, default=0,
                    help="morphological closing kernel before tracing. The scan's thin "
                         "strokes leave 1-2 px gaps, so counters leak to the outside and "
                         "potrace sees no hole (audit P0). 3 seals them; 0 = old behaviour")
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
        if args.close:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (args.close, args.close))
            ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, k) > 0
        if args.hole_repair:
            ink, shipped = repair_counters(ink, ch, base_close=args.close)
            if shipped:
                n_repaired += 1
        if ink.sum() < 60:
            continue
        contours = trace(ink)
        if not contours:
            continue
        scale = 880.0 / max(args.pitch_floor, m["pitch"])
        pad = 6
        em = to_em(contours, scale, m["x0"] - pad, m["y0"] - pad,
                   (m["x0"] + m["x1"]) / 2, (m["slot"][0] + m["slot"][1]) / 2,
                   em_cx=500.0, em_cy=440.0)
        n = norm.get(ch)
        if n:
            em = transform(em, n["sx"], n["sy"], n["dx"], n["dy"])
        glyphs[ch] = em
        used[ch] = f
    print("glyphs", len(glyphs), f"(counter repair with a bigger kernel: {n_repaired})")
    if len(glyphs) < args.min_glyphs:
        raise SystemExit(f"ABORT: only {len(glyphs)} real glyphs — refusing to overwrite "
                         f"{args.out} and work-b/real_contours.jsonl")
    with open(wd / "real_contours.jsonl", "w") as fh:
        for ch, cs in glyphs.items():
            fh.write(json.dumps({"char": ch, "contours": cs, "src": "real"},
                                ensure_ascii=False) + "\n")
    build_font(glyphs, Path(args.out), family=FAMILY, style="Real", version=VERSION,
               copyright_text=COPYRIGHT)
    json.dump(used, open(wd / "real_glyph_sources.json", "w"), ensure_ascii=False)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
