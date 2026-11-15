#!/usr/bin/env python3
"""B-Q9: missing-part scan with exact registration (glyph -> cell pixels).

The two cheap proxies both failed: connected-component counts change because `--close 7`
merges separate strokes, and bbox normalisation misaligns (the 亻 radical lands elsewhere).
So this script inverts the build's own transform chain instead of guessing:

    cell px -> to_em -> transform(sx, sy, dx, dy) -> font units

inverted per character, the shipped contours are projected back onto the exact cell mask,
and every mask component (area >= 1% of the cell ink, min side >= 8 px) must be covered by
the glyph (coverage >= --min-cover, after a small dilation for tracing tolerance).

  python3 scripts/83_missing_parts_b.py --n 0 --out work-b/missing_parts_b.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PAD = 6
EM_CX, EM_CY = 500.0, 440.0


def contour_polygon(c: dict) -> np.ndarray:
    """Start point + every segment endpoint, in font units (curves are approximated)."""
    pts = [c["start"]]
    for s in c["segs"]:
        if s[0] == "L":
            pts.append((s[1], s[2]))
        else:
            pts.append((s[5], s[6]))
    return np.asarray(pts, dtype=np.float32)


def to_cell(pts, scale, page_x0, page_y0, slot_cx, slot_cy, sx, sy, dx, dy, em_cx, em_cy):
    """Invert transform() then to_em()."""
    ex = (pts[:, 0] - dx) / sx
    ey = (pts[:, 1] - dy) / sy
    px = (ex - em_cx) / scale + slot_cx - page_x0
    py = slot_cy - (ey - em_cy) / scale - page_y0
    return np.stack([px, py], axis=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--n", type=int, default=0, help="0 = all")
    ap.add_argument("--min-cover", type=float, default=0.45)
    ap.add_argument("--dilate", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "work-b" / "missing_parts_b.json"))
    ap.add_argument("--dump", default="", help="dir for overlay PNGs of flagged chars")
    args = ap.parse_args()

    wd = Path(args.work)
    cells = {json.loads(l)["file"]: json.loads(l) for l in open(wd / "cells.jsonl")}
    norm = json.loads((wd / "norm.json").read_text())
    rows = [json.loads(l) for l in open(wd / "chosen.jsonl")]
    by_char = {r["label"]: r for r in rows}
    glyphs = {}
    for line in open(wd / "real_contours.jsonl"):
        g = json.loads(line)
        glyphs[g["char"]] = g["contours"]

    chars = sorted(glyphs)
    if args.n:
        chars = chars[: args.n]
    flagged, checked = [], 0
    dump = Path(args.dump) if args.dump else None
    if dump:
        dump.mkdir(parents=True, exist_ok=True)

    for ch in chars:
        r, n = by_char.get(ch), norm.get(ch)
        m = cells.get(r["file"]) if r else None
        if not (r and n and m):
            continue
        mp = wd / "masks" / r["file"]
        if not mp.exists():
            continue
        mask = np.array(Image.open(mp).convert("L")) > 127
        h, w = mask.shape
        scale = 880.0 / max(100.0, m["pitch"])
        page_x0, page_y0 = m["x0"] - PAD, m["y0"] - PAD
        slot_cx = (m["x0"] + m["x1"]) / 2.0
        slot_cy = (m["slot"][0] + m["slot"][1]) / 2.0
        canvas = np.zeros((h, w), np.uint8)
        for c in glyphs[ch]:
            pts = to_cell(contour_polygon(c), scale, page_x0, page_y0, slot_cx, slot_cy,
                          n["sx"], n["sy"], n["dx"], n["dy"], EM_CX, EM_CY)
            if len(pts) < 3:
                continue
            layer = np.zeros((h, w), np.uint8)
            cv2.fillPoly(layer, [np.round(pts).astype(np.int32)], 1)
            canvas ^= layer            # holes are opposite-orientation contours
        glyph = canvas > 0
        grown = cv2.dilate(glyph.astype(np.uint8), np.ones((args.dilate, args.dilate), np.uint8)) > 0
        nlab, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        ink = int(mask.sum())
        worst, worst_comp = 1.0, None
        for i in range(1, nlab):
            if st[i, cv2.CC_STAT_AREA] < 0.01 * ink or min(st[i, cv2.CC_STAT_WIDTH],
                                                           st[i, cv2.CC_STAT_HEIGHT]) < 8:
                continue
            sel = lab == i
            cover = float((sel & grown).sum()) / max(1, int(sel.sum()))
            if cover < worst:
                worst, worst_comp = cover, i
        checked += 1
        if worst < args.min_cover:
            rec = {"char": ch, "cover": round(worst, 3), "file": r["file"]}
            if worst_comp is not None:
                sel = lab == worst_comp
                dist = cv2.distanceTransform((~glyph).astype(np.uint8), cv2.DIST_L2, 3)
                rec.update({"area": int(st[worst_comp, cv2.CC_STAT_AREA]),
                            "dist_mean": round(float(dist[sel].mean()), 1),
                            "dist_max": round(float(dist[sel].max()), 1)})
            flagged.append(rec)
            if dump is not None:
                # 灰度可读：背景白 / 字形中灰 / 可疑部件黑 / 部件外画黑框（放大到整字看，
                # 不要只裁那一小块——那样看不出是哪个字，也判断不了是不是笔画）
                ov = np.full((h, w, 3), 255, np.uint8)
                ov[glyph] = (185, 185, 185)
                if worst_comp is not None:
                    sel = lab == worst_comp
                    ov[sel] = (0, 0, 0)
                    ys_, xs_ = np.nonzero(sel)
                    m_ = 6
                    cv2.rectangle(ov, (max(0, xs_.min() - m_), max(0, ys_.min() - m_)),
                                  (min(w - 1, xs_.max() + m_), min(h - 1, ys_.max() + m_)),
                                  (0, 0, 0), 1)
                Image.fromarray(ov.astype(np.uint8)).save(dump / f"{ch}.png")
                if worst_comp is not None:
                    x_, y_, w_, h_ = (st[worst_comp, cv2.CC_STAT_LEFT], st[worst_comp, cv2.CC_STAT_TOP],
                                      st[worst_comp, cv2.CC_STAT_WIDTH], st[worst_comp, cv2.CC_STAT_HEIGHT])
                    pad = max(30, 2 * max(w_, h_))
                    x0, y0 = max(0, x_ - pad), max(0, y_ - pad)
                    x1, y1 = min(ov.shape[1], x_ + w_ + pad), min(ov.shape[0], y_ + h_ + pad)
                    z = Image.fromarray(ov[y0:y1, x0:x1].astype(np.uint8))
                    z = z.resize((z.width * 4, z.height * 4), Image.NEAREST)
                    z.save(dump / f"{ch}_zoom.png")

    res = {"checked": checked, "min_cover": args.min_cover, "dilate": args.dilate,
           "flagged": len(flagged), "chars": flagged}
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"checked {checked} real glyphs; flagged {len(flagged)} "
          f"(coverage < {args.min_cover})")
    if flagged:
        print("examples:", [(f["char"], f["cover"]) for f in flagged[:10]])
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
