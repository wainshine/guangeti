"""Rectify a 《史記》 spread: straighten every text column, dump before/after panels.

Prototype / QA tool for the B-line pipeline.  Measured at the native 150 dpi and
reported both at 300 dpi (what the pipeline uses) and at 100 dpi (the acceptance
figure quoted in docs/PROMPT-SHIJI.md §2).

  python3 scripts/50_shiji_dewarp.py --pages 100,500,1000 --out work-b/dewarp_qa
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from shiji_page import dewarp_page  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "史记.二十四册.传姜立纲抄本.新加坡国立大学藏.水印.pdf"


def parse_pages(s: str, n: int):
    if not s:
        return list(range(n))
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def panel(before, after, path):
    """Side-by-side leaf strip: original on top, rectified below."""
    h, w = before.shape[:2]
    sc = 900.0 / h
    b = cv2.resize(before, (int(w * sc), 900), interpolation=cv2.INTER_AREA)
    a = cv2.resize(after, (int(w * sc), 900), interpolation=cv2.INTER_AREA)
    gap = np.full((10, b.shape[1], 3), 128, np.uint8)
    cv2.imwrite(str(path), np.vstack([b, gap, a]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="100,500,1000")
    ap.add_argument("--dpi", type=int, default=300, help="render dpi (native scan is 150)")
    ap.add_argument("--out", default=str(ROOT / "work-b" / "dewarp_qa"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(PDF)
    pages = parse_pages(args.pages, doc.page_count)
    rows = []
    for p in pages:
        t0 = time.time()
        pix = doc[p].get_pixmap(dpi=args.dpi)
        rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
        res = dewarp_page(rgb)
        info = res["info"]
        info["page"] = p
        info["shape"] = list(res["image"].shape[:2])
        info["sec"] = round(time.time() - t0, 2)
        rows.append(info)
        panel(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), cv2.cvtColor(res["image"], cv2.COLOR_RGB2BGR),
              out / f"panel_p{p:04d}.png")
        cv2.imwrite(str(out / f"before_p{p:04d}.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(out / f"after_p{p:04d}.png"), cv2.cvtColor(res["image"], cv2.COLOR_RGB2BGR))
        print(json.dumps(info, ensure_ascii=False), flush=True)

    # --------- reporting: convert residuals to 100 dpi for the documented criterion
    conv = 100.0 / args.dpi
    print("\n=== column straightness (res = |midline - best fit line|, px) ===")
    print("page  leaf  n   before_res_med  after_res_med  after@100dpi  near/far   max_shift")
    ratios = []
    for r in rows:
        for b, a in zip(r.get("before", []), r.get("after", [])):
            near, far = a.get("near"), a.get("far")
            ratio = (near / far) if (near and far and far > 1e-6) else None
            if ratio:
                ratios.append(ratio)
            print(f"{r['page']:4d}  {b['leaf']}  {a['n']:2d}   {b['res_med']:6.2f}        "
                  f"{a['res_med']:6.2f}       {a['res_med']*conv:6.2f}    "
                  f"{(f'{ratio:.2f}' if ratio else '   -')}     {r['max_shift_px']:6.2f}")
    if ratios:
        print(f"\nnear-spine / page-edge residual ratio: median {np.nanmedian(ratios):.3f} "
              f"max {max(ratios):.3f}")
    (out / "dewarp_metrics.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    print("->", out)


if __name__ == "__main__":
    main()
