"""Apply the v1.0.1 simplified/traditional label fix to `work-c/labeled.jsonl`.

The 10 mismatches (书/习/长/价/礼/类/庄 dropped, 个→個 / 亘→亙 / 坛→罎 relabelled)
were fixed by hand-editing `chosen.jsonl`.  A clean rebuild runs `05_select.py` again
and would re-introduce them, so the fix lives here and is applied between
`94_label_c.py` and `05_select.py` (see docs/DATA-C.md step 4.5).

Idempotent: running it twice changes nothing.

  python3 scripts/96_fix_labels_c.py --work work-c
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-c"))
    ap.add_argument("--fix", default="")
    args = ap.parse_args()
    wd = Path(args.work)
    fix_p = Path(args.fix) if args.fix else wd / "label_fix_final.json"
    fix = json.loads(fix_p.read_text())
    relabel = fix.get("relabel", {})
    drop = set(fix.get("drop", []))
    lab_p = wd / "labeled.jsonl"
    bak = wd / "labeled.jsonl.bak_pre_fix"
    if not bak.exists():
        shutil.copy2(lab_p, bak)
        print(f"backup -> {bak}")

    n_rel = n_drop = 0
    tmp = lab_p.with_suffix(".jsonl.tmp")
    with open(lab_p) as src, open(tmp, "w") as dst:
        for line in src:
            r = json.loads(line)
            lab = r.get("label", "")
            if lab in relabel:
                r["label"] = relabel[lab]
                r["label_src"] = "relabeled_mismatch"
                n_rel += 1
            elif lab in drop:
                r["label"] = ""
                r["label_src"] = "dropped_mismatch"
                n_drop += 1
            dst.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(lab_p)
    print(f"relabelled {n_rel} cells, dropped {n_drop} cells "
          f"({len(relabel)} relabel rules, {len(drop)} drop labels)")
    if n_rel == 0 and n_drop == 0:
        print("nothing to do (already fixed)")


if __name__ == "__main__":
    main()
