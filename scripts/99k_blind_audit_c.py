"""Build the 400-cell blind human audit (design C: 200 uniform + 200 targeted).

Sheets show the cell image + id + k + line text, but NOT our label.  The answer key
is written separately and sealed until marking is done.
"""
from __future__ import annotations
import json, random, re, collections
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from importlib.machinery import SourceFileLoader

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def cjk(s):
    return "".join(c for c in s if CJK.match(c))


def main():
    seg = SourceFileLoader("seg", str(ROOT / "scripts" / "93_segment_c.py")).load_module()
    v6 = {json.loads(l)["key"]: json.loads(l)["lines"] for l in open(WORK / "ocr_v6.jsonl")}
    line_text = {}
    for key, raw in v6.items():
        for li, ln in enumerate(seg.dedupe_boxes(raw)):
            line_text[(key, li)] = cjk(ln["text"])
    cells = []
    for l in open(WORK / "cells.jsonl"):
        r = json.loads(l)
        if r.get("label"):
            cells.append(r)
    by = collections.defaultdict(list)
    for r in cells:
        by[(r["key"], r["li"])].append(r)
    rng = random.Random(42)
    picked = []

    def add(r, stratum):
        picked.append({"file": r["file"], "key": r["key"], "li": r["li"], "sub": r["sub"],
                       "our_label": cjk(r.get("label", ""))[:1], "w": r.get("w"), "h": r.get("h"),
                       "cpitch": r.get("cpitch"), "merged": bool(r.get("merged")),
                       "stratum": stratum})

    seen = set()
    def take(pool, n, stratum):
        pool = [r for r in pool if r["file"] not in seen]
        rng.shuffle(pool)
        for r in pool[:n]:
            seen.add(r["file"]); add(r, stratum)

    # 200 uniform
    take(cells, 200, "uniform")
    # targeted from pilot
    pilot = json.load(open(WORK / "sentinel_pilot.json"))["rows"]
    same = [p for p in pilot if p.get("both_bad")]
    diff = [p for p in pilot if p.get("v6") and p.get("v5") and p["v6"] != p["v5"]]
    ok = [p for p in pilot if p.get("ok")]
    blank = [p for p in pilot if not p.get("v6") and not p.get("v5")]
    for name, pool, n in (("same_wrong", same, 50), ("different", diff, 30),
                          ("read_back", ok, 30), ("blank", blank, 20)):
        rng.shuffle(pool)
        for p in pool[:n]:
            if p["file"] in seen: continue
            r = next((x for x in cells if x["file"] == p["file"]), None)
            if r is None: continue
            seen.add(r["file"]); add(r, name)
    # geometry / merged / horizontal / confusable
    merged = [r for r in cells if r.get("merged")]
    take(merged, 30, "merged")
    take([r for r in cells if r.get("label") in ("一", "二", "三")], 20, "horizontal")
    take([r for r in cells if r.get("label") in set("申甲由田电因内")], 20, "confusable")
    # top up to 400 from random cells
    if len(picked) < 400:
        take(cells, 400 - len(picked), "topup")
    rng.shuffle(picked)
    for i, p in enumerate(picked, 1):
        p["id"] = i
        p["line_text"] = line_text.get((p["key"], p["li"]), "")
        p["n"] = len(p["line_text"])
        p["k"] = p["sub"]
    # key + manifest
    key = {"design": "C: 200 uniform + 200 targeted (no A/B controls yet)",
           "overall_from": "uniform only", "cells": picked}
    json.dump(key, open(WORK / "blind_400_key.json", "w"), ensure_ascii=False, indent=1)
    cnt = collections.Counter(p["stratum"] for p in picked)
    json.dump({"strata": dict(cnt), "n": len(picked), "overall_from": "uniform",
               "note": "targeted strata must NOT be pooled into the overall rate"},
              open(WORK / "blind_400_manifest.json", "w"), ensure_ascii=False, indent=1)
    # sheets: 4 x 100, 5 cols x 20 rows, 160px cells
    S = 160; cols = 5; per = 100
    small = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 12)
    for page in range(4):
        chunk = picked[page * per:(page + 1) * per]
        if not chunk: break
        rows = (len(chunk) + cols - 1) // cols
        W = cols * (S + 30); H = rows * (S + 40)
        im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
        for j, p in enumerate(chunk):
            x = (j % cols) * (S + 30); y = (j // cols) * (S + 40)
            try:
                ci = Image.open(WORK / "cells" / p["file"]).convert("L")
                ci.thumbnail((S, S))
                im.paste(ci, (x + (S - ci.width) // 2, y + (S - ci.height) // 2))
            except Exception:
                pass
            d.text((x, y + S + 2), f"#{p['id']:03d} k={p['k']}/{p['n']}", font=small, fill="black")
            d.text((x, y + S + 16), p["line_text"][:12], font=small, fill="gray")
        out = ROOT / "docs" / "images" / f"c-blind-{page+1}.png"
        im.save(out); print(out, im.size)
    print(json.dumps(dict(cnt), ensure_ascii=False))


if __name__ == "__main__":
    main()
