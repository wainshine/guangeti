"""B-line: add high-confidence *singletons* to the chosen set.

`05_select.py --min-samples 2` drops characters that occur only once because a single
sample cannot be cross-validated (四書 lost 617 characters that way).  This copy has two
independent witnesses per cell — the OCR transcript and the aligned reference text — so
a singleton is admitted only when they agree, the page's alignment is coherent, and the
page is not in the low-align set.  Everything else stays synthetic.

  python3 scripts/58_add_singletons_b.py --work work-b
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--out", default="", help="default: <work>/chosen_plus.jsonl")
    args = ap.parse_args()
    wd = Path(args.work)

    rows = [json.loads(l) for l in open(wd / "labeled.jsonl")]
    chosen = [json.loads(l) for l in open(wd / "chosen.jsonl")]
    have = {r["label"] for r in chosen}
    cnt = collections.Counter(r["label"] for r in rows if r.get("label"))
    singles = [r for r in rows if r.get("label") and cnt[r["label"]] == 1]

    def confident(r):
        return (r.get("label_src") == "ocr" and r.get("ocr") and r.get("ref")
                and r["ocr"] == r["ref"] and r.get("coherent") and not r.get("low_align"))

    add = [r for r in singles if confident(r) and r["label"] not in have]
    for r in add:
        r["n_samples"] = 1
        r["singleton"] = True
        r["medoid_dist"] = 0.0
    print(f"singletons {len(singles)}; admitted {len(add)}; "
          f"chosen {len(chosen)} -> {len(chosen)+len(add)}")
    print("rejected (no second witness):",
          len(singles) - len(add), "sample:",
          [(r["label"], r.get("label_src"), r["ocr"], r.get("ref"))
           for r in singles if not confident(r)][:10])

    out = Path(args.out) if args.out else wd / "chosen_plus.jsonl"
    with open(out, "w") as f:
        for r in chosen:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        for r in add:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("->", out, sum(1 for _ in open(out)), "rows")


if __name__ == "__main__":
    main()
