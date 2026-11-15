#!/usr/bin/env python3
"""C-Q1 sample pack: 300 real labels, stratified, blind crops + private key."""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_sheet as rs
OUT = ROOT / "work-c/qa/label-audit"
chosen = [json.loads(l) for l in open(ROOT / "work-c/chosen.jsonl", encoding="utf-8")]
rng = random.Random(0)
seen, groups = set(), []
def take(name, n, pred):
    pool = [r for r in chosen if r["file"] not in seen and pred(r)]
    pick = rng.sample(pool, min(n, len(pool)))
    seen.update(r["file"] for r in pick)
    groups.append((name, pick))
take("dual_common", 100, lambda r: r.get("agree_ab") and r.get("n_samples", 0) >= 5 and not r.get("big"))
take("dual_low", 60, lambda r: r.get("agree_ab") and (r.get("n_samples", 0) < 5 or r.get("big")))
take("single", 60, lambda r: not r.get("agree_ab"))
take("big", 40, lambda r: r.get("big"))
take("rare", 40, lambda r: r.get("n_samples", 0) <= 2)
rows = [(name, r) for name, rs in groups for r in rs]
OUT.mkdir(parents=True, exist_ok=True)
review_rows = []
with open(OUT / "key.tsv", "w", encoding="utf-8") as key:
    key.write("no\tchar\tstratum\tpage\tfile\tlabel_src\tagree_ab\tn_samples\tbig\n")
    for i, (name, r) in enumerate(rows, 1):
        key.write(f"{i:04d}\t{r['label']}\t{name}\t{r.get('page')}\t{r['file']}\t{r.get('label_src')}\t{r.get('agree_ab')}\t{r.get('n_samples')}\t{r.get('big')}\n")
        review_rows.append({"no": i, "line": "C", "char": r["label"],
                            "crop": f"work-c/cells/{r['file']}",
                            "glyph_font": str(ROOT / "build/GuanGeKai-C-Real.ttf"),
                            "meta": [f"p{r.get('page')} c{r.get('col')} l{r.get('li')}", name,
                                     f"src={r.get('label_src')} n={r.get('n_samples')}"],
                            "tag": name, "page": str(r.get("page", ""))})
pngs = rs.build_sheet(review_rows, str(ROOT / "build/GuanGeKai-C-Real.ttf"),
                      str(OUT / "sheet-{n}.png"))
rs.write_tsv(review_rows, OUT / "ledger.tsv")
(OUT / "verdict.tsv").write_text("no\tlabel_ok\tcorrect_char\tdefect\tnotes\n" +
    "".join(f"{i:04d}\t\t\t\t\n" for i in range(1, len(rows) + 1)), encoding="utf-8")
print(len(rows), "samples", len(pngs), "sheets", OUT)
