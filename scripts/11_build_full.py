"""Build the complete CJK font from real + generated glyphs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fontbuild import VERSION, build_font  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BLOCK = (0x4E00, 0x9FFF)


def load(path):
    out = {}
    p = Path(path)
    if not p.exists():
        return out
    for line in open(p):
        r = json.loads(line)
        out[r["char"]] = r["contours"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "build" / "GuanGeKai-Regular.ttf"))
    ap.add_argument("--real", default=str(ROOT / "work" / "real_contours.jsonl"))
    ap.add_argument("--gen", default=str(ROOT / "work" / "generated.jsonl"))
    args = ap.parse_args()
    real = load(args.real)
    gen = load(args.gen)
    glyphs = {}
    for c in range(BLOCK[0], BLOCK[1] + 1):
        ch = chr(c)
        if ch in real:
            glyphs[ch] = real[ch]
        elif ch in gen:
            glyphs[ch] = gen[ch]
    print(f"real {len(real)} gen {len(gen)} total {len(glyphs)} / {BLOCK[1]-BLOCK[0]+1}")
    missing = (BLOCK[1] - BLOCK[0] + 1) - len(glyphs)
    print("missing", missing)
    if len(real) < 1000 or missing > 0:
        raise SystemExit(
            f"ABORT: real={len(real)} missing={missing} — refusing to write a font "
            f"whose real glyphs are absent (run 07_build_real.py first)")
    build_font(glyphs, Path(args.out), family="GuanGe Kai", version=VERSION,
               copyright_text=(
                   "GuanGe Kai (館閣楷). Real glyphs extracted from the Ming woodblock print "
                   "四書白文 (attributed to 姜立綱), scans courtesy of 書格 shuge.org / 宮内庁書陵部. "
                   "Generated glyphs derived from LXGW WenKai (OFL 1.1). "
                   "Copyright 2026 The GuanGe Kai Project Authors."
               ))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
