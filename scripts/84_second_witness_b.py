#!/usr/bin/env python3
"""B-Q4: second OCR witness (PP-OCRv5) for the chosen cells.

B's labels are single-witness for 47.6% of the real glyphs (pages where the reference
alignment failed); see B-Q8/B-Q12.  A second, independent recogniser gives an error proxy
without human review: run PP-OCRv5 rec on the same cell and compare with the stored label
(which came from PP-OCRv6 + reference alignment).

  python3 scripts/84_second_witness_b.py --n 0 --out work-b/second_witness_b.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from rapidocr import RapidOCR
from rapidocr.utils.typings import ModelType, OCRVersion

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--n", type=int, default=0, help="0 = every chosen glyph")
    ap.add_argument("--out", default=str(ROOT / "work-b" / "second_witness_b.json"))
    args = ap.parse_args()

    wd = Path(args.work)
    rows = [json.loads(l) for l in open(wd / "chosen.jsonl")]
    rows.sort(key=lambda r: r["label"])
    if args.n:
        rows = rows[: args.n]

    eng = RapidOCR(params={
        "Global.use_det": False, "Global.use_cls": False, "Global.log_level": "error",
        "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE,
        "EngineConfig.onnxruntime.intra_op_num_threads": 1,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    })

    t0, out = time.time(), []
    for i, r in enumerate(rows, 1):
        f = wd / "cells" / r["file"]
        try:
            res = eng(str(f))
            txt = (res.txts[0] if getattr(res, "txts", None) else "") or ""
            score = float(res.scores[0]) if getattr(res, "scores", None) else 0.0
        except Exception:  # noqa: BLE001
            txt, score = "", 0.0
        lab = r["label"]
        out.append({"char": lab, "v5": txt, "score": round(score, 4),
                    "agree": txt == lab, "coherent": bool(r.get("coherent")),
                    "ar": r.get("align_rate", 0), "file": r["file"]})
        if i % 500 == 0:
            print(f"  {i}/{len(rows)}  {time.time()-t0:.0f}s", flush=True)

    n = len(out)
    agree = sum(1 for o in out if o["agree"])
    nc = [o for o in out if not o["coherent"]]
    nc_agree = sum(1 for o in nc if o["agree"])
    res = {"n": n, "agree": agree, "agree_rate": round(agree / n, 4),
           "n_noncoherent": len(nc), "agree_noncoherent": nc_agree,
           "agree_rate_noncoherent": round(nc_agree / max(1, len(nc)), 4),
           "disagree": [o for o in out if not o["agree"]], "rows": out}
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"PP-OCRv5 witness: agree {agree}/{n} = {agree/n:.1%}; "
          f"non-coherent pages {nc_agree}/{len(nc)} = {nc_agree/max(1,len(nc)):.1%}; "
          f"{time.time()-t0:.0f}s")
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
