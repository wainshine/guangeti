"""Reader-mode experiment: line image with the target cell boxed; read only that box.

Local PaddleOCR-VL via Ollama.  This tests whether target-box anchoring removes
the off-by-one correlated error, not whether the model is generally better.
"""
from __future__ import annotations
import argparse, base64, json, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
CJK=re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
PROMPT=('The rectangle marks exactly one Chinese character in this vertical line. '
        'Read ONLY the character inside the rectangle; ignore all other ink. '
        'Return ONLY JSON: {"char":"<one character>"}.')

def call(p,model,timeout=300):
    b=base64.b64encode(Path(p).read_bytes()).decode()
    body={'model':model,'stream':False,'messages':[{'role':'user','content':PROMPT,'images':[b]}]}
    req=urllib.request.Request('http://localhost:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: d=json.load(r)
    txt=(d.get('message') or {}).get('content','').strip(); m=CJK.search(txt)
    return (m.group(0) if m else '?'),txt,d

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--rows',default=str(W/'preview/geom_rescore_guarded.json'))
    ap.add_argument('--out',default=str(W/'preview/targetbox_read.jsonl'))
    ap.add_argument('--cropdir',default=str(W/'preview/targetbox_crops'))
    ap.add_argument('--model',default='enaval/PaddleOCR-VL-1.6-0.9B-Backup')
    ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--map',default='')
    args=ap.parse_args()
    rows=[r for r in json.load(open(args.rows)) if r.get('route') in ('human','human_label_fix') and r.get('truth')]
    cells={}
    for l in open(W/'cells.jsonl'):
        r=json.loads(l); cells[r['file']]=r
    outdir=Path(args.cropdir); outdir.mkdir(parents=True,exist_ok=True)
    gmap=json.load(open(args.map)) if args.map else {}
    out=Path(args.out); done=set()
    if out.exists():
        for l in open(out): done.add(json.loads(l)['sid'])
    todo=[r for r in rows if r['sid'] not in done]
    print('todo',len(todo),'selected',len(rows),flush=True)
    def work(r):
        c=cells.get(r['file'])
        if not c: return {**r,'target_char':'','error':'no_cell'}
        p=W/'pages300'/f'{c["key"]}.jpg'
        if not p.exists(): return {**r,'target_char':'','error':'no_page'}
        im=Image.open(p).convert('L'); lx=c['lin_xyxy']; m=20
        ox,oy=max(0,lx[0]-m),max(0,lx[1]-m)
        crop=im.crop((ox,oy,min(im.width,lx[2]+m),min(im.height,lx[3]+m))).convert('L')
        dr=ImageDraw.Draw(crop)
        bx0,by0,bx1,by1=(gmap.get(r['file'],{}).get('bbox') or [c['x0'],c['y0'],c['x1'],c['y1']])
        dr.rectangle((bx0-ox,by0-oy,bx1-ox,by1-oy),outline=255,width=5)
        w,h=crop.size; sc=min(1.0,2400/max(w,h))
        if sc<1: crop=crop.resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.LANCZOS)
        cp=outdir/f'{r["sid"].replace(":","_")}.png'; crop.save(cp)
        try:
            ch,raw,d=call(cp,args.model)
            return {**r,'target_char':ch,'raw':raw,'crop':str(cp),'model':args.model,
                    'usage':{k:d.get(k) for k in ('prompt_eval_count','eval_count')}}
        except Exception as e: return {**r,'target_char':'','error':str(e)[:300]}
    with ThreadPoolExecutor(max_workers=args.workers) as ex, open(out,'a') as f:
        for i,rec in enumerate(ex.map(work,todo)):
            f.write(json.dumps(rec,ensure_ascii=False)+'\n'); f.flush()
            if i and i%10==0: print('done',i,flush=True)
    print('->',out)

if __name__=='__main__': main()
