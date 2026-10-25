"""Build paired rasters (base font render -> book glyph) for style transfer."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CELLS = ROOT / "work" / "cells"
OUT = ROOT / "work" / "pairs"
S = 256
EM_TOP, EM_BOT = 880.0, -120.0
PAD = 6

FONT_PATH = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"


def render_base(chars, path):
    font = ImageFont.truetype(str(FONT_PATH), S)  # UPM 1000 -> S px
    out = {}
    for ch in chars:
        img = Image.new("L", (S, S), 0)
        d = ImageDraw.Draw(img)
        baseline = EM_TOP * S / 1000.0
        d.text((0, baseline), ch, fill=255, font=font, anchor="ls")
        out[ch] = np.array(img, dtype=np.uint8)
    return out


def book_raster(m, path, nrm):
    img = np.array(Image.open(path).convert("L"))
    scale = nrm["scale"]
    slot_cx, slot_cy = nrm["slot_cx"], nrm["slot_cy"]
    px0, py0 = m["x0"] - PAD, m["y0"] - PAD
    # page -> em units
    a = scale * S / 1000.0
    # em -> canvas px, including the per-glyph normalisation
    a *= nrm["sx"]
    bscale = scale * S / 1000.0 * nrm["sy"]
    tx = (((px0 - slot_cx) * scale + 500) * nrm["sx"] + nrm["dx"]) * S / 1000.0
    ty = (880 - nrm["dy"] - 440 * nrm["sy"]
          - (slot_cy - py0) * scale * nrm["sy"]) * S / 1000.0
    M = np.array([[a, 0, tx], [0, bscale, ty]], dtype=np.float32)
    warped = cv2.warpAffine(img, M, (S, S), flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    return warped


def book_raster_ink(m, ink, nrm):
    scale = nrm["scale"]
    slot_cx, slot_cy = nrm["slot_cx"], nrm["slot_cy"]
    px0, py0 = m["x0"] - PAD, m["y0"] - PAD
    a = scale * S / 1000.0 * nrm["sx"]
    bscale = scale * S / 1000.0 * nrm["sy"]
    tx = (((px0 - slot_cx) * scale + 500) * nrm["sx"] + nrm["dx"]) * S / 1000.0
    ty = (880 - nrm["dy"] - 440 * nrm["sy"] - (slot_cy - py0) * scale * nrm["sy"]) * S / 1000.0
    M = np.array([[a, 0, tx], [0, bscale, ty]], dtype=np.float32)
    return cv2.warpAffine(ink, M, (S, S), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def to_ink(gray):
    gray = cv2.medianBlur(gray, 3)
    thr, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thr = min(max(thr, 110), 200)
    ink = (gray < thr).astype(np.uint8)
    # drop specks
    n, lab, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    keep = np.zeros(n, np.uint8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= 20:
            keep[i] = 1
    ink = keep[lab]
    soft = cv2.GaussianBlur(ink.astype(np.float32) * 255, (0, 0), 0.9)
    return soft.astype(np.uint8)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sigma", type=float, default=1.0, help="target blur; 0.5 keeps corners sharper")
    ap.add_argument("--out", default=str(ROOT / "work" / "pairs" / "pairs.npz"))
    _a = ap.parse_args()
    meta = {json.loads(l)["file"]: json.loads(l) for l in open(ROOT / "work" / "cells.jsonl")}
    chosen = [json.loads(l) for l in open(ROOT / "work" / "chosen.jsonl")]
    norm = json.load(open(ROOT / "work" / "norm.json"))
    OUT.mkdir(parents=True, exist_ok=True)
    chars, targets = [], []
    for r in chosen:
        m = meta.get(r["file"])
        if not m:
            continue
        nrm = norm.get(r["label"])
        if not nrm:
            continue
        mpath = ROOT / "work" / "masks" / r["file"]
        if not mpath.exists():
            continue
        ink = np.array(Image.open(mpath).convert("L"))
        ink = (ink > 127).astype(np.uint8) * 255
        g = book_raster_ink(m, ink, nrm)
        chars.append(r["label"])
        targets.append(cv2.GaussianBlur(g.astype(np.float32), (0, 0), _a.sigma).astype(np.uint8))
    bases = render_base(chars, None)
    # stack into a npz
    X = np.stack([bases[c] for c in chars]).astype(np.uint8)
    Y = np.stack(targets).astype(np.uint8)
    np.savez_compressed(_a.out, X=X, Y=Y, chars=np.array(chars, dtype=object))
    print("pairs", X.shape, Y.shape, "chars", len(set(chars)))
    # preview sheet
    n = min(12, len(chars))
    sheet = Image.new("L", (S * n, S * 2), 0)
    for i in range(n):
        sheet.paste(Image.fromarray(X[i]), (i * S, 0))
        sheet.paste(Image.fromarray(Y[i]), (i * S, S))
    sheet.resize((S * n // 2, S)).save(ROOT / "work" / "preview" / "pairs.png")
    print("wrote pairs")


if __name__ == "__main__":
    main()
