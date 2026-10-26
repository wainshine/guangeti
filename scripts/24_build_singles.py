"""Build the single-occurrence test set (617 glyphs never used in training)."""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from glyphvec import clean_ink, trace, to_em, contour_bounds, base_bounds

ROOT = Path(__file__).resolve().parents[1]
S, PAD, BLEND = 256, 6, 0.8
SIGMA = 1.0   # target blur; keep in sync with 08_make_pairs --sigma


def main():
    import argparse
    ap = argparse.ArgumentParser()
    # default 0: the released clean set (work/pairs_single.npz) is UNBLURRED, while the
    # training targets use 1.0 — re-running with the old default silently changed it (audit 2-10)
    ap.add_argument("--sigma", type=float, default=0.0)
    ap.add_argument("--work", default=str(ROOT / "work"),
                    help="working directory (the B line uses work-b)")
    ap.add_argument("--pitch-floor", type=float, default=200.0)
    ap.add_argument("--out", default="")
    ap.add_argument("--from-chosen", default="",
                    help="build the set from a chosen.jsonl-like file instead of the "
                         "singletons (used for the same-character chamfer floor)")
    _a = ap.parse_args()
    globals()["SIGMA"] = _a.sigma
    wd = Path(_a.work)
    meta = {json.loads(l)["file"]: json.loads(l) for l in open(wd / "cells.jsonl")}
    rows = [json.loads(l) for l in open(wd / "labeled.jsonl")]
    cnt = collections.Counter(r["label"] for r in rows if r.get("label"))
    if _a.from_chosen:
        singles = [json.loads(l) for l in open(_a.from_chosen)]
        singles = [r for r in singles if r.get("label")]
    else:
        singles = [r for r in rows if r.get("label") and cnt[r["label"]] == 1]
        # A clean set must be DISJOINT from the training pairs.  The B line admits 271
        # high-confidence singletons into chosen.jsonl, and without this exclusion they
        # would count as "never trained" while having been trained on (30% of the set).
        have = set()
        cp = wd / "chosen.jsonl"
        if cp.exists():
            have = {json.loads(l)["label"] for l in open(cp)}
        n0 = len(singles)
        singles = [r for r in singles if r["label"] not in have]
        print(f"clean set: dropped {n0-len(singles)} singletons that are in chosen.jsonl")

    norm = {}
    for row in singles:
        ch, m, mp = row["label"], meta.get(row["file"]), wd / "masks" / row["file"]
        if not m or not mp.exists():
            continue
        cs = trace(clean_ink(np.array(Image.open(mp).convert("L")) > 127))
        if not cs:
            continue
        scale = 880.0 / max(_a.pitch_floor, m["pitch"])
        em = to_em(cs, scale, m["x0"] - PAD, m["y0"] - PAD,
                   (m["x0"] + m["x1"]) / 2, (m["slot"][0] + m["slot"][1]) / 2,
                   em_cx=500.0, em_cy=440.0)
        bb = base_bounds(ch)
        d = dict(scale=float(scale), origin=(m["x0"] - PAD, m["y0"] - PAD), file=row["file"],
                 slot_cx=float((m["x0"] + m["x1"]) / 2),
                 slot_cy=float((m["slot"][0] + m["slot"][1]) / 2))
        if bb is None:
            d.update(sx=1.0, sy=1.0, dx=0.0, dy=0.0)
        else:
            x0, y0, x1, y1 = contour_bounds(em)
            w, h = max(1e-3, x1 - x0), max(1e-3, y1 - y0)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            sx = min(max((BLEND * tw + (1 - BLEND) * w) / w, 0.6), 1.7)
            sy = min(max((BLEND * th + (1 - BLEND) * h) / h, 0.6), 1.7)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            d.update(sx=float(sx), sy=float(sy),
                     dx=float((bb[0] + bb[2]) / 2 - cx * sx),
                     dy=float((bb[1] + bb[3]) / 2 - cy * sy))
        norm[ch] = d

    def book_ink(m, ink, nrm):
        sc = nrm["scale"]; scx, scy = nrm["slot_cx"], nrm["slot_cy"]
        px0, py0 = m["x0"] - PAD, m["y0"] - PAD
        a = sc * S / 1000.0 * nrm["sx"]; bs = sc * S / 1000.0 * nrm["sy"]
        tx = (((px0 - scx) * sc + 500) * nrm["sx"] + nrm["dx"]) * S / 1000.0
        ty = (880 - nrm["dy"] - 440 * nrm["sy"] - (scy - py0) * sc * nrm["sy"]) * S / 1000.0
        M = np.array([[a, 0, tx], [0, bs, ty]], np.float32)
        return cv2.warpAffine(ink, M, (S, S), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    chars = sorted(norm)
    font = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S)
    X = np.zeros((len(chars), S, S), np.uint8)
    Y = np.zeros((len(chars), S, S), np.uint8)
    for i, ch in enumerate(chars):
        nrm = norm[ch]; m = meta[nrm["file"]]
        img = Image.new("L", (S, S), 0)
        ImageDraw.Draw(img).text((0, 880 * S / 1000), ch, fill=255, font=font, anchor="ls")
        X[i] = np.array(img)
        g = np.array(Image.open(wd / "cells" / nrm["file"]).convert("L"))
        Y[i] = book_ink(m, (g < 160).astype(np.uint8) * 255, nrm)
        if SIGMA >= 0:
            Y[i] = cv2.GaussianBlur(Y[i].astype(np.float32), (0, 0), SIGMA).astype(np.uint8)
    out = Path(_a.out) if _a.out else wd / "pairs_single.npz"
    np.savez_compressed(out, X=X, Y=Y, chars=np.array(chars))
    json.dump(norm, open(wd / "norm_single.json", "w"), ensure_ascii=False)
    print(f"singles: {len(chars)} glyphs -> {out}")


if __name__ == "__main__":
    main()
