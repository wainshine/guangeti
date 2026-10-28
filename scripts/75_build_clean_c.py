"""C-line: build the clean (holdout) set used for every generalisation number.

Forked from `24_build_singles.py`, but the selection rule is different: the C line
holds out whole pages (see `74_make_holdout_c.py`) because single-occurrence
characters are the least verifiable labels when there is no reference text.

Only cells on held-out pages that passed the A/B agreement are used, one per
character (the cleanest sample per label), and the target rasters are built with the
same normalisation as `06_norm.py` (cpitch + stored crop origin).

  python3 scripts/75_build_clean_c.py      # -> work-c/pairs_clean.npz
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from glyphvec import base_bounds, clean_ink, contour_bounds, to_em, trace  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"
S, BLEND = 256, 0.8
SIGMA = 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(WORK))
    ap.add_argument("--holdout", default=str(WORK / "holdout_pages.json"))
    ap.add_argument("--out", default="",
                    help="default: pairs_clean.npz for --rank 0, pairs_clean_second.npz for --rank 1")
    ap.add_argument("--pitch-floor", type=float, default=180.0)
    ap.add_argument("--sigma", type=float, default=0.0)
    ap.add_argument("--rank", type=int, default=0,
                    help="0 = best sample per character (the clean set); 1 = runner-up, "
                         "used to measure the same-character chamfer floor")
    ap.add_argument("--require-ab", action="store_true", default=True,
                    help="only cells whose two OCR witnesses agreed")
    ap.add_argument("--allow-a-only", dest="require_ab", action="store_false")
    ap.add_argument("--chars-file", default="",
                    help="JSON list of characters; build the set from their chosen samples "
                         "(character-level holdout, no page restriction)")
    args = ap.parse_args()
    wd = Path(args.work)
    hold = set(json.load(open(args.holdout)))
    meta = {json.loads(l)["file"]: json.loads(l) for l in open(wd / "cells.jsonl")}
    chars_file = set(json.load(open(args.chars_file))) if args.chars_file else None
    if chars_file is not None:
        chosen = {json.loads(l)["label"]: json.loads(l) for l in open(wd / "chosen.jsonl")}
        rows = [chosen[c] for c in sorted(chars_file) if c in chosen]
        picks = rows
        print(f"character holdout {len(chars_file)}; picked {len(picks)}")
    else:
        rows = [json.loads(l) for l in open(wd / "labeled.jsonl")]
        rows = [r for r in rows if r.get("label") and r.get("key") in hold
                and (r.get("agree_ab") or not args.require_ab)
                and not r.get("bad")]
        print(f"holdout pages {len(hold)}; candidate cells {len(rows)}")
        # one sample per character: prefer the least suspicious cell, then the largest
        by_char = defaultdict(list)
        for r in rows:
            by_char[r["label"]].append(r)
        picks = []
        for ch, cs in by_char.items():
            cs.sort(key=lambda r: (round(r.get("edge", 0), 3), -r["h"] * r["w"]))
            if len(cs) > args.rank:
                picks.append(cs[args.rank])
    print(f"characters {len(picks)}")

    font_path = ROOT / "data/base/LXGWWenKai-Regular.ttf"
    font = ImageFont.truetype(str(font_path), S)
    chars, X, Y, files, keys = [], [], [], [], []
    for row in picks:
        ch = row["label"]
        m = meta.get(row["file"])
        mp = wd / "masks" / row["file"]
        if not m or not mp.exists():
            continue
        ink = clean_ink(np.array(Image.open(mp).convert("L")) > 127)
        cs = trace(ink)
        if not cs:
            continue
        cpitch = float(m.get("cpitch", m["pitch"]))
        scale = 880.0 / max(args.pitch_floor, min(760.0, cpitch))
        sx0, sx1 = m.get("slot_x", (m["x0"], m["x1"]))
        em = to_em(cs, scale, m.get("cx0", m["x0"] - 8), m.get("cy0", m["y0"] - 8),
                   (sx0 + sx1) / 2, (m["slot"][0] + m["slot"][1]) / 2,
                   em_cx=500.0, em_cy=440.0)
        bb = base_bounds(ch)
        if bb is None:
            sx = sy = 1.0
            dx = dy = 0.0
        else:
            x0, y0, x1, y1 = contour_bounds(em)
            w, h = max(1e-3, x1 - x0), max(1e-3, y1 - y0)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            sx = min(max((BLEND * tw + (1 - BLEND) * w) / w, 0.6), 1.7)
            sy = min(max((BLEND * th + (1 - BLEND) * h) / h, 0.6), 1.7)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            dx = (bb[0] + bb[2]) / 2 - cx * sx
            dy = (bb[1] + bb[3]) / 2 - cy * sy
        nrm = dict(scale=scale, sx=sx, sy=sy, dx=dx, dy=dy,
                   origin=(m.get("cx0", m["x0"] - 8), m.get("cy0", m["y0"] - 8)),
                   slot_cx=(sx0 + sx1) / 2,
                   slot_cy=(m["slot"][0] + m["slot"][1]) / 2,
                   file=row["file"], key=row["key"], page=row["page"])

        def book_ink(ink, nrm):
            sc = nrm["scale"]; scx, scy = nrm["slot_cx"], nrm["slot_cy"]
            px0, py0 = nrm["origin"]
            a = sc * S / 1000.0 * nrm["sx"]
            bs = sc * S / 1000.0 * nrm["sy"]
            tx = (((px0 - scx) * sc + 500) * nrm["sx"] + nrm["dx"]) * S / 1000.0
            ty = (880 - nrm["dy"] - 440 * nrm["sy"]
                  - (scy - py0) * sc * nrm["sy"]) * S / 1000.0
            M = np.array([[a, 0, tx], [0, bs, ty]], np.float32)
            return cv2.warpAffine(ink, M, (S, S), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=0)

        img = Image.new("L", (S, S), 0)
        ImageDraw.Draw(img).text((0, 880 * S / 1000), ch, fill=255, font=font, anchor="ls")
        g = np.array(Image.open(wd / "masks" / row["file"]).convert("L"))
        Y.append(book_ink((g > 127).astype(np.uint8) * 255, nrm))
        X.append(np.array(img))
        chars.append(ch)
        files.append(row["file"])
        keys.append(row["key"])
    X = np.stack(X).astype(np.uint8)
    Y = np.stack(Y).astype(np.uint8)
    if SIGMA > 0:
        Y = np.stack([cv2.GaussianBlur(y.astype(np.float32), (0, 0), SIGMA).astype(np.uint8)
                      for y in Y])
    out = Path(args.out) if args.out else wd / (
        "pairs_clean_second.npz" if args.rank else
        "pairs_holdout.npz" if args.chars_file else "pairs_clean.npz")
    if args.rank and out.name == "pairs_clean.npz":
        raise SystemExit("ABORT: --rank 1 must not overwrite pairs_clean.npz "
                         "(that silently changes the clean-set baseline); "
                         "use --out pairs_clean_second.npz")
    np.savez_compressed(out, X=X, Y=Y, chars=np.array(chars),
                        files=np.array(files), keys=np.array(keys))
    print(f"clean set {len(chars)} glyphs -> {out}")
    # contact sheet for eyeballing: label on top, book glyph below
    n = min(40, len(chars))
    sheet = Image.new("L", (S * n // 8, (S + 18) * 8), 255)
    for i in range(n):
        r, c = divmod(i, 8)
        tile = Image.fromarray(Y[i]).resize((S // 2, S // 2))
        sheet.paste(tile, (c * S // 2, r * (S // 2 + 9) + 14))
        ImageDraw.Draw(sheet).text((c * S // 2 + 2, r * (S // 2 + 9) + 1),
                                   chars[i], fill=0, font=ImageFont.truetype(
                                       str(font_path), 14))
    sheet.save(wd / "clean_sheet.png")
    print("sheet ->", wd / "clean_sheet.png")


if __name__ == "__main__":
    main()
