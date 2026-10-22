"""Cross-check chosen glyphs against the corpus means of every label."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from select_lib import norm_glyph
ROOT = Path(__file__).resolve().parents[1]
rows = [json.loads(l) for l in open(ROOT/'work'/'labeled.jsonl')]
rows = [r for r in rows if r['label']]
labels = sorted({r['label'] for r in rows})
idx = {l:i for i,l in enumerate(labels)}
V = np.zeros((len(rows), 48*48), np.float32)
ok = np.zeros(len(rows), bool)
for i,r in enumerate(rows):
    v,_ = norm_glyph(ROOT/'work'/'cells'/r['file'])
    if v is None: continue
    V[i] = v.ravel(); ok[i]=True
rows = [r for i,r in enumerate(rows) if ok[i]]
V = V[ok]
means = np.zeros((len(labels), V.shape[1]), np.float32)
cnt = np.zeros(len(labels))
for r,v in zip(rows,V):
    means[idx[r['label']]] += v; cnt[idx[r['label']]] += 1
means /= np.maximum(cnt,1)[:,None]
chosen = {json.loads(l)['label']: json.loads(l) for l in open(ROOT/'work'/'chosen.jsonl')}
byfile = {r['file']:i for i,r in enumerate(rows)}
out=[]
for lab,r in chosen.items():
    i = byfile.get(r['file'])
    if i is None: continue
    v = V[i]
    d = ((means - v)**2).sum(1)
    order = np.argsort(d)
    own = d[idx[lab]]
    best = labels[order[0]]
    second = labels[order[1]] if order[0]==idx[lab] else labels[order[0]]
    # similarity margin relative to the label's own dispersion
    margin = (own - d[order[0]]) / (own + 1e-6)
    out.append(dict(char=lab, best=best, own=float(own), bestd=float(d[order[0]]),
                    margin=float(margin), n=int(cnt[idx[lab]]), file=r['file']))
bad = [o for o in out if o['best'] != o['char'] and o['margin'] > 0.35]
bad.sort(key=lambda o: -o['margin'])
print('flagged', len(bad), 'of', len(out))
for o in bad[:40]:
    print(f"{o['char']} -> {o['best']}  margin {o['margin']:.2f} n={o['n']}")
json.dump(out, open(ROOT/'work'/'label_check.json','w'), ensure_ascii=False)
