"""A++ geometry repair: re-crop the 34 B/C cells from pages300 at the assigned
v6 box, and write a separate geomfix map.  Canonical cells/masks are untouched.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import cv2, numpy as np
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--guard',default=str(W/'preview/geom_guard.jsonl'))
    ap.add_argument('--assign',default=str(W/'preview/geom_assign.jsonl'))
    ap.add_argument('--out',default=str(W/'geomfix'))
    ap.add_argument('--map',default=str(W/'preview/geomfix_map.json'))
    args=ap.parse_args()
    guard=[json.loads(l) for l in open(args.guard)]
    amap={r['file']:r for r in map(json.loads,open(args.assign))}
    cells={}
    for l in open(W/'cells.jsonl'):
        r=json.loads(l); cells[r['file']]=r
    out=Path(args.out); (out/'cells').mkdir(parents=True,exist_ok=True); (out/'masks').mkdir(exist_ok=True)
    m={}; skipped=[]
    for g in guard:
        if g['geom_status'] not in ('B_no_box','C_short_bbox'): continue
        c=cells.get(g['file']); a=amap.get(g['file'])
        if not c or not a or a['status']!='assigned_mutual': skipped.append(g['file']); continue
        b=a['box']; x0,y0,x1,y1=b['x0'],b['y0'],b['x1'],b['y1']
        padx=max(8,0.08*(x1-x0)); pady=max(8,0.08*(y1-y0))
        x0=max(0,int(x0-padx)); y0=max(0,int(y0-pady)); x1=int(x1+padx); y1=int(y1+pady)
        page=W/'pages300'/f'{c["key"]}.jpg'
        if not page.exists(): skipped.append(g['file']); continue
        im=cv2.imread(str(page),cv2.IMREAD_GRAYSCALE)
        crop=im[y0:y1,x0:x1]
        if crop.size==0: skipped.append(g['file']); continue
        p=out/'cells'/g['file']; cv2.imwrite(str(p),crop)
        mask=(crop<200).astype(np.uint8)*255
        mp=out/'masks'/g['file']; cv2.imwrite(str(mp),mask)
        m[g['file']]={'bbox':[x0,y0,x1,y1],'cell':str(p),'mask':str(mp),'box_char':b.get('ch',''),'old_bbox':[c['x0'],c['y0'],c['x1'],c['y1']]}
    json.dump(m,open(args.map,'w'),ensure_ascii=False,indent=1)
    print(json.dumps({'repaired':len(m),'skipped':len(skipped),'skipped_sample':skipped[:10]},ensure_ascii=False,indent=1))

if __name__=='__main__': main()
