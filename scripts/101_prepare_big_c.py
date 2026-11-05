"""C-line 大字实验: filter the 头字 (large head-character) cells into work-c-big/.

Reads work-c/labeled.jsonl once (streaming) and keeps rows that are genuine
大字字头 cells.  The raw `big` flag is necessary but not sufficient: OCR merges
whole 小字 columns into one wide line box, which also sets big=true (84% of all
big rows have n_line>=24 and are ordinary small text).  A genuine 字头 line is
one (at most a few) chars tall AND its per-char advance cpitch is a large
fraction of the 朱丝栏 column pitch:

    big && 1 <= n_line <= 3 && cpitch >= max(0.6 * pitch, --min-cpitch)

Rows are written unchanged to work-c-big/labeled.jsonl; work-c-big/cells.jsonl
is the same row set with the four OCR-witness fields stripped (matching the
A/B cells.jsonl schema).  cells/ and masks/ are symlinked, not copied (~14 GB).
Pages holding big cells are sampled 10% (fixed seed) into holdout_pages.json —
the same page-level holdout convention as the C line (05_select matches r["key"]).

    python3 scripts/101_prepare_big_c.py
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "work-c" / "labeled.jsonl"
OUT = ROOT / "work-c-big"

WITNESS_FIELDS = ("v6_char", "v5_char", "agree_ab", "label_src")
# 标签见证未通过或不在基本区的行：与 C 线的丢弃口径一致（冲突约 9% 已在上游标记）
BAD_SOURCES = {"conflict", "dropped_mismatch", "relabeled_mismatch", "out_of_block"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(SRC))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--min-n-line", type=int, default=3,
                    help="keep big lines with at most this many OCR chars")
    ap.add_argument("--pitch-frac", type=float, default=0.6,
                    help="cpitch must reach this fraction of the column pitch")
    ap.add_argument("--min-cpitch", type=float, default=160.0,
                    help="absolute floor for cpitch (narrow-column pages, e.g. p00_0072)")
    ap.add_argument("--keep-bad", action="store_true",
                    help="keep bad=true rows in the file (default: keep them too — "
                         "05_select down-weights them; this flag is a no-op kept for clarity)")
    ap.add_argument("--drop-bad", action="store_true",
                    help="drop bad=true rows outright instead of leaving them to 05_select")
    ap.add_argument("--holdout-frac", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    n_scan = n_big = n_kept = 0
    chars = Counter()
    srcs = Counter()
    books = Counter()
    cpitches = []
    pages = set()
    fout_lab = open(out / "labeled.jsonl", "w")
    fout_cells = open(out / "cells.jsonl", "w")
    with open(args.src) as f:
        for line in f:
            n_scan += 1
            r = json.loads(line)
            if not r.get("big"):
                continue
            n_big += 1
            nl = r.get("n_line", 0)
            cp = float(r.get("cpitch", 0.0))
            pitch = float(r.get("pitch", 0.0))
            label = r.get("label") or ""
            if not (1 <= nl <= args.min_n_line):
                continue
            if pitch <= 0 or cp < max(args.pitch_frac * pitch, args.min_cpitch):
                continue
            if len(label) != 1 or not (0x4E00 <= ord(label) <= 0x9FFF):
                continue
            if r.get("label_src") in BAD_SOURCES:
                continue
            if args.drop_bad and r.get("bad"):
                continue
            n_kept += 1
            chars[label] += 1
            srcs[r.get("label_src", "?")] += 1
            books[r["key"].split("_")[0]] += 1
            cpitches.append(cp)
            pages.add(r["key"])
            fout_lab.write(json.dumps(r, ensure_ascii=False) + "\n")
            slim = {k: v for k, v in r.items() if k not in WITNESS_FIELDS}
            fout_cells.write(json.dumps(slim, ensure_ascii=False) + "\n")
    fout_lab.close()
    fout_cells.close()

    # page-level holdout over pages that actually hold big cells
    keys = sorted(pages)
    rng = random.Random(args.seed)
    hold = sorted(rng.sample(keys, max(1, round(len(keys) * args.holdout_frac))))
    (out / "holdout_pages.json").write_text(json.dumps(hold, ensure_ascii=False))
    hold_set = set(hold)

    # reuse the C line's per-char relative-width prior verbatim (77_generate_c --rel-width)
    rw = ROOT / "work-c" / "stroke_rel_width.npy"
    if rw.exists():
        shutil.copy2(rw, out / "stroke_rel_width.npy")

    for name in ("cells", "masks"):
        link = out / name
        if not link.exists():
            link.symlink_to(f"../work-c/{name}")

    cp_sorted = sorted(cpitches)
    def pct(q):  # noqa: E301
        return cp_sorted[min(len(cp_sorted) - 1, int(q * len(cp_sorted)))] if cp_sorted else 0

    hold_cells = sum(1 for line in open(out / "labeled.jsonl")
                     if json.loads(line)["key"] in hold_set)
    train_chars = set()
    hold_chars = set()
    for line in open(out / "labeled.jsonl"):
        r = json.loads(line)
        (hold_chars if r["key"] in hold_set else train_chars).add(r["label"])

    print(f"scanned {n_scan} rows, big={n_big}, kept={n_kept}")
    print(f"unique chars: {len(chars)}  (train pages {len(chars) - len(hold_chars)}, "
          f"holdout-only {len(hold_chars - train_chars)})")
    print(f"cpitch min/p50/p90/max: {pct(0):.0f}/{pct(0.5):.0f}/{pct(0.9):.0f}/{pct(1):.0f}")
    print(f"label_src: {dict(srcs)}")
    print(f"pages with big cells: {len(keys)}; holdout {len(hold)} pages / {hold_cells} cells")
    print(f"books: {dict(sorted(books.items()))}")
    common = chars.most_common(15)
    print("top chars:", " ".join(f"{c}x{n}" for c, n in common))


if __name__ == "__main__":
    main()
