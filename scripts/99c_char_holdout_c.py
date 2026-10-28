"""Pick a character-level holdout for the C line (W0.2).

The page holdout measures *style consistency* (the character was trained on other
pages); it cannot measure generalisation, because 98% of its characters are ones the
model has seen.  This script reserves N characters outright: they are removed from
the training pairs (`08_make_pairs.py --exclude-chars`) and evaluated on their own
chosen samples.

  python3 scripts/99c_char_holdout_c.py --work work-c-v2 --n 300 --seed 42
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-c"))
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    wd = Path(args.work)
    rows = [json.loads(l) for l in open(wd / "chosen.jsonl")]
    labels = sorted({r["label"] for r in rows})
    rng = random.Random(args.seed)
    pick = sorted(rng.sample(labels, min(args.n, len(labels))))
    out = Path(args.out) if args.out else wd / "char_holdout.json"
    out.write_text(json.dumps(pick, ensure_ascii=False))
    print(f"holdout {len(pick)} / {len(labels)} chars -> {out}")
    print("".join(pick[:40]) + " ...")


if __name__ == "__main__":
    main()
