#!/usr/bin/env python3
"""B adapter for the shared review sheet.

Purpose per owner (2026-11-14): the sheet audits **slices and real glyphs**; synthetic
glyphs only need a style check (structure comes from WenKai by construction), so the
sample is weighted 85 real / 15 synthetic.

Layers: singleton (real, one image sample) · coherent_false (reference alignment lost)
· slice_risk (faint / blobby / blurry / dewarp-failed cells) · synthetic (style only).
"""
import argparse, json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_sheet as rs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    wd = ROOT / "work-b"
    chosen = {json.loads(l)["label"]: json.loads(l) for l in open(wd / "chosen.jsonl")}
    prov = json.loads((ROOT / "release-b" / "provenance.json").read_text())
    rnd = random.Random(0)
    picks = ([("real_random", c) for c in rnd.sample(sorted(chosen), 40)]
             + [("singleton", c) for c in rnd.sample(sorted(c for c in chosen if chosen[c].get("singleton")), 25)]
             + [("coherent_false", c) for c in rnd.sample(sorted(c for c in chosen if not chosen[c].get("coherent")), 25)]
             + [("synthetic", c) for c in rnd.sample(sorted(c for c, v in prov.items() if v in ("gan", "ribbon_fb")), 10)])
    rows, R = [], str(ROOT / "build" / "GuanGeKai-B-Regular.ttf")
    for tag, c in picks:
        r, real = chosen.get(c, {}), tag != "synthetic"
        meta = ([f"p{r['page']} c{r['col']} r{r['row']}", f"ar={r.get('align_rate', 0):.2f} s={r.get('sharp', 0) or 0:.2f}", tag]
                if real else [f"layer={prov.get(c, '-')}", f"U+{ord(c):04X}", tag])
        rows.append({"no": len(rows) + 1, "line": "B", "char": c, "tag": tag, "meta": meta, "page": r.get("page", ""),
                     "crop": str(wd / "cells" / r["file"]) if real else None, "glyph_font": None if real else R})
    pngs = rs.build_sheet(rows, str(ROOT / "build" / "GuanGeKai-B-Real.ttf"), str(ROOT / "work-b" / "qa" / "review-b" / "sheet-{n}.png"))
    rs.write_tsv(rows, str(ROOT / "work-b" / "qa" / "review-b" / "ledger.tsv"))
    print(f"{len(rows)} rows -> {len(pngs)} sheet(s): {', '.join(pngs)}")


if __name__ == "__main__":
    main()
