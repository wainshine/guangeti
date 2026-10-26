"""Compute per-glyph normalisation (bbox -> base font bbox) for the real glyphs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from glyphvec import (base_bounds, clean_ink, contour_bounds, trace,  # noqa: E402
                      normalize_to_base, to_em)

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
CELLS = WORK / "cells"
BLEND = 0.8


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work"),
                    help="working directory (the B line uses work-b)")
    ap.add_argument("--pitch-floor", type=float, default=200.0,
                    help="guard against absurd pitches; 四書 at 300 dpi is 310, 史記 is 175")
    args = ap.parse_args()
    wd = Path(args.work)
    meta = {json.loads(l)["file"]: json.loads(l) for l in open(wd / "cells.jsonl")}
    chosen = [json.loads(l) for l in open(wd / "chosen.jsonl")]
    out = {}
    for row in chosen:
        ch = row["label"]
        m = meta.get(row["file"])
        if not m or not ch:
            continue
        mpath = wd / "masks" / row["file"]
        if not mpath.exists():
            continue
        ink = clean_ink(np.array(Image.open(mpath).convert("L")) > 127)
        cs = trace(ink)
        if not cs:
            continue
        scale = 880.0 / max(args.pitch_floor, m["pitch"])
        pad = 6
        em = to_em(cs, scale, m["x0"] - pad, m["y0"] - pad,
                   (m["x0"] + m["x1"]) / 2, (m["slot"][0] + m["slot"][1]) / 2,
                   em_cx=500.0, em_cy=440.0)
        bb = base_bounds(ch)
        if bb is None:
            out[ch] = dict(sx=1.0, sy=1.0, dx=0.0, dy=0.0, scale=scale,
                           origin=(m["x0"] - pad, m["y0"] - pad),
                           slot_cx=(m["x0"] + m["x1"]) / 2,
                           slot_cy=(m["slot"][0] + m["slot"][1]) / 2)
            continue
        x0, y0, x1, y1 = contour_bounds(em)
        w, h = max(1e-3, x1 - x0), max(1e-3, y1 - y0)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        sx = min(max((BLEND * tw + (1 - BLEND) * w) / w, 0.6), 1.7)
        sy = min(max((BLEND * th + (1 - BLEND) * h) / h, 0.6), 1.7)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        dx = (bb[0] + bb[2]) / 2 - cx * sx
        dy = (bb[1] + bb[3]) / 2 - cy * sy
        out[ch] = dict(sx=float(sx), sy=float(sy), dx=float(dx), dy=float(dy), scale=float(scale),
                       origin=(m["x0"] - pad, m["y0"] - pad),
                       slot_cx=float((m["x0"] + m["x1"]) / 2),
                       slot_cy=float((m["slot"][0] + m["slot"][1]) / 2))
    with open(wd / "norm.json", "w") as f:
        json.dump(out, f)
    print("norm computed for", len(out))


if __name__ == "__main__":
    main()
