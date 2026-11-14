"""C-line adapter for shared review_sheet; drawing stays in the library."""
import json, random, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_sheet as rs
rows = []
rng = random.Random(0)
def add(ch, tag, meta, crop=None, font="build/GuanGeKai-C-Regular.ttf", page=""):
    rows.append({"no": len(rows) + 1, "line": "C", "char": ch, "crop": crop,
                 "glyph_font": str(ROOT / font), "meta": meta, "tag": tag, "page": page})
chosen = [json.loads(l) for l in open(ROOT / "work-c/chosen.jsonl", encoding="utf-8")]
dual = [r for r in chosen if r.get("agree_ab")]
single = [r for r in chosen if not r.get("agree_ab")]
for r in rng.sample(dual, 12):
    add(r["label"], "dual", [f"p{r['page']} c{r['col']} l{r['li']}", "dual witness", "real"], f"work-c/cells/{r['file']}", "build/GuanGeKai-C-Real.ttf", str(r["page"]))
for r in rng.sample(single, 11):
    add(r["label"], "single", [f"p{r['page']} c{r['col']} l{r['li']}", "single witness", "real"], f"work-c/cells/{r['file']}", "build/GuanGeKai-C-Real.ttf", str(r["page"]))
hold = np.load(ROOT / "work-c/pairs_clean.npz", allow_pickle=True)
for i in rng.sample(range(len(hold["chars"])), 11):
    ch, f, k = hold["chars"][i], hold["files"][i], hold["keys"][i]
    add(str(ch), "holdout", [str(k), "page holdout", "real"], f"work-c/cells/{f}", "build/GuanGeKai-C-Regular.ttf", str(k))
gen = [json.loads(l) for l in open(ROOT / "work-c/generated.jsonl", encoding="utf-8")]
for tag, src in (("gan", "gen"), ("ribbon", "base")):
    for r in rng.sample([x for x in gen if x.get("src") == src], 33):
        add(r["char"], tag, [f"src={src}", "v1.3 ep090", tag], None, page="generated")
pngs = rs.build_sheet(rows, str(ROOT / "build/GuanGeKai-C-Regular.ttf"), str(ROOT / "work-c/qa/review-c/sheet-{n}.png"))
rs.write_tsv(rows, str(ROOT / "work-c/qa/review-c/ledger.tsv"))
print(len(rows), "rows", len(pngs), "sheets", pngs[0] if pngs else "")
