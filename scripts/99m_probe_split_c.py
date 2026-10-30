"""Probe v3d2 merged cells using the UNTRIMMED v3d mask (audit P1 fix).

v3d2's merge-trim removed the second character from the mask, so a split based on
v3d2 masks can never see it.  This probe reads the same (key,li,sub) from v3d,
checks whether the slot is tall and has >=2 ink clusters, and reports whether the
split is feasible (cluster heights, valley, free adjacent slots).
"""
from __future__ import annotations
import argparse, json, collections, statistics
from pathlib import Path
import numpy as np, cv2
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "work-c"


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
    ap.add_argument("--keys", default=str(ROOT / "work-c/exp/keys20.txt"))
    ap.add_argument("--out", default=str(W / "exp/v3d3_split_probe.json"))
    args = ap.parse_args()
    keys = set(open(args.keys).read().strip().split(","))
    def load(wd):
        cells = collections.defaultdict(list)
        for l in open(Path(wd) / "cells.jsonl"):
            r = json.loads(l)
            if r["key"] in keys:
                cells[(r["key"], r["li"])].append(r)
        return cells
    base = load(args.base); ink = load(args.ink)
    stats = collections.Counter(); rows = []
    for line, bcs in base.items():
        bcs = sorted(bcs, key=lambda r: r["sub"]); ics = {r["sub"]: r for r in ink.get(line, [])}
        for c in bcs:
            ic = ics.get(c["sub"])
            if ic is None: stats["no_ink_cell"] += 1; continue
            cp = max(1.0, float(c.get("cpitch") or c["h"]))
            slot_h = ic["y1"] - ic["y0"]
            if slot_h <= 1.10 * cp: continue
            m = np.array(Image.open(Path(args.ink) / "masks" / ic["file"]).convert("L")) > 127
            rr = runs(m)
            if len(rr) < 2: stats["trim_hides_second"] += 1; continue
            stats["candidate"] += 1
            heights = [(b - a) / cp for a, b in rr]
            gaps = [(rr[i + 1][0] - rr[i][1]) / cp for i in range(len(rr) - 1)]
            if min(heights) < 0.35: stats["cluster_too_small"] += 1
            if max(gaps) < 0.08: stats["valley_too_narrow"] += 1
            # free adjacent slots (sub+1 .. sub+K-1) with no/empty cells
            free = []
            for j in range(1, len(rr)):
                nxt = next((x for x in bcs if x["sub"] == c["sub"] + j), None)
                free.append(nxt is None or nxt.get("fill", 1) < 0.02)
            rows.append({"key": c["key"], "li": c["li"], "sub": c["sub"], "file": c["file"],
                         "cpitch": cp, "slot_h": slot_h, "runs": len(rr),
                         "heights": [round(x, 2) for x in heights],
                         "gaps": [round(x, 2) for x in gaps],
                         "free_adjacent": free, "label": c.get("label")})
    out = {"keys": len(keys), "stats": dict(stats), "rows": rows}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(dict(stats), ensure_ascii=False, indent=1))
    print("rows", len(rows), "->", args.out)


if __name__ == "__main__":
    main()
