"""Build work-c/ocr_bench.json from the human audits.

Three sources:
  400 v3c cells: marked = cut fail, unmarked = cut pass (content NOT verified)
  300 v3d2 cells: same, ids only
  572 verified anchors: content-verified labels

A record is one audit cell; the same (key,li,sub) can occur in v3c and v3d2
cuts, so `dedupe_key` includes the cut version and must be used explicitly.
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
def sha16(s): return hashlib.sha256(s.encode()).hexdigest()[:16]
row400=json.load(open(W/'blind_400_key.json'))['cells']
mark400={r['id']:r for r in json.load(open(W/'blind_400_marked.json'))}
row300=json.load(open(W/'exp/v3d2/blind_300_key.json'))['cells']
mark300=set(json.load(open(W/'exp/v3d2/blind_300_audit.json'))['ids'])
anchors=[json.loads(l) for l in open(W/'verified/index.jsonl')]
out=[]
for r in row400:
    m=mark400.get(r['id']); src='v3c-audit400'
    out.append({'bench_id':f'400:{r["id"]}','source':src,'version':'v3c',
      'key':r['key'],'li':r['li'],'sub':r['sub'],'file':r['file'],
      'label_current':r.get('our_label',''),
      'cut_status':'fail' if m else 'pass',
      'cut_type':(m or {}).get('type',''),
      'content_oracle':None,'oracle_kind':'cut_pass_content_unknown' if not m else 'cut_fail',
      'dedupe_key':f'{src}:{r["key"]}:{r["li"]}:{r["sub"]}'})
for r in row300:
    src='v3d2-audit300'; bad=r['id'] in mark300
    out.append({'bench_id':f'300:{r["id"]}','source':src,'version':'v3d2',
      'key':r['key'],'li':r['li'],'sub':r['sub'],'file':r['file'],
      'label_current':r.get('our_label',''),
      'cut_status':'fail' if bad else 'pass','cut_type':'',
      'content_oracle':None,'oracle_kind':'cut_fail' if bad else 'cut_pass_content_unknown',
      'dedupe_key':f'{src}:{r["key"]}:{r["li"]}:{r["sub"]}'})
for a in anchors:
    src=a.get('source','verified'); ver='v3d2' if 'v3d2' in src else 'v3c'
    out.append({'bench_id':f'anchor:{a["id"]}','source':f'verified-{src}','version':ver,
      'key':a.get('key'),'li':a.get('line'),'sub':a.get('sub'),
      'file':a['id']+'.png','label_current':a['label'],
      'cut_status':'pass','cut_type':'',
      'content_oracle':None,'oracle_kind':'cut_pass_content_unverified',
      'dedupe_key':f'verified:{ver}:{a.get("key")}:{a.get("line")}:{a.get("sub")}:{a["id"]}'})
meta={'n_records':len(out),'sources':{s:sum(1 for r in out if r['source'].startswith(s)) for s in ('v3c-audit400','v3d2-audit300','verified')},
      'content_verified':0,
      'cut_fail':sum(1 for r in out if r['cut_status']=='fail'),
      'cut_pass_content_unverified':sum(1 for r in out if r['oracle_kind']=='cut_pass_content_unverified'),
      'unique_dedupe_keys':len({r['dedupe_key'] for r in out}),
      'p90_estimator':'ordinal_index',
      'note':'No content oracle: 400/300 unmarked and the 572 anchors are cut-pass, not content-verified. Do not use them as label truth.'}
json.dump({'meta':meta,'cells':out},open(W/'ocr_bench.json','w'),ensure_ascii=False,indent=1)
print(json.dumps(meta,ensure_ascii=False,indent=1))
