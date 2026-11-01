"""G1: read-only geometry guard audit for 99zf's 128 cells.

Classifies each cell as:
  A_normal, B_no_box, C_short_bbox, D_center_drift, E_multi_box
No labels, masks or fonts are modified.
"""
from __future__ import annotations
import argparse, json, collections, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--report',default=str(W/'preview/99zf_report.json'))
    ap.add_argument('--boxes',default=str(W/'preview/99zf_charboxes.json'))
    ap.add_argument('--cells',default=str(W/'cells.jsonl'))
    ap.add_argument('--out',default=str(W/'preview/geom_guard.jsonl'))
    ap.add_argument('--summary',default=str(W/'preview/geom_guard_summary.json'))
    args=ap.parse_args()
    cells={}
    for l in open(args.cells):
        r=json.loads(l); cells[r['file']]=r
    boxes=json.load(open(args.boxes))
    # median cell height per line
    line_h=collections.defaultdict(list)
    for r in cells.values(): line_h[(r['key'],r['li'])].append(r['h'])
    line_med={k:statistics.median(v) for k,v in line_h.items()}
    report=json.load(open(args.report)); out=[]; counts=collections.Counter()
    for r in report:
        c=cells.get(r['file'])
        if not c:
            out.append({**r,'geom_status':'no_cell'}); counts['no_cell']+=1; continue
        key=c['key']; x0,y0,x1,y1=c['x0'],c['y0'],c['x1'],c['y1']; cx,cy=(x0+x1)/2,(y0+y1)/2
        # boxes in this line band (lin_xyxy + 20 px)
        lx0,ly0,lx1,ly1=c['lin_xyxy']; pad=20
        cand=[]
        for b in boxes.get(key,[]):
            bx=(b['x0']+b['x1'])/2; by=(b['y0']+b['y1'])/2
            if lx0-pad<=bx<=lx1+pad and ly0-pad<=by<=ly1+pad: cand.append(b)
        inside=[]
        for b in cand:
            bx=(b['x0']+b['x1'])/2; by=(b['y0']+b['y1'])/2
            if x0<=bx<=x1 and y0<=by<=y1: inside.append(b)
        def dist(b):
            bx=(b['x0']+b['x1'])/2; by=(b['y0']+b['y1'])/2
            dx=max(x0-bx,0,bx-x1); dy=max(y0-by,0,by-y1)
            return (dx*dx+dy*dy)**0.5
        near=min(cand,key=dist) if cand else None
        nd=dist(near) if near else None
        cp=max(1.0,float(c.get('cpitch') or c['h']))
        hr=c['h']/max(1.0,line_med.get((key,c['li']),c['h']))
        dy=( (near['y0']+near['y1'])/2 - cy)/cp if near else None
        if not cand: st='B_no_box'
        elif len(inside)>1: st='E_multi_box'
        elif not inside: st='B_no_box'
        elif hr<0.75: st='C_short_bbox'
        elif abs(dy or 0)>0.5: st='D_center_drift'
        else: st='A_normal'
        counts[st]+=1
        out.append({**r,'li':c['li'],'sub':c['sub'],'geom_status':st,'n_boxes_line':len(cand),'n_inside':len(inside),
                    'nearest_dist_px':round(nd,1) if nd is not None else None,
                    'nearest_dist_cp':round(nd/cp,3) if nd is not None else None,
                    'h_ratio':round(hr,3),'dy_cp':round(dy,3) if dy is not None else None,
                    'cell_bbox':[x0,y0,x1,y1],'box_near':near,'offset_suspect':bool(hr>=0.75 and abs(dy or 0)>0.3)})
    with open(args.out,'w') as f:
        for r in out: f.write(json.dumps(r,ensure_ascii=False)+'\n')
    summary={'n':len(out),'counts':dict(counts),'offset_suspect':sum(1 for r in out if r.get('offset_suspect'))}
    json.dump(summary,open(args.summary,'w'),ensure_ascii=False,indent=1)
    print(json.dumps(summary,ensure_ascii=False,indent=1))
if __name__=='__main__': main()
