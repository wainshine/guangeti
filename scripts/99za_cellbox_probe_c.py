"""Probe: match RapidOCR single-character boxes to bench cell boxes.

Run on work-c/ocr_bench.json (700 unique cells).  This is a diagnostic:
it does not rewrite labels or masks.
"""
from __future__ import annotations
import argparse, json, collections, math
from pathlib import Path
import cv2
from importlib.machinery import SourceFileLoader
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
ocr=SourceFileLoader('ocr',str(ROOT/'scripts/92_ocr_c.py')).load_module()

def load_meta(path):
    m={}
    for l in open(path):
        r=json.loads(l); m[r['file']]=(r['x0'],r['y0'],r['x1'],r['y1'])
    return m
v3d2=load_meta(W/'cells.jsonl'); v3c=load_meta(W/'archive/v1.2.0-v3c/cells.jsonl')
anchors={json.loads(l)['id']:json.loads(l) for l in open(W/'verified/index.jsonl')}

def cell_bbox(r):
    f=r.get('file','')
    if f in v3d2: return v3d2[f]
    if f in v3c: return v3c[f]
    a=anchors.get(f.replace('.png',''))
    if a and a.get('bbox'): return tuple(a['bbox'])
    return None

def boxes(page, eng):
    r=eng(page, return_word_box=True, return_single_char_box=True)
    out=[]
    for line in (r.word_results or []):
        for ch,score,poly in line:
            xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
            out.append((ch,float(score),min(xs),min(ys),max(xs),max(ys)))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--bench',default=str(W/'ocr_bench.json'))
    ap.add_argument('--out',default=str(W/'cellbox_probe.json'))
    ap.add_argument('--max-pages',type=int,default=0)
    args=ap.parse_args()
    cells=json.load(open(args.bench))['cells']
    bypage=collections.defaultdict(list)
    for r in cells:
        if cell_bbox(r): bypage[r['key']].append(r)
    keys=sorted(bypage)
    if args.max_pages: keys=keys[:args.max_pages]
    e6=ocr.get_engine('v6'); e5=ocr.get_engine('v5')
    rows=[]
    for pi,key in enumerate(keys):
        p=W/'pages150'/f'{key}.jpg'
        img=cv2.imread(str(p))
        if img is None: print('missing',p); continue
        b6=boxes(img,e6); b5=boxes(img,e5)
        for r in bypage[key]:
            bb=cell_bbox(r); x0,y0,x1,y1=[v/2 for v in bb]
            cx,cy=(x0+x1)/2,(y0+y1)/2
            pad=0.15*max(x1-x0,y1-y0)
            def pick(boxes_):
                cand=[]
                for ch,sc,a,b,c,d in boxes_:
                    mx,my=(a+c)/2,(b+d)/2
                    if x0-pad<=mx<=x1+pad and y0-pad<=my<=y1+pad: cand.append((ch,sc,a,b,c,d))
                if len(cand)>1: return None,cand
                if cand: return cand[0],cand
                best=None
                for ch,sc,a,b,c,d in boxes_:
                    mx,my=(a+c)/2,(b+d)/2; dist=math.hypot(mx-cx,my-cy)
                    if best is None or dist<best[0]: best=(dist,ch,sc)
                if best and best[0] < 0.5*max(x1-x0,y1-y0): return (best[1],best[2],0,0,0,0),[]
                return None,[]
            a,c6=pick(b6); b,c5=pick(b5)
            if a is None or b is None:
                status='MULTI' if c6 or c5 else 'UNMATCHED'
            else:
                v6,v5=a[0],b[0]
                if v6==v5==r['label_current']: status='AGREE'
                elif v6==v5: status='WRONG_LABEL'
                else: status='DISAGREE'
            rows.append({**{k:r[k] for k in ('bench_id','source','version','key','li','sub','file','label_current','cut_status','cut_type','oracle_kind','content_oracle')},
                         'v6':a[0] if a else '', 'v5':b[0] if b else '', 'status':status})
        if pi and pi%20==0: print('pages',pi,'/',len(keys),flush=True)
    c=collections.Counter((r['oracle_kind'],r['status']) for r in rows)
    summary=collections.defaultdict(dict)
    for (kind,st),n in c.items(): summary[kind][st]=n
    json.dump({'rows':rows,'summary':summary,'n_pages':len(keys),'n_cells':len(rows)},open(args.out,'w'),ensure_ascii=False,indent=1)
    print(json.dumps(summary,ensure_ascii=False,indent=1)); print('->',args.out)

if __name__=='__main__': main()
