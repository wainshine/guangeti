"""C-line stage 2: two independent OCR passes over every text page.

The 大典 has no reference transcription, so the only way to trust a label is to make
two witnesses disagree as little as possible and then verify the survivors.  The two
passes deliberately differ in engine *and* preprocessing:

  A  PP-OCRv6 small on the rectified colour page (the same recipe A/B used);
  B  PP-OCRv5 mobile on a red-removed, contrast-stretched copy upscaled 1.3x.

v6 and v5 are different releases (different training corpora, different detector), and
the red-removal changes what the detector sees around the 朱丝栏, so their errors are
far from perfectly correlated.  Agreement between A and B is the primary label signal;
neither is trusted alone.

Outputs (coordinates in the 150 dpi rectified space, p300 = 2 * p150):
  work-c/ocr_v6.jsonl   {key, page, variant, lines:[{box,text,score}]}
  work-c/ocr_v5.jsonl

  python3 scripts/92_ocr_c.py --workers 6
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"
MODELS = WORK / "models"

ENGINE = {}


def get_engine(variant: str):
    if variant in ENGINE:
        return ENGINE[variant]
    from rapidocr import RapidOCR
    from rapidocr.utils.typings import ModelType, OCRVersion
    base = {"Global.model_root_dir": str(MODELS),
            "EngineConfig.onnxruntime.intra_op_num_threads": 1,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1}
    if variant == "v6":
        e = RapidOCR(params=base)
    else:
        e = RapidOCR(params={**base,
                             "Det.ocr_version": OCRVersion.PPOCRV5,
                             "Det.model_type": ModelType.MOBILE,
                             "Rec.ocr_version": OCRVersion.PPOCRV5,
                             "Rec.model_type": ModelType.MOBILE})
    ENGINE[variant] = e
    return e


def prep_b(img: np.ndarray, scale: float = 1.3):
    """Red-removed, contrast-stretched grey for witness B."""
    b, g, r = img[:, :, 0].astype(np.int16), img[:, :, 1].astype(np.int16), img[:, :, 2].astype(np.int16)
    red = ((r - g) > 40) & ((r - b) > 34)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray[red] = 255
    p2, p98 = np.percentile(gray, 2), np.percentile(gray, 98)
    span = max(1.0, p98 - p2)
    g2 = np.clip((gray.astype(np.float32) - p2) * 255.0 / span, 0, 255).astype(np.uint8)
    g2 = cv2.cvtColor(g2, cv2.COLOR_GRAY2BGR)
    if scale != 1.0:
        g2 = cv2.resize(g2, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return g2


def run_page(task):
    key, path, variants = task
    cv2.setNumThreads(1)
    out = {}
    try:
        img = cv2.imread(str(path))
        if img is None:
            return key, out, "cannot read"
        for v in variants:
            e = get_engine(v)
            if v == "v6":
                src = img
                sc = 1.0
            else:
                src = prep_b(img)
                sc = 1.3
            r = e(src)
            lines = []
            if r is not None and r.boxes is not None:
                for box, txt, s in zip(r.boxes, r.txts, r.scores):
                    lines.append(dict(box=[[float(x) / sc, float(y) / sc] for x, y in box],
                                      text=txt, score=float(s)))
            out[v] = lines
        return key, out, None
    except Exception:
        import traceback
        return key, out, traceback.format_exc()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--variants", default="v6,v5")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--keys", default="", help="comma separated page keys (debug)")
    args = ap.parse_args()
    variants = args.variants.split(",")
    stats = [json.loads(l) for l in open(WORK / "page_stats.jsonl")]
    todo = [s for s in stats if s["content"] == "text"]
    if args.keys:
        keep = set(args.keys.split(","))
        todo = [s for s in todo if s["key"] in keep]
    if args.limit:
        todo = todo[:args.limit]
    tasks = [(s["key"], WORK / "pages150" / (s["key"] + ".jpg"), variants) for s in todo]
    print(f"pages {len(tasks)} variants {variants}", flush=True)
    # download/validate the model files once, before the pool starts: six workers
    # racing on the same URL left a truncated .onnx in work-c/models
    for v in variants:
        get_engine(v)
    print("models ready", {v: str(get_engine(v).cfg["Det"].get("model_path") or "") for v in variants},
          flush=True)

    files = {v: open(WORK / f"ocr_{v}.jsonl", "w") for v in variants}
    t0 = time.time()
    done = 0
    import multiprocessing as mp
    ctx = mp.get_context("fork")
    with ctx.Pool(args.workers) as pool:
        for key, out, err in pool.imap_unordered(run_page, tasks):
            if err:
                print(f"[ERR] {key}: {err.splitlines()[-1]}", flush=True)
            for v, lines in out.items():
                files[v].write(json.dumps(dict(key=key, variant=v, lines=lines),
                                          ensure_ascii=False) + "\n")
            done += 1
            if done % 50 == 0:
                el = time.time() - t0
                print(f"{done}/{len(tasks)} {el:.0f}s ({el/done:.2f}s/page)", flush=True)
    for f in files.values():
        f.close()
    print(f"done {done} pages in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
