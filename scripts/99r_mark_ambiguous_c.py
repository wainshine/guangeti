"""Mark v3d2 cells that hold >=2 characters (ambiguous) as bad.

Runs on the UNTRIMMED v3d mask (v3d2's merge-trim removed the second char).
A cell is ambiguous when a tall slot has >=2 ink clusters (each >=0.35cp,
valley >=0.08cp) and either the next slot is occupied or there are >=3 clusters.
The patch is a `bad=True` flag in a copy of cells.jsonl; 05 already knows how
to prefer clean samples and drop characters whose every sample is bad.
"""
from __future__ import annotations
import argparse, json, collections, multiprocessing as mp
from pathlib import Path
import numpy as np, cv2
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; W = ROOT / "work-c"


def runs(mask):
    ys = mask.any(1); out = []; st = None
    for i, v in enumerate(ys):
        if v and st is None: st = i
        if not v and st is not None: out.append((st, i)); st = None
    if st is not None: out.append((st, len(ys)))
    return out


def check(task):
    base_file, ink_file, cp, slot_h, next_fill = task
    m = np.array(Image.open(W / "exp/v3d/masks" / ink_file).convert("L")) > 127
    rr = runs(m)
    if len(rr) < 2: return None
    heights = [(b - a) / cp for a, b in rr]
    gaps = [(rr[i + 1][0] - rr[i][1]) / cp for i in range(len(rr) - 1)]
    if min(heights) < 0.35 or max(gaps) < 0.08: return None
    if next_fill is None or next_fill >= 0.02 or len(rr) >= 3:
        return (base_file, len(rr), round(min(heights), 2), round(max(gaps), 2))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(W / "exp/v3d3"))
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    base = collections.defaultdict(list); ink = collections.defaultdict(list)
    for l in open(W / "exp/v3d2/cells.jsonl"):
        r = json.loads(l); base[(r["key"], r["li"])].append(r)
    for l in open(W / "exp/v3d/cells.jsonl"):
        r = json.loads(l); ink[(r["key"], r["li"])].append(r)
    tasks = []
    for line, cs in base.items():
        cs = sorted(cs, key=lambda r: r["sub"]); ics = {r["sub"]: r for r in ink.get(line, [])}
        for c in cs:
            ic = ics.get(c["sub"])
            if ic is None: continue
            cp = max(1.0, float(c.get("cpitch") or c["h"]))
            slot_h = ic["y1"] - ic["y0"]
            if slot_h <= 1.10 * cp: continue
            nxt = next((x for x in cs if x["sub"] == c["sub"] + 1), None)
            tasks.append((c["file"], ic["file"], cp, slot_h, (nxt or {}).get("fill")))
    print("candidates", len(tasks), flush=True)
    bad = []
    ctx = mp.get_context("fork")
    with ctx.Pool(args.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(check, tasks, chunksize=200)):
            if r: bad.append(r)
            if i and i % 20000 == 0: print("checked", i, "bad", len(bad), flush=True)
    bad_files = {x[0] for x in bad}
    with open(out / "ambiguous.jsonl", "w") as f:
        for x in bad: f.write(json.dumps({"file": x[0], "runs": x[1], "min_h": x[2], "gap": x[3]}, ensure_ascii=False) + "\n")
    # patch cells.jsonl
    n = 0
    with open(out / "cells.jsonl", "w") as f:
        for l in open(W / "exp/v3d2/cells.jsonl"):
            r = json.loads(l)
            if r["file"] in bad_files: r["bad"] = True; r["ambiguous"] = True; n += 1
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("bad", len(bad), "patched", n, "->", out)


if __name__ == "__main__":
    main()
