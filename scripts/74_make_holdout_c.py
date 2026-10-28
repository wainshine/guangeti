"""C-line: choose the held-out pages (the clean set is by PAGE, not by character).

The A/B lines used "characters that occur exactly once" as their clean set because a
reference text could vouch for those labels.  The 大典 has no reference text, so a
single-occurrence character is simply the *least* corroborated label in the corpus —
using it as a test set measures OCR noise, not generation quality.  The defensible
alternative is to reserve whole pages: they never enter selection, pairs or training,
and the clean set is taken from their multi-witness cells.

Selection is deterministic and stratified by volume (proportional to text pages), so
every volume contributes and the split can be reproduced from this seed alone.

  python3 scripts/74_make_holdout_c.py --frac 0.06
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frac", type=float, default=0.06)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(WORK / "holdout_pages.json"))
    args = ap.parse_args()
    stats = [json.loads(l) for l in open(WORK / "page_stats.jsonl")]
    text = [s for s in stats if s["content"] == "text"]
    by_book = defaultdict(list)
    for s in text:
        by_book[s["book_idx"]].append(s["key"])
    rng_seed = str(args.seed)
    hold = []
    for b, keys in sorted(by_book.items()):
        keys = sorted(keys)
        k = max(1, int(round(len(keys) * args.frac)))
        # hash-based order: stable, independent of the file listing, no RNG state
        order = sorted(keys, key=lambda x: hashlib.sha256((rng_seed + x).encode()).hexdigest())
        hold.extend(order[:k])
    hold = sorted(hold)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(hold, ensure_ascii=False))
    meta = dict(frac=args.frac, seed=args.seed, n_pages=len(hold), n_text_pages=len(text),
                share=round(len(hold) / max(1, len(text)), 4),
                per_book={str(b): max(1, int(round(len(k) * args.frac)))
                          for b, k in sorted(by_book.items())})
    (WORK / "holdout_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
