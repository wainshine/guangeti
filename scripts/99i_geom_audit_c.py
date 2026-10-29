"""P0-0.6 geometric self-check: per-line width consistency (no OCR).

Flags lines whose cell-width sequence cannot be a normal grid: high CV, a wide cell
followed by a narrow one (merged), a narrow cell between normal ones (broken), or a
cell whose height approaches the line pitch (the 一 case: previous glyph + bottom bar).
"""
from __future__ import annotations
import json, collections, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"


def main():
    by = collections.defaultdict(list)
    for l in open(WORK / "cells.jsonl"):
        r = json.loads(l)
        by[(r["key"], r["li"])].append(r)
    rows = 0
    cv_bad = merged_bad = broken_bad = tall_bad = 0
    suspect = []
    total_cells = 0
    for (key, li), cs in by.items():
        cs = sorted(cs, key=lambda r: r["sub"])
        if len(cs) < 3:
            continue
        rows += 1
        total_cells += len(cs)
        w = [max(1.0, c["w"]) for c in cs]
        h = [max(1.0, c["h"]) for c in cs]
        med = statistics.median(w)
        mean = statistics.mean(w)
        cv = statistics.pstdev(w) / mean if mean else 0.0
        merged = any(w[i] > 1.4 * med and i + 1 < len(w) and w[i + 1] < 0.6 * med
                     for i in range(len(w) - 1))
        broken = any(w[i] < 0.6 * med and i + 1 < len(w) and w[i + 1] < 0.8 * med
                     for i in range(len(w) - 1))
        cp = statistics.median([max(1.0, c.get("cpitch", 1)) for c in cs])
        tall = any(hh > 0.85 * cp for hh in h)
        if cv > 0.35: cv_bad += 1
        if merged: merged_bad += 1
        if broken: broken_bad += 1
        if tall: tall_bad += 1
        if cv > 0.35 or merged or broken:
            suspect.append({"key": key, "li": li, "n": len(cs), "cv": round(cv, 3),
                            "med_w": round(med, 1), "cpitch": round(cp, 1),
                            "merged": merged, "broken": broken, "tall": tall})
    out = {"rows": rows, "cells": total_cells,
           "cv_gt_0.35": cv_bad, "cv_pct": round(100 * cv_bad / rows, 1),
           "merged": merged_bad, "merged_pct": round(100 * merged_bad / rows, 1),
           "broken": broken_bad, "broken_pct": round(100 * broken_bad / rows, 1),
           "tall": tall_bad, "tall_pct": round(100 * tall_bad / rows, 1),
           "tall_note": "h in cells is slot height, not ink bbox; NOT diagnostic, do not use",
           "suspect_rows": len(suspect),
           "suspect_sample": suspect[:50]}
    (WORK / "geom_audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "suspect_sample"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
