"""List every OCR-vs-reference disagreement so the variant table can be curated.

Writes work-b/ref_conflicts.json ({ocr|ref: count}) and prints the most frequent pairs.
A pair listed in data/reference-b/variants.json is treated as a legitimate manuscript
variant (label kept from the scan); everything else is treated as an OCR misread
(label taken from the reference).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--top", type=int, default=120)
    args = ap.parse_args()
    wd = Path(args.work)
    c = Counter()
    n = 0
    for line in open(wd / "labeled.jsonl"):
        r = json.loads(line)
        o, ref = r.get("ocr", ""), r.get("ref", "")
        n += 1
        if o and ref and o != ref and not r.get("low_align"):
            c[f"{o}|{ref}"] += 1
    tot = sum(c.values())
    print(f"cells {n}; conflicting cells {tot} ({tot/max(1,n):.2%}); distinct pairs {len(c)}")
    (wd / "ref_conflicts.json").write_text(json.dumps(c.most_common(), ensure_ascii=False, indent=0))
    for k, v in c.most_common(args.top):
        print(f"{v:6d}  {k}")
    print("->", wd / "ref_conflicts.json")


if __name__ == "__main__":
    main()
