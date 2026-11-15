#!/usr/bin/env python3
"""Review sheet for the 貝-family real glyphs: source cell vs shipped glyph."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_sheet as rs


def main():
    wd = ROOT / "work-b"
    rows_by = {json.loads(l)["label"]: json.loads(l) for l in open(wd / "chosen.jsonl")}
    chars = [l.strip() for l in open("/tmp/bei_chars.txt") if l.strip()]
    rows = []
    for ch in chars:
        r = rows_by.get(ch)
        if not r:
            continue
        rows.append({"no": len(rows) + 1, "line": "B", "char": ch,
                     "crop": str(wd / "cells" / r["file"]),
                     "meta": [f"p{r['page']} c{r['col']} r{r['row']}", "beifamily", ch],
                     "tag": "beifamily", "page": r.get("page", "")})
    out = ROOT / "work-b" / "qa" / "review-b-bei" / "sheet-{n}.png"
    pngs = rs.build_sheet(rows, str(ROOT / "build" / "GuanGeKai-B-Real.ttf"), str(out))
    rs.write_tsv(rows, str(ROOT / "work-b" / "qa" / "review-b-bei" / "ledger.tsv"))
    print(f"{len(rows)} rows -> {len(pngs)} sheet(s): {', '.join(pngs)}")


if __name__ == "__main__":
    main()
