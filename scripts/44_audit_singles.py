"""A-Q0: are the 617 single-occurrence labels as trustworthy as the 1,675 chosen ones?

Method: per-cell OCR as an independent second witness.  Every labelled cell is re-OCR'd
on its own crop; a label whose second witness disagrees goes to a human/visual adjudication
list.  Comparing the disagreement rate of singles vs a random control from multi-sample
labels gives a same-population estimate of relative label risk.

Output: work/singles_audit.json (counts, rates, Wilson CI, Fisher p, adjudication list).
This is measurement only: it never rewrites labels or fonts.

Usage:
    python3 scripts/44_audit_singles.py --n-control 150
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def norm(ch: str) -> str:
    """Compare tradition/simplified forms as equal; OCR often returns simplified."""
    try:
        from opencc import OpenCC
        return OpenCC("t2s").convert(ch)
    except Exception:
        return ch


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-control", type=int, default=150)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(ROOT / "work" / "singles_audit.json"))
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(ROOT / "work" / "labeled.jsonl")]
    by = defaultdict(list)
    for r in rows:
        by[r["label"]].append(r["file"])
    singles = {c: f[0] for c, f in by.items() if len(f) == 1}
    multi = [c for c, f in by.items() if len(f) >= 2]
    rng = random.Random(args.seed)
    control = rng.sample(sorted(multi), min(args.n_control, len(multi)))

    from rapidocr import RapidOCR
    engine = RapidOCR()

    def ocr(file: str) -> str:
        res = engine(str(ROOT / "work" / "cells" / file))
        txt = getattr(res, "txts", None)
        return (txt[0] if txt else "") or ""

    def run(chars: dict[str, str]):
        out = []
        for i, (ch, f) in enumerate(sorted(chars.items()), 1):
            got = ocr(f)
            out.append({"label": ch, "file": f, "ocr": got,
                        "agree": bool(got) and norm(got[0]) == norm(ch)})
            if i % 50 == 0:
                print(f"  {i}/{len(chars)}", flush=True)
        return out

    print(f"singles {len(singles)} | control {len(control)}")
    s_rows = run(singles)
    c_rows = run({c: by[c][0] for c in control})

    def report(name, rs):
        n = len(rs)
        bad = [r for r in rs if not r["agree"]]
        lo, hi = wilson(len(bad), n)
        return {"n": n, "disagree": len(bad), "rate": round(len(bad) / n, 4),
                "ci95": [round(lo, 4), round(hi, 4)], "bad": bad}

    S, C = report("singles", s_rows), report("control", c_rows)
    from scipy.stats import fisher_exact
    table = [[S["disagree"], S["n"] - S["disagree"]],
             [C["disagree"], C["n"] - C["disagree"]]]
    p = float(fisher_exact(table)[1])

    out = {
        "method": "per-cell PP-OCRv6 second witness; t2s-normalised compare",
        "seed": args.seed, "control_n": len(control),
        "singles": {k: S[k] for k in ("n", "disagree", "rate", "ci95")},
        "control": {k: C[k] for k in ("n", "disagree", "rate", "ci95")},
        "fisher_p": round(p, 4),
        "adjudicate": S["bad"] + C["bad"],
        "verdict_hint": ("include" if S["ci95"][1] <= 0.08 and p >= 0.05
                         else "do_not_include_without_manual_adjudication"),
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("singles", "control", "fisher_p", "verdict_hint")},
                     ensure_ascii=False, indent=1))
    print(f"-> {args.out}  (adjudication list: {len(out['adjudicate'])})")


if __name__ == "__main__":
    main()
