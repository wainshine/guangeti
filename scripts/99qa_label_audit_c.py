#!/usr/bin/env python3
"""C-Q1 sample pack: 300 real labels, stratified, blind crops + private key."""
import json, random, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
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
OUT.mkdir(parents=True, exist_ok=True); (OUT / "crops").mkdir(exist_ok=True)
with open(OUT / "key.tsv", "w", encoding="utf-8") as key, open(OUT / "blind.tsv", "w", encoding="utf-8") as blind:
    key.write("no\tchar\tstratum\tpage\tfile\tlabel_src\tagree_ab\tn_samples\tbig\n")
    blind.write("no\tguessed_char\tdefect\tnotes\n")
    for i, (name, r) in enumerate(rows, 1):
        dst = f"{i:04d}.png"; shutil.copyfile(ROOT / "work-c/cells" / r["file"], OUT / "crops" / dst)
        key.write(f"{i:04d}\t{r['label']}\t{name}\t{r.get('page')}\t{r['file']}\t{r.get('label_src')}\t{r.get('agree_ab')}\t{r.get('n_samples')}\t{r.get('big')}\n")
        blind.write(f"{i:04d}\t\t\t\n")
print(len(rows), "samples", OUT)
