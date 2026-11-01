"""Rescore 99zf with G2 assignment + frozen label/box guard (read-only).

Production guard is strict: label_current must equal the assigned box character,
otherwise conflict -> human.  Variant equivalence is reported separately, never
auto-passes.  correct_vlm/correct_verified are recomputed, never inherited.
"""
from __future__ import annotations
import argparse, json, collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
from importlib.machinery import SourceFileLoader
zf=SourceFileLoader('zf',str(ROOT/'scripts/99zf_dp_align_gate_c.py')).load_module()
VARIANTS={
 '來':'来','来':'來','劍':'剑','剑':'劍','黃':'黄','黄':'黃','長':'长','长':'長',
 '爲':'为','为':'爲','體':'体','体':'體','國':'国','国':'國','萬':'万','万':'萬',
 '與':'与','与':'與','學':'学','学':'學','書':'书','书':'書','車':'车','车':'車',
 '廣':'广','广':'廣','養':'养','养':'養','龍':'龙','龙':'龍','門':'门','门':'門',
}
def norm(ch): return VARIANTS.get(ch,ch)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default=str(W/'preview/geom_rescore_guarded.json'))
    ap.add_argument('--map',default=str(W/'preview/geom_assign_map.json'))
    ap.add_argument('--v5-boxes',default='')
    args=ap.parse_args()
    amap=json.load(open(args.map))
    lines={r['sid']:r for r in map(json.loads,open(W/'preview/99zf_linevlm.jsonl'))}
    boxes=json.load(open(W/'preview/99zf_charboxes.json'))
    v5boxes=json.load(open(args.v5_boxes)) if args.v5_boxes else {}
    cells={}
    for l in open(W/'cells.jsonl'):
        r=json.loads(l); cells[r['file']]=r
    report=json.load(open(W/'preview/99zf_report.json'))
    rows=[]
    for r in report:
        c=cells.get(r['file']); rec=dict(r); rec['guard_reason']=''; rec['route']='human'; rec['label_fix']=False
        rec['vlm_char']=''; rec['ocr_char']=''; rec['verified']=False; rec['conflict']=False
        rec['verified_variant']=False; rec['correct_vlm']=False; rec['correct_verified']=False
        if not c:
            rec['guard_reason']='no_cell'; rows.append(rec); continue
        if r['file'] not in amap:
            rec['guard_reason']='unassigned'; rec['conflict']=True; rows.append(rec); continue
        a=amap[r['file']]; box=a['box']; key=c['key']; lx=c['lin_xyxy']
        page=[b for b in boxes.get(key,[]) if lx[1]-24<=(b['y0']+b['y1'])/2<=lx[3]+24 and lx[0]-24<=(b['x0']+b['x1'])/2<=lx[2]+24]
        page.sort(key=lambda b:b['y0'])
        bi=next((i for i,b in enumerate(page) if all(abs(b[k]-box[k])<0.5 for k in ('x0','y0','x1','y1'))),None)
        vlmr=lines.get(r['sid'],{}); chars=vlmr.get('chars',[])
        vlm=''
        if bi is not None:
            for vi,bj in zf.dp_align(chars,page):
                if bj==bi:
                    if vi is not None: vlm=chars[vi]
                    break
        label=r.get('label',''); boxch=box.get('ch',''); v5=r.get('v5','') or ''
        rec.update(vlm_char=vlm,ocr_char=boxch,v5=v5)
        # routing: label must agree with BOTH box and VLM; v5 is a veto, not an override
        rec['route']='human'
        rec['verified']=False
        rec['label_fix']=False
        if not vlm:
            rec['guard_reason']='no_vlm_char'
        elif label != boxch:
            if vlm == boxch and (not v5 or v5 == boxch):
                rec['route']='human_label_fix'; rec['label_fix']=True
                rec['guard_reason']='label_fix_double_witness_human'
            else:
                rec['guard_reason']='label_box_mismatch'
        elif label != vlm:
            rec['guard_reason']='label_vlm_mismatch'
        elif v5 and v5 != label:
            rec['guard_reason']='v5_conflict'
        else:
            rec['route']='auto_strict'; rec['verified']=True
        # variant-normalized only for reporting; never auto-pass
        rec['verified_variant']=bool(vlm and norm(vlm)==norm(label)==norm(boxch) and (not v5 or norm(v5)==norm(label)))
        rec['conflict']=not rec['verified']
        if 'truth' in r:
            rec['correct_vlm']=bool(vlm) and vlm==r['truth']
            rec['correct_verified']=rec['verified'] and vlm==r['truth']
        rows.append(rec)
    json.dump(rows,open(args.out,'w'),ensure_ascii=False,indent=1)
    ver=[r for r in rows if r['verified'] and 'truth' in r]
    ok=[r for r in ver if r['correct_verified']]
    vacc=[r for r in rows if r.get('verified_variant') and 'truth' in r]
    vok=[r for r in vacc if r['vlm_char']==r['truth']]
    scored=[r for r in rows if 'truth' in r]
    print(json.dumps({'scored':len(scored),'verified_strict':len(ver),'verified_ok':len(ok),
        'strict_precision':round(len(ok)/max(1,len(ver)),3),
        'verified_variant':len(vacc),'variant_ok':len(vok),
        'variant_precision':round(len(vok)/max(1,len(vacc)),3),
        'no_char':sum(1 for r in rows if not r.get('vlm_char')),
        'conflict':sum(1 for r in rows if r['conflict']),
        'route_counts':dict(collections.Counter(r['route'] for r in rows)),
        'label_fix':sum(1 for r in rows if r.get('label_fix')),
        'guard_reasons':dict(collections.Counter(r['guard_reason'] for r in rows)),
        'end2end_strict':round(len(ok)/max(1,len(scored)),3)},ensure_ascii=False,indent=1))
if __name__=='__main__': main()
