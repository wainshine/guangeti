"""P0-0.5: single-cell OCR sample (200 cells) — veto-only check of cell labels."""
from __future__ import annotations
import json, random, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"
sys.path.insert(0, str(ROOT / "scripts"))
from importlib.machinery import SourceFileLoader
ocr = SourceFileLoader("ocr92", str(ROOT / "scripts" / "92_ocr_c.py")).load_module()


def norm(t):
    return "".join(c for c in (t or "") if "\u4e00" <= c <= "\u9fff")


def main():
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--out", default=str(WORK / "cell_ocr_sample.json"))
    ap.add_argument("--sheet", default=str(ROOT / "docs/images/c-cell-ocr-sample.png"))
    args = ap.parse_args()
    rng = random.Random(42)
    cells = [json.loads(l) for l in open(WORK / "cells.jsonl")]
    by = {}
    for r in cells:
        by.setdefault((r["key"], r["li"]), []).append(r)
    suspect = {(k, li) for (k, li), cs in by.items() if len(cs) != cs[0].get("n_line", 0)}
    chosen = {json.loads(l)["file"] for l in open(WORK / "chosen.jsonl")}
    conf = set("申甲由田电因内四曰昌一十目自")
    merged = set()
    for r in cells:
        if r["label"] in ("一", "二", "三") and r["h"] > 0.8 * r.get("cpitch", 1):
            merged.add(r["file"])
    pools = {
        "chosen": [r for r in cells if r["file"] in chosen],
        "suspect": [r for r in cells if (r["key"], r["li"]) in suspect],
        "aligned": [r for r in cells if (r["key"], r["li"]) not in suspect],
        "confusable": [r for r in cells if r["label"] in conf],
        "merged": [r for r in cells if r["file"] in merged],
    }
    plan = [("chosen", 40), ("suspect", 60), ("aligned", 50), ("confusable", 20), ("merged", 30)]
    picked, seen = [], set()
    for name, n in plan:
        pool = [r for r in pools[name] if r["file"] not in seen and r.get("label")]
        rng.shuffle(pool)
        for r in pool[:n]:
            if r["file"] in seen: continue
            seen.add(r["file"]); r = dict(r); r["_pool"] = name; picked.append(r)
    # top up to n
    rest = [r for r in cells if r["file"] not in seen and r.get("label")]
    rng.shuffle(rest)
    for r in rest[: max(0, args.n - len(picked))]:
        r = dict(r); r["_pool"] = "rest"; picked.append(r)
    e6 = ocr.get_engine("v6"); e5 = ocr.get_engine("v5")
    out = []
    for i, r in enumerate(picked):
        img = cv2.imread(str(WORK / "cells" / r["file"]), cv2.IMREAD_GRAYSCALE)
        if img is None: continue
        h, w = img.shape
        sc = max(1.0, 128.0 / max(1, min(h, w)))
        if sc > 1: img = cv2.resize(img, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_CUBIC)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        reads = {}
        for name, eng in (("v6", e6), ("v5", e5)):
            try:
                res = eng(img)
                reads[name] = norm("".join(res.txts or []))[:2]
            except Exception as e:
                reads[name] = "ERR"
        lab = norm(r["label"])[:1]
        ok = (reads["v6"][:1] == lab) or (reads["v5"][:1] == lab)
        out.append({"file": r["file"], "label": lab, "pool": r["_pool"], "w": r["w"], "h": r["h"],
                    "cpitch": r.get("cpitch"), "v6": reads["v6"], "v5": reads["v5"], "ok": ok,
                    "suspect_row": (r["key"], r["li"]) in suspect})
        if i % 20 == 0: print(i, len(picked), flush=True)
    json.dump(out, open(args.out, "w"), ensure_ascii=False, indent=1)
    bad = [r for r in out if not r["ok"]]
    print("n", len(out), "mismatch", len(bad), f"{100*len(bad)/max(1,len(out)):.1f}%")
    # sheet: show mismatches (max 60)
    show = bad[:60]
    if show:
        S = 96; cols = 6; rows = (len(show) + cols - 1) // cols
        im = Image.new("RGB", (cols * (S + 40), rows * (S + 30)), "white"); d = ImageDraw.Draw(im)
        small = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 13)
        for j, r in enumerate(show):
            x = (j % cols) * (S + 40); y = (j // cols) * (S + 30)
            ci = Image.open(WORK / "cells" / r["file"]).convert("L"); ci.thumbnail((S, S))
            im.paste(ci, (x, y)); d.text((x, y + S), f"{r['label']}→{r['v6']}/{r['v5']}", font=small, fill="red")
        im.save(args.sheet); print("sheet", args.sheet)


if __name__ == "__main__":
    main()
