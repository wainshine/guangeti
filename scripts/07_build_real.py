"""Build the real-glyph subset font (characters present in the scanned book)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from fontbuild import VERSION, build_font  # noqa: E402
from glyphvec import binarize, clean_ink, trace, to_em, normalize_to_base, transform  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CELLS = ROOT / "work" / "cells"


def main():
    # Fast path: the contours are already extracted; no need for work/masks.
    if "--reuse-contours" in sys.argv:
        cache = ROOT / "work" / "real_contours.jsonl"
        if not cache.exists():
            raise SystemExit(f"ABORT: {cache} missing")
        glyphs = {}
        for line in open(cache):
            r = json.loads(line)
            glyphs[r["char"]] = r["contours"]
        if len(glyphs) < 1000:
            raise SystemExit(f"ABORT: only {len(glyphs)} cached glyphs")
        build_font(glyphs, Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv
                   else ROOT / "build" / "GuanGeKai-Real.ttf",
                   family="GuanGe Kai", style="Real", version=VERSION,
                   copyright_text="GuanGe Kai — extracted from 四書白文 (Ming, attributed to 姜立綱). Scans: 書格 shuge.org / 宮内庁書陵部. SIL OFL 1.1.")
        print("wrote (from cached contours)")
        return
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=str(ROOT / "build" / "GuanGeKai-Real.ttf"))
    ap.add_argument("--reuse-contours", action="store_true",
                    help="rebuild from work/real_contours.jsonl when work/masks has been cleared")
    args = ap.parse_args()

    meta = {}
    for line in open(ROOT / "work" / "cells.jsonl"):
        r = json.loads(line)
        meta[r["file"]] = r

    chosen = [json.loads(l) for l in open(ROOT / "work" / "chosen.jsonl")]
    norm = json.load(open(ROOT / "work" / "norm.json"))
    if args.limit:
        chosen = chosen[: args.limit]

    glyphs = {}
    used_files = {}
    for row in chosen:
        f = row["file"]
        m = meta.get(f)
        if not m:
            continue
        ch = row["label"]
        if not ch or ch in glyphs:
            continue
        mpath = ROOT / "work" / "masks" / f
        if not mpath.exists():
            continue
        ink = np.array(Image.open(mpath).convert("L")) > 127
        ink = clean_ink(ink)
        if ink.sum() < 60:
            continue
        contours = trace(ink)
        if not contours:
            continue
        scale = 880.0 / max(200.0, m["pitch"])
        pad = 6
        page_x0 = m["x0"] - pad
        page_y0 = m["y0"] - pad
        slot_cx = (m["x0"] + m["x1"]) / 2
        slot_cy = (m["slot"][0] + m["slot"][1]) / 2
        em = to_em(contours, scale, page_x0, page_y0, slot_cx, slot_cy, em_cx=500.0, em_cy=440.0)
        n = norm.get(ch)
        if n:
            em = transform(em, n["sx"], n["sy"], n["dx"], n["dy"])
        glyphs[ch] = em
        used_files[ch] = f
    print("glyphs", len(glyphs))
    if len(glyphs) < 1000:
        raise SystemExit(f"ABORT: only {len(glyphs)} real glyphs — refusing to overwrite "
                         f"build/GuanGeKai-Real.ttf and work/real_contours.jsonl "
                         f"(check that work/masks/ and work/cells/ exist)")
    with open(ROOT / "work" / "real_contours.jsonl", "w") as fh:
        for ch, cs in glyphs.items():
            fh.write(json.dumps({"char": ch, "contours": cs, "src": "real"}, ensure_ascii=False) + "\n")
    build_font(glyphs, Path(args.out), family="GuanGe Kai", style="Real", version=VERSION,
               copyright_text="GuanGe Kai — extracted from 四書白文 (Ming, attributed to 姜立綱). Scans: 書格 shuge.org / 宮内庁書陵部. SIL OFL 1.1.")
    print("wrote", args.out)
    with open(ROOT / "work" / "real_glyph_sources.json", "w") as fh:
        json.dump(used_files, fh, ensure_ascii=False)


if __name__ == "__main__":
    main()
