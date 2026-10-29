"""B-line: build the complete font build/GuanGeKai-B-Regular.ttf.

Forked from `11_build_full.py`; family name `GuanGe Kai B`, work-b paths.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fontbuild import build_font  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "work-b"
BLOCK = (0x4E00, 0x9FFF)
FAMILY = "GuanGe Kai B"
VERSION = "1.3.0"
COPYRIGHT = ("GuanGe Kai B (館閣楷 B). Real glyphs traced from the Ming manuscript 史記 "
             "(attributed to 姜立綱), NUS Libraries 藏本 / digitised by NUS Libraries. "
             "Generated glyphs derived from LXGW WenKai (OFL 1.1). "
             "Copyright 2026 The GuanGe Kai Project Authors. SIL OFL 1.1.")


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
    ap.add_argument("--work", default=str(WB))
    ap.add_argument("--out", default=str(ROOT / "build" / "GuanGeKai-B-Regular.ttf"))
    ap.add_argument("--min-real", type=int, default=1000)
    ap.add_argument("--allow-missing", action="store_true",
                    help="dry-run only: build even when coverage is incomplete")
    ap.add_argument("--drop-outside-basic", action="store_true",
                    help="drop glyphs outside 0x4E00-0x9FFF (the 5 extension-A forms) so the "
                         "cmap matches the advertised basic-block coverage")
    args = ap.parse_args()
    wd = Path(args.work)
    real = load(wd / "real_contours.jsonl")
    if args.drop_outside_basic:
        real = {k: v for k, v in real.items() if BLOCK[0] <= ord(k) <= BLOCK[1]}
    gen = load(wd / "generated.jsonl")
    glyphs = {}
    for ch in sorted(set(real) | set(gen)):
        glyphs[ch] = real[ch] if ch in real else gen[ch]
    in_block = sum(1 for c in range(BLOCK[0], BLOCK[1] + 1) if chr(c) in glyphs)
    missing = (BLOCK[1] - BLOCK[0] + 1) - in_block
    print(f"real {len(real)} gen {len(gen)} total {len(glyphs)} "
          f"(basic block {in_block}/{BLOCK[1]-BLOCK[0]+1}) missing {missing}")
    if (len(real) < args.min_real or missing > 0) and not args.allow_missing:
        raise SystemExit(f"ABORT: real={len(real)} missing={missing} — refusing to write a "
                         f"font whose real glyphs are absent or whose coverage is incomplete")
    build_font(glyphs, Path(args.out), family=FAMILY, style="Regular", version=VERSION,
               copyright_text=COPYRIGHT)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
