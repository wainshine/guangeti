"""Multi-instance pairs: one base render per char, up to K real samples per char.

The single-instance version (08_make_pairs.py) trains on the medoid sample only,
which is 2.9% of the 53k available cells. Seeing K variants per character teaches
the model the *distribution* of the print's strokes instead of one instance.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
S = 256
FONT_PATH = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"
PAD = 6


def render_base(ch: str) -> np.ndarray:
    font = ImageFont.truetype(str(FONT_PATH), S)
    img = Image.new("L", (S, S), 0)
    ImageDraw.Draw(img).text((0, 880 * S / 1000.0), ch, fill=255, font=font, anchor="ls")
    return np.array(img, dtype=np.uint8)


def book_ink(m, ink, nrm):
    scale = nrm["scale"]
    # slot_cx/cy are cell-specific (the norm was fitted on one sample per char),
    # so take them from *this* cell instead of reusing the chosen sample's
    slot_cx = (m["x0"] + m["x1"]) / 2
    slot_cy = (m["slot"][0] + m["slot"][1]) / 2
    px0, py0 = m["x0"] - PAD, m["y0"] - PAD
    a = scale * S / 1000.0 * nrm["sx"]
    b = scale * S / 1000.0 * nrm["sy"]
    tx = (((px0 - slot_cx) * scale + 500) * nrm["sx"] + nrm["dx"]) * S / 1000.0
    ty = (880 - nrm["dy"] - 440 * nrm["sy"] - (slot_cy - py0) * scale * nrm["sy"]) * S / 1000.0
    M = np.array([[a, 0, tx], [0, b, ty]], dtype=np.float32)
    return cv2.warpAffine(ink, M, (S, S), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=4, help="max samples per character")
    ap.add_argument("--out", default=str(ROOT / "work" / "pairs_multi.npz"))
    args = ap.parse_args()

    meta = {json.loads(l)["file"]: json.loads(l) for l in open(ROOT / "work" / "cells.jsonl")}
    chosen = [json.loads(l) for l in open(ROOT / "work" / "chosen.jsonl")]
    norm = json.load(open(ROOT / "work" / "norm.json"))
    by_char = collections.defaultdict(list)
    for l in open(ROOT / "work" / "labeled.jsonl"):
        r = json.loads(l)
        if r.get("label") and r["file"] in meta:
            by_char[r["label"]].append(r["file"])
    keep_chars = {r["label"] for r in chosen}
    X, Y, names, inst = [], [], [], []
    for ch in sorted(keep_chars):
        nrm = norm.get(ch)
        if not nrm:
            continue
        files = [f for f in by_char.get(ch, []) if (ROOT / "work" / "masks" / f).exists()]
        if not files:
            continue
        # prefer the medoid first, then the sharpest variants
        pref = {r["file"]: r.get("sharp", 0) for r in chosen if r["label"] == ch}
        files.sort(key=lambda f: (-1 if f in pref else 0, -pref.get(f, 0)))
        base = render_base(ch)
        for j, f in enumerate(files[: args.k]):
            m = meta[f]
            ink = np.array(Image.open(ROOT / "work" / "masks" / f).convert("L"))
            ink = (ink > 127).astype(np.uint8) * 255
            g = book_ink(m, ink, nrm)
            X.append(base)
            Y.append(cv2.GaussianBlur(g.astype(np.float32), (0, 0), 1.0).astype(np.uint8))
            names.append(ch)
            inst.append(j)
    X = np.stack(X).astype(np.uint8)
    Y = np.stack(Y).astype(np.uint8)
    np.savez_compressed(args.out, X=X, Y=Y, chars=np.array(names, dtype=object),
                        inst=np.array(inst, dtype=np.int8))
    print(f"pairs {X.shape[0]} from {len(set(names))} chars -> {args.out}")


if __name__ == "__main__":
    main()
