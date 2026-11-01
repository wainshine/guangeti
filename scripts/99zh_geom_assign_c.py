"""G2 read-only: mutual-nearest cell-box assignment.

Does not modify cells/masks.  Produces a virtual assignment for 99zf to test
whether geometry alone can recover B/C cells without leaking neighbours.
"""
from __future__ import annotations
import argparse, json, collections, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--report',default=str(W/'preview/99zf_report.json'))
    ap.add_argument('--boxes',default=str(W/'preview/99zf_charboxes.json'))
    ap.add_argument('--cells',default=str(W/'cells.jsonl'))
    ap.add_argument('--out',default=str(W/'preview/geom_assign.jsonl'))
    ap.add_argument('--map',default=str(W/'preview/geom_assign_map.json'))
    ap.add_argument('--cells-arg',default='')
    args=ap.parse_args()
    cells_path=args.cells_arg or args.cells
    cells={}
    for l in open(cells_path):
        r=json.loads(l); cells[r['file']]=r
    boxes=json.load(open(args.boxes))
    report=json.load(open(args.report)); rows=[]; amap={}; counts=collections.Counter()
    # group cells by line
    byline=collections.defaultdict(list)
    for r in report:
        c=cells.get(r['file'])
        if c: byline[(c['key'],c['li'])].append((r,c))
    for (key,li), items in byline.items():
        cs=[c for _,c in items]
        cx=lambda c:(c['x0']+c['x1'])/2; cy=lambda c:(c['y0']+c['y1'])/2
        lb=cells[cs[0]['file']]['lin_xyxy']
        cand=[b for b in boxes.get(key,[]) if lb[1]-24<=(b['y0']+b['y1'])/2<=lb[3]+24 and lb[0]-24<=(b['x0']+b['x1'])/2<=lb[2]+24]
        if not cand:
            for r,c in items: rows.append({'sid':r['sid'],'file':c['file'],'status':'unassigned_no_boxes'}); counts['unassigned_no_boxes']+=1
            continue
        # nearest box for each cell; nearest cell for each box
        cell_near={}; box_near={}
        for r,c in items:
            ds=[(math.hypot(cx(c)-(b['x0']+b['x1'])/2,cy(c)-(b['y0']+b['y1'])/2),j) for j,b in enumerate(cand)]
            cell_near[c['file']]=min(ds)
        for j,b in enumerate(cand):
            bs=(b['x0']+b['x1'])/2,(b['y0']+b['y1'])/2
            ds=[(math.hypot((c['x0']+c['x1'])/2-bs[0],(c['y0']+c['y1'])/2-bs[1]),c['file']) for _,c in items]
            box_near[j]=min(ds)
        for r,c in items:
            d,j=cell_near[c['file']]; cp=max(1.0,float(c.get('cpitch') or c['h']))
            mutual=box_near[j][1]==c['file']
            if mutual and d<=0.75*cp:
                st='assigned_mutual'; amap[c['file']]={'box':cand[j],'dist_px':round(d,1)}
            elif d<=0.35*cp:
                st='assigned_unique'; amap[c['file']]={'box':cand[j],'dist_px':round(d,1)}
            else:
                st='unassigned_ambiguous'
            counts[st]+=1
            rows.append({'sid':r['sid'],'file':c['file'],'status':st,'dist_px':round(d,1),
                         'dist_cp':round(d/cp,3),'mutual':mutual,'box':cand[j],'n_boxes':len(cand)})
    with open(args.out,'w') as f:
        for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
    json.dump(amap,open(args.map,'w'),ensure_ascii=False)
    print(json.dumps({'n':len(rows),'counts':dict(counts)},ensure_ascii=False,indent=1))
if __name__=='__main__': main()
