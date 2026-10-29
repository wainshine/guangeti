"""P0-1.3 pilot: OCR first/middle/last cell of 2,000 lines, compare to line text.

No human truth yet: this measures (a) whether sentinel positions are readable at all,
(b) mismatch rate by geometry-suspect vs clean lines, (c) ab vs a_only.  The 400-cell
human audit supplies the FP calibration later.
"""
from __future__ import annotations
import argparse, json, random, re, statistics, collections
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def cjk(s):
    return "".join(c for c in s if CJK.match(c))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, default=2000)
    ap.add_argument("--out", default=str(WORK / "sentinel_pilot.json"))
    ap.add_argument("--sheet", default=str(ROOT / "docs/images/c-sentinel-pilot.png"))
    args = ap.parse_args()
    from importlib.machinery import SourceFileLoader
    seg = SourceFileLoader("seg", str(ROOT / "scripts" / "93_segment_c.py")).load_module()
    ocr = SourceFileLoader("ocr", str(ROOT / "scripts" / "92_ocr_c.py")).load_module()
    v6 = {json.loads(l)["key"]: json.loads(l)["lines"] for l in open(WORK / "ocr_v6.jsonl")}
    by = collections.defaultdict(list)
    for l in open(WORK / "cells.jsonl"):
        r = json.loads(l); by[(r["key"], r["li"])].append(r)
    abmap = {}
    for l in open(WORK / "labeled.jsonl"):
        r = json.loads(l); abmap[r["file"]] = bool(r.get("agree_ab"))
    # geometry flag
    geom = {}
    for (key, li), cs in by.items():
        if len(cs) < 3: continue
        cs = sorted(cs, key=lambda r: r["sub"]); w = [max(1, c["w"]) for c in cs]
        med = statistics.median(w); mean = statistics.mean(w)
        cv = statistics.pstdev(w) / mean if mean else 0
        merged = any(w[i] > 1.4 * med and i + 1 < len(w) and w[i + 1] < 0.6 * med for i in range(len(w) - 1))
        broken = any(w[i] < 0.6 * med and i + 1 < len(w) and w[i + 1] < 0.8 * med for i in range(len(w) - 1))
        geom[(key, li)] = (cv > 0.35) or merged or broken
    pool = []
    for key, raw in v6.items():
        for li, ln in enumerate(seg.dedupe_boxes(raw)):
            ch = cjk(ln["text"])
            cs = by.get((key, li), [])
            if len(ch) >= 3 and len(cs) >= 3:
                pool.append({"key": key, "li": li, "ch": ch, "cs": sorted(cs, key=lambda r: r["sub"]),
                             "geom": geom.get((key, li), False)})
    rng = random.Random(42)
    clean = [p for p in pool if not p["geom"]]; sus = [p for p in pool if p["geom"]]
    rng.shuffle(clean); rng.shuffle(sus)
    n_half = args.lines // 2
    picked = clean[:n_half] + sus[: args.lines - n_half]
    print("pool", len(pool), "clean", len(clean), "sus", len(sus), "picked", len(picked), flush=True)
    e6 = ocr.get_engine("v6"); e5 = ocr.get_engine("v5")
    res = []
    for i, p in enumerate(picked):
        n = len(p["cs"]); pos = sorted({0, n // 2, n - 1})
        for k in pos:
            ptype = "first" if k == 0 else ("last" if k == n - 1 else "mid")
            c = p["cs"][k]
            img = cv2.imread(str(WORK / "cells" / c["file"]), cv2.IMREAD_GRAYSCALE)
            if img is None: continue
            h, w = img.shape; sc = max(1.0, 128.0 / max(1, min(h, w)))
            if sc > 1: img = cv2.resize(img, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_CUBIC)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            reads = {}
            for name, eng in (("v6", e6), ("v5", e5)):
                try:
                    r = eng(img, use_det=False, use_cls=False, use_rec=True)
                    reads[name] = cjk("".join(r.txts or []))[:1]
                except Exception:
                    reads[name] = "ERR"
            lab = cjk(c.get("label", ""))[:1]
            res.append({"key": p["key"], "li": p["li"], "sub": c["sub"], "pos": ptype,
                        "file": c["file"],
                        "label": lab, "v6": reads["v6"], "v5": reads["v5"],
                        "geom": p["geom"], "ab": abmap.get(c["file"], False),
                        "ok": (reads["v6"] == lab) or (reads["v5"] == lab),
                        "both_bad": reads["v6"] != lab and reads["v5"] != lab})
        if i % 100 == 0: print(i, len(picked), flush=True)
    def rate(sel):
        s = [r for r in res if sel(r)]
        return (len(s), round(100 * sum(1 for r in s if not r["ok"]) / max(1, len(s)), 1),
                round(100 * sum(1 for r in s if r["both_bad"]) / max(1, len(s)), 1))
    out = {"n_lines": len(picked), "n_cells": len(res),
           "clean": rate(lambda r: not r["geom"]), "geom": rate(lambda r: r["geom"]),
           "ab": rate(lambda r: r["ab"]), "aonly": rate(lambda r: not r["ab"]),
           "pos_first": rate(lambda r: r["pos"] == "first"),
           "pos_mid": rate(lambda r: r["pos"] == "mid"),
           "pos_last": rate(lambda r: r["pos"] == "last"),
           "both_bad": sum(1 for r in res if r["both_bad"])}
    json.dump({"summary": out, "rows": res}, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    bad = [r for r in res if r["both_bad"]][:40]
    if bad:
        S = 96; cols = 8; rows = (len(bad) + cols - 1) // cols
        im = Image.new("RGB", (cols * (S + 30), rows * (S + 30)), "white"); d = ImageDraw.Draw(im)
        f = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 13)
        for j, r in enumerate(bad):
            x = (j % cols) * (S + 30); y = (j // cols) * (S + 30)
            try:
                ci = Image.open(WORK / "cells" / r["file"]).convert("L"); ci.thumbnail((S, S)); im.paste(ci, (x, y))
            except Exception:
                pass
            d.text((x, y + S), f"{r['label']}→{r['v6']}/{r['v5']}", font=f, fill="red")
        im.save(args.sheet)


if __name__ == "__main__":
    main()
