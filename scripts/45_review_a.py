"""A-line adapter for the shared review sheet (data preparation only).

Picks characters by layer (real / gan / ribbon), resolves each to its source cell crop,
and hands normalised rows to scripts/review_sheet.py.  No drawing code lives here.

Usage:
    python3 scripts/45_review_a.py --n 40                 # 40 chars, stratified by layer
    python3 scripts/45_review_a.py --chars work/sample.txt --out work/qa/review-a
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_sheet as rs  # noqa: E402

DEFAULT_FONT = ROOT / "build" / "GuanGeKai-Regular.ttf"


def cell_map() -> dict[str, str]:
    out = {}
    for line in open(ROOT / "work" / "labeled.jsonl"):
        r = json.loads(line)
        out.setdefault(r["label"], r["file"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--chars", default="")
    ap.add_argument("--out", default=str(ROOT / "work" / "qa" / "review-a"))
    ap.add_argument("--font", default=str(DEFAULT_FONT))
    ap.add_argument("--cols", type=int, default=10)
    ap.add_argument("--per-page", type=int, default=100)
    args = ap.parse_args()

    prov = json.load(open(ROOT / "release" / "provenance.json"))
    cells = cell_map()

    if args.chars:
        chars = [l.strip() for l in open(args.chars) if l.strip()]
    else:
        by_layer: dict[str, list[str]] = {"real": [], "gan": [], "ribbon": []}
        for ch, layer in prov.items():
            if layer == "punct" or ch not in cells:
                continue
            key = "ribbon" if layer.startswith("ribbon") else ("real" if layer == "real" else "gan")
            by_layer[key].append(ch)
        per = max(1, args.n // 3)
        chars = []
        for k in ("real", "gan", "ribbon"):
            chars += sorted(by_layer[k])[:per]
        chars = sorted(set(chars))[:args.n]

    rows = []
    for i, ch in enumerate(chars, 1):
        f = cells.get(ch)
        layer = prov.get(ch, "?")
        rows.append({
            "no": i, "line": "A", "char": ch,
            "crop": f"work/cells/{f}" if f else None,
            "glyph_font": args.font,
            "meta": [f"p{f.split('_')[0][1:]}" if f else "-", layer,
                     "source cell" if f else "no crop"],
            "tag": layer,
        })

    out_dir = Path(args.out)
    pngs = rs.build_sheet(rows, args.font, str(out_dir / "sheet-{n}.png"),
                          cols=args.cols, per_page=args.per_page)
    tsv = rs.write_tsv(rows, str(out_dir / "ledger.tsv"))
    print(f"{len(rows)} rows | {len(pngs)} sheet(s) | {tsv}")
    for p in pngs:
        print(" ", p)


if __name__ == "__main__":
    main()
