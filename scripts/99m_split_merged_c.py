"""20-page prototype: split merged cells using the UNTRIMMED v3d mask.

Outputs only a patch report and split crops (no full cells.jsonl rewrite yet).
A cell is split only when the v3d mask has exactly 2 y-clusters, each >=0.35cp,
valley >=0.08cp, slot_h >1.1cp, and the next base slot is free (fill<0.02).
"""
from __future__ import annotations
import argparse, json, collections
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]; W = ROOT / "work-c"
_F = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 128)
_C = {}

def wk(ch):
    if ch not in _C:
        im = Image.new("L", (128, 128), 0)
        ImageDraw.Draw(im).text((0, 112), ch, fill=255, font=_F, anchor="ls")
        _C[ch] = np.array(im) > 127
    return _C[ch]

def dice(a, b):
    return 2 * (a & b).sum() / max(1, a.sum() + b.sum())


def runs(mask):
    ys = mask.any(1); out = []; st = None
    for i, v in enumerate(ys):
        if v and st is None: st = i
        if not v and st is not None: out.append((st, i)); st = None
    if st is not None: out.append((st, len(ys)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(W / "exp/v3d2"))
    ap.add_argument("--ink", default=str(W / "exp/v3d"))
    ap.add_argument("--keys", default=str(W / "exp/keys20.txt"))
    ap.add_argument("--out", default=str(W / "exp/v3d3_split20"))
    args = ap.parse_args()
    keys = set(open(args.keys).read().strip().split(","))
    out = Path(args.out); (out / "masks").mkdir(parents=True, exist_ok=True); (out / "cells").mkdir(exist_ok=True)
    def load(wd):
        cells = collections.defaultdict(list)
        for l in open(Path(wd) / "cells.jsonl"):
            r = json.loads(l)
            if r["key"] in keys: cells[(r["key"], r["li"])].append(r)
        return cells
    base = load(args.base); ink = load(args.ink)
    report = []; over = []
    for line, bcs in base.items():
        bcs = sorted(bcs, key=lambda r: r["sub"]); ics = {r["sub"]: r for r in ink.get(line, [])}
        for c in bcs:
            ic = ics.get(c["sub"])
            if ic is None: continue
            cp = max(1.0, float(c.get("cpitch") or c["h"]))
            slot_h = ic["y1"] - ic["y0"]
            if slot_h <= 1.10 * cp: continue
            m = np.array(Image.open(Path(args.ink) / "masks" / ic["file"]).convert("L")) > 127
            rr = runs(m)
            if len(rr) != 2: 
                if len(rr) > 2: over.append({"key": c["key"], "li": c["li"], "sub": c["sub"], "runs": len(rr)})
                continue
            heights = [(b - a) / cp for a, b in rr]
            gap = (rr[1][0] - rr[0][1]) / cp
            if min(heights) < 0.35 or gap < 0.08: continue
            nxt = next((x for x in bcs if x["sub"] == c["sub"] + 1), None)
            if nxt is None or nxt.get("fill", 1) >= 0.02:
                # next slot is occupied: the second cluster is a duplicate of the
                # neighbour, so TRIM to the main cluster instead of splitting
                # (splitting would overwrite a non-empty cell and shift labels).
                # choose the cluster that matches the cell label (the larger one may
                # be the neighbour, which is exactly how trim went wrong).
                best = None
                for run in rr:
                    seg0 = np.zeros_like(m); seg0[run[0]:run[1]] = m[run[0]:run[1]]
                    ys0, xs0 = np.nonzero(seg0)
                    if not len(ys0): continue
                    sm0 = seg0[ys0.min():ys0.max() + 1, xs0.min():xs0.max() + 1]
                    sm0 = cv2.resize(sm0.astype(np.uint8), (128, 128), interpolation=cv2.INTER_NEAREST) > 0
                    ch = c.get("label") or ""
                    d = float(dice(sm0, wk(ch))) if ch else 0.0
                    if best is None or d > best[0]: best = (d, run, sm0)
                if best is None: continue
                main = best[1]
                seg = np.zeros_like(m); seg[main[0]:main[1]] = m[main[0]:main[1]]
                ys, xs = np.nonzero(seg)
                if not len(ys): continue
                seg = seg[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                name = f"{c['key']}_c{c['col']:02d}_l{c['li']:02d}_s{c['sub']:03d}.png"
                Image.fromarray(seg.astype(np.uint8) * 255).save(out / "masks" / name)
                g = Image.open(Path(args.ink) / "cells" / ic["file"]).convert("L")
                gm = np.array(g); sm = np.array(Image.open(out / "masks" / name).convert("L")) > 127
                crop = np.full_like(sm, 255, dtype=np.uint8); h, w = sm.shape
                gx0 = max(0, xs.min()); gy0 = max(0, ys.min())
                gx1 = min(gm.shape[1], gx0 + w); gy1 = min(gm.shape[0], gy0 + h)
                crop[:gy1 - gy0, :gx1 - gx0] = gm[gy0:gy1, gx0:gx1]
                Image.fromarray(crop).save(out / "cells" / name)
                report.append({"key": c["key"], "li": c["li"], "sub": c["sub"], "file": name,
                               "label": c.get("label", ""), "from": c["file"], "part": "trim",
                               "h_run": round(max(heights), 2), "gap": round(gap, 2),
                               "label_dice": round(best[0], 3)})
                continue
            # split at the gap midpoint
            mid = (rr[0][1] + rr[1][0]) // 2
            for j, (a, b) in enumerate(((rr[0][0], mid), (mid, rr[1][1]))):
                seg = np.zeros_like(m); seg[a:b] = m[a:b]
                ys, xs = np.nonzero(seg)
                if not len(ys): continue
                seg = seg[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                lab = (c.get("label") if j == 0 else (nxt.get("label") if nxt else "")) or ""
                name = f"{c['key']}_c{c['col']:02d}_l{c['li']:02d}_s{c['sub'] + j:03d}.png"
                Image.fromarray(seg.astype(np.uint8) * 255).save(out / "masks" / name)
                g = Image.open(Path(args.ink) / "cells" / ic["file"]).convert("L")
                gm = np.array(g); sm = np.array(Image.open(out / "masks" / name).convert("L")) > 127
                # crop the same bbox from the gray cell; pad to the segment size
                x0 = xs.min(); y0 = ys.min()
                crop = np.full_like(sm, 255, dtype=np.uint8)
                h, w = sm.shape
                gx0 = max(0, x0); gy0 = max(0, y0)
                gx1 = min(gm.shape[1], gx0 + w); gy1 = min(gm.shape[0], gy0 + h)
                crop[:gy1 - gy0, :gx1 - gx0] = gm[gy0:gy1, gx0:gx1]
                Image.fromarray(crop).save(out / "cells" / name)
                report.append({"key": c["key"], "li": c["li"], "sub": c["sub"] + j, "file": name,
                               "label": lab, "from": c["file"], "part": j,
                               "h_run": round((b - a) / cp, 2), "gap": round(gap, 2)})
    json.dump({"split_cells": report, "overflow": over, "n_split": len(report),
               "n_lines": len({(r["key"], r["li"]) for r in report})},
              open(out / "split_report.json", "w"), ensure_ascii=False, indent=1)
    print("split", len(report), "overflow", len(over), "lines", len({(r["key"], r["li"]) for r in report}))


if __name__ == "__main__":
    main()
