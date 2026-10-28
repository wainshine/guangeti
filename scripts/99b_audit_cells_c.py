"""Audit C-line cell cuts: size outliers, merged cells, stray fragments, tiny cells.

User-reported failure modes (2026-10-28):
  * two-column small text: a cell can hold an empty half (slot centred, glyph on one side);
  * very small glyphs are kept and later upscaled (blurry);
  * two small characters merged into one cell;
  * a neighbour stroke / 句读 fragment carried into the cell.

This script does not re-cut; it produces the audit list and a contact sheet so the
segmentation fix (W1.5) can be measured before/after.

  python3 scripts/99b_audit_cells_c.py --rows work-c/chosen.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def analyse(mask: np.ndarray, cp: float):
    h, w = mask.shape
    ys = mask.any(1)
    runs = []
    s = None
    for i, v in enumerate(ys):
        if v and s is None:
            s = i
        if not v and s is not None:
            runs.append((s, i))
            s = None
    if s is not None:
        runs.append((s, len(ys)))
    merged_y = False
    if len(runs) >= 2 and h > 1.25 * cp:
        a = runs[0]
        b = runs[-1]
        merged_y = ((a[1] - a[0]) > 0.25 * h and (b[1] - b[0]) > 0.25 * h
                    and (b[0] - a[1]) > 0.08 * h)
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    areas = sorted((int(st[i, 4]) for i in range(1, n)), reverse=True)
    frag = bool(len(areas) >= 2 and areas[0] >= 0.5 * mask.sum()
                and 20 <= areas[1] <= 0.03 * mask.sum())
    return merged_y, frag, len(runs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(ROOT / "work-c" / "chosen.jsonl"))
    ap.add_argument("--work", default=str(ROOT / "work-c"))
    ap.add_argument("--out", default=str(ROOT / "work-c" / "cell_audit.json"))
    ap.add_argument("--sheet", default=str(ROOT / "work-c" / "cell_audit.png"))
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(args.rows)]
    flagged = []
    for r in rows:
        cp = max(1.0, float(r["cpitch"]))
        w, h = r["w"], r["h"]
        mask = np.array(Image.open(Path(args.work) / "masks" / r["file"]).convert("L")) > 127
        merged, frag, runs = analyse(mask, cp)
        sc = (r["slot_x"][0] + r["slot_x"][1]) / 2.0
        bc = (r["x0"] + r["x1"]) / 2.0
        off = abs(bc - sc) / max(1.0, max(w, h))
        flags = []
        if w > 1.15 * cp or h > 1.15 * cp:
            flags.append("large")
        if w < 0.30 * cp or h < 0.30 * cp:
            flags.append("tiny")
        if merged:
            flags.append("merged_y")
        if frag:
            flags.append("fragment")
        if off > 0.18:
            flags.append("off_center")
        if flags:
            flagged.append(dict(char=r["label"], file=r["file"], w=w, h=h,
                                cp=round(cp, 1), wcp=round(w / cp, 2),
                                hcp=round(h / cp, 2), off=round(off, 3), flags=flags))
    n_off = sum(1 for r in rows
                if abs(((r["x0"] + r["x1"]) / 2.0
                        - (r["slot_x"][0] + r["slot_x"][1]) / 2.0))
                / max(1.0, max(r["w"], r["h"])) > 0.18)
    print(f"audited {len(rows)}; flagged {len(flagged)}; off_center(>0.18) {n_off}")
    from collections import Counter
    c = Counter(f for x in flagged for f in x["flags"])
    print(dict(c))
    Path(args.out).write_text(json.dumps(flagged, ensure_ascii=False, indent=1))
    print(f"-> {args.out}")

    items = flagged[:80]
    cols, cell = 10, 100
    rows_n = max(1, (len(items) + cols - 1) // cols)
    sheet = Image.new("L", (cols * 2 * cell, rows_n * cell), 255)
    d = ImageDraw.Draw(sheet)
    for k, x in enumerate(items):
        row, col = divmod(k, cols)
        im = Image.open(Path(args.work) / "cells" / x["file"]).convert("L")
        im.thumbnail((2 * cell - 6, cell - 6))
        sheet.paste(im, (col * 2 * cell + 2, row * cell + 2))
        d.text((col * 2 * cell + 2, row * cell + cell - 12),
               x["char"] + "/" + ",".join(x["flags"]), fill=0)
    sheet.save(args.sheet)
    print(f"-> {args.sheet}")


if __name__ == "__main__":
    main()
