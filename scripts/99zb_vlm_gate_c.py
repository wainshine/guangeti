"""Run the pinned vision model on per-cell grayscale page crops.

No label is included in the prompt.  Crops are from pages150, not binary masks.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, os, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
PROMPT="""You are reading exactly one character from a Ming dynasty manuscript.
The image is a grayscale page crop centered on that character; neighbouring ink may appear at the edges.
Return ONLY JSON:
{"char":"<one Chinese character, or ? if unreadable>","confidence":0.0-1.0,"note":"<brief>"}
Read the ink at the center. Do not use any expected label. Do not output anything except the JSON object."""

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def call(b64,base,key,model,detail,timeout=90):
 body={"model":model,"messages":[{"role":"user","content":[
  {"type":"text","text":PROMPT},
  {"type":"image_url","image_url":{"url":"data:image/png;base64,"+b64,"detail":detail}}]}],
  "temperature":0,"max_tokens":80,"thinking":{"type":"disabled"}}
 req=urllib.request.Request(base.rstrip('/')+'/chat/completions',data=json.dumps(body).encode(),
  headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as r: d=json.load(r)
 txt=d['choices'][0]['message']['content'].strip(); s=txt[txt.find('{'):txt.rfind('}')+1]
 return json.loads(s),d.get('usage')

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--kind',choices=['calib28','oracle100'],required=True)
 ap.add_argument('--out',default=''); ap.add_argument('--limit',type=int,default=0); ap.add_argument('--workers',type=int,default=4)
 ap.add_argument('--detail',default='high'); ap.add_argument('--crop-dir',default=str(W/'vlm_crops'))
 args=ap.parse_args()
 key=os.environ.get('VISION_API_KEY',''); base=os.environ.get('VISION_BASE_URL',''); model=os.environ.get('VISION_MODEL','')
 if not(key and base and model): raise SystemExit('set VISION_API_KEY / VISION_BASE_URL / VISION_MODEL')
 kp=W/'preview'/f'{args.kind}_key.json'; rows=json.load(open(kp))['cells']
 if args.limit: rows=rows[:args.limit]
 cells={}
 for l in open(W/'cells.jsonl'):
  r=json.loads(l); cells[r['file']]=r
 cropdir=Path(args.crop_dir)/args.kind; cropdir.mkdir(parents=True,exist_ok=True)
 todo=[]
 for r in rows:
  r=dict(r); c=cells.get(r['file'])
  if not c or not (W/'pages150'/f'{r["key"]}.jpg').exists():
   r['skip_reason']='no_cell_or_page'; todo.append(r); continue
  im=Image.open(W/'pages150'/f'{r["key"]}.jpg').convert('L')
  x0,y0,x1,y1=[v/2 for v in (c['x0'],c['y0'],c['x1'],c['y1'])]
  mx=0.28*(x1-x0); my=0.28*(y1-y0)
  box=(max(0,int(x0-mx)),max(0,int(y0-my)),min(im.width,int(x1+mx)),min(im.height,int(y1+my)))
  crop=im.crop(box); sc=min(2.0,384/max(1,min(crop.width,crop.height)))
  if sc>1: crop=crop.resize((int(crop.width*sc),int(crop.height*sc)),Image.LANCZOS)
  p=cropdir/f'{r["sid"]}.png'; crop.save(p); r['crop']=str(p); r['crop_sha256']=sha(p); todo.append(r)
 out=Path(args.out or (W/'preview'/f'{args.kind}_vlm.jsonl')); done=set()
 if out.exists():
  for l in open(out): done.add(json.loads(l)['sid'])
 todo=[r for r in todo if r['sid'] not in done]
 print('todo',len(todo),'done',len(done),flush=True)
 lock=__import__('threading').Lock()
 def work(r):
  if r.get('skip_reason'): return {**r,'vlm_char':'','error':r['skip_reason']}
  b64=base64.b64encode(Path(r['crop']).read_bytes()).decode()
  try:
   v,u=call(b64,base,key,model,args.detail)
   return {**r,'vlm_char':v.get('char',''),'confidence':v.get('confidence'),'note':v.get('note',''),'usage':u,
           'model':model,'detail':args.detail}
  except Exception as e: return {**r,'error':str(e)[:200]}
 with ThreadPoolExecutor(max_workers=args.workers) as ex, open(out,'a') as f:
  for i,rec in enumerate(ex.map(work,todo)):
   f.write(json.dumps(rec,ensure_ascii=False)+'\n'); f.flush()
   if i and i%10==0: print('done',i,flush=True)
 print('->',out)

if __name__=='__main__': main()
