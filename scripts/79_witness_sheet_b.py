#!/usr/bin/env python3
"""Review sheet for the second-witness disagreements (B-Q4).

Each cell: product glyph (the stored label) + WenKai reference + the book crop; the meta
line shows what PP-OCRv5 read, so the reviewer can say "the crop really is the v5 char".
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_sheet as rs


def main():
    wd = ROOT / "work-b"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/hard_disagree.json")
    picks = json.loads(path.read_text())
    rows = []
    for o in picks:
        rows.append({"no": len(rows) + 1, "line": "B", "char": o["char"],
                     "crop": str(wd / "cells" / o["file"]),
                     "meta": [f"v5={o['v5']} {o['score']:.2f}",
                              f"coherent={o['coherent']} ar={o['ar']:.2f}",
                              "witness_disagree"],
                     "tag": "witness_disagree"})
    out = ROOT / "work-b" / "qa" / "review-b-witness" / "sheet-{n}.png"
    pngs = rs.build_sheet(rows, str(ROOT / "build" / "GuanGeKai-B-Real.ttf"), str(out))
    rs.write_tsv(rows, str(ROOT / "work-b" / "qa" / "review-b-witness" / "ledger.tsv"))
    print(f"{len(rows)} rows -> {len(pngs)} sheet(s): {', '.join(pngs)}")


if __name__ == "__main__":
    main()
