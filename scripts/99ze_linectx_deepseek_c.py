"""DeepSeek Flash line-context transcription on 300 dpi line crops.

Prompt sees the full line only; no labels.  Output is the character sequence;
evaluation against content truth happens in a separate step.
"""
from __future__ import annotations
import argparse, base64, json, os, re, hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
PROMPT='''Transcribe the vertical Chinese text line in this image from top to bottom.
Return only the Chinese characters in order, no punctuation, no spaces, no explanation.
Include every character exactly once.'''
CJK=re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')

def call(p,base,key,model,timeout=300):
 im=Image.open(p).convert('L'); w,h=im.size
 sc=min(1.0,2400/max(w,h))
 if sc<1: im=im.resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.LANCZOS)
 tmp=Path('/tmp')/('line_'+hashlib.sha256(str(p).encode()).hexdigest()[:10]+'.png'); im.save(tmp)
 b=base64.b64encode(tmp.read_bytes()).decode()
 body={'model':model,'temperature':0,'max_tokens':500,'thinking':{'type':'disabled'},
  'messages':[{'role':'user','content':[{'type':'text','text':PROMPT},
   {'type':'image_url','image_url':{'url':'data:image/png;base64,'+b,'detail':'high'}}]}]}
 req=urllib.request.Request(base.rstrip('/')+'/chat/completions',data=json.dumps(body).encode(),
  headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as r: d=json.load(r)
 txt=d['choices'][0]['message']['content'].strip()
 chars=CJK.findall(txt)
 return ''.join(chars),txt,d.get('usage')

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--kind',choices=['calib28','oracle100'],required=True)
 ap.add_argument('--out',default=''); ap.add_argument('--workers',type=int,default=2)
 args=ap.parse_args()
 key=os.environ.get('VISION_API_KEY',''); base=os.environ.get('VISION_BASE_URL',''); model=os.environ.get('VISION_MODEL','')
 if not(key and base and model): raise SystemExit('set VISION_API_KEY/VISION_BASE_URL/VISION_MODEL')
 rows=json.load(open(W/'preview'/f'{args.kind}_key.json'))['cells']
 cells={}
 for l in open(W/'cells.jsonl'):
  r=json.loads(l); cells[r['file']]=r
 nline={}
 for l in open(W/'cells.jsonl'):
  r=json.loads(l); nline[(r['key'],r['li'])]=nline.get((r['key'],r['li']),0)+1
 out=Path(args.out or (W/'preview'/f'{args.kind}_linectx_deepseek.jsonl')); done=set()
 if out.exists():
  for l in open(out): done.add(json.loads(l)['sid'])
 todo=[r for r in rows if r['sid'] not in done]
 print('todo',len(todo),flush=True)
 def work(r):
  c=cells.get(r['file'])
  if not c: return {**r,'chars':'','error':'no_cell'}
  sub='calib28' if args.kind=='calib28' else ''
  p=W/'vlm_crops300'/sub/f'line_{r["sid"]}.png'
  if not p.exists(): return {**r,'chars':'','error':'no_line_crop'}
  try:
   ch,raw,u=call(p,base,key,model)
   return {**r,'li':c['li'],'sub':c['sub'],'chars':ch,'raw':raw,'n_cells':nline.get((c['key'],c['li']),0),'source':'deepseek-flash-linectx','usage':u}
  except Exception as e: return {**r,'error':str(e)[:300]}
 with ThreadPoolExecutor(max_workers=args.workers) as ex, open(out,'a') as f:
  for i,rec in enumerate(ex.map(work,todo)):
   f.write(json.dumps(rec,ensure_ascii=False)+'\n'); f.flush()
   if i and i%10==0: print('done',i,flush=True)
 print('->',out)

if __name__=='__main__': main()
