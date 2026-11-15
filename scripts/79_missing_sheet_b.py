#!/usr/bin/env python3
"""Review sheet for the B-Q9 missing-part candidates (10 chars).

Rows come from `work-b/missing_parts_b.json`; the crop is the overlay PNG written by
`83_missing_parts_b.py` (green = projected glyph, red = the mask component the glyph does
not cover), so the reviewer sees the evidence directly.

  python3 scripts/79_missing_sheet_b.py
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_sheet as rs


def main():
    d = json.loads((ROOT / "work-b" / "missing_parts_b.json").read_text())
    rows = []
    for i, c in enumerate(d["chars"], 1):
        rows.append({
            "no": i, "line": "B", "char": c["char"],
            "crop": str(ROOT / "work-b" / "qa" / "missing_ov" / f"{c['char']}.png"),
            "meta": [f"cover={c['cover']:.2f}  area={c.get('area', '?')}px",
                     f"d_mean={c.get('dist_mean', '?')} d_max={c.get('dist_max', '?')}",
                     "missing_candidate"],
            "tag": "missing_candidate", "page": "",
        })
    out = ROOT / "work-b" / "qa" / "review-b-missing" / "sheet-{n}.png"
    pngs = rs.build_sheet(rows, str(ROOT / "build" / "GuanGeKai-B-Real.ttf"), str(out))
    rs.write_tsv(rows, str(ROOT / "work-b" / "qa" / "review-b-missing" / "ledger.tsv"))
    print(f"{len(rows)} rows -> {len(pngs)} sheet(s): {', '.join(pngs)}")


if __name__ == "__main__":
    main()
