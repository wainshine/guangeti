"""Run local Ollama PaddleOCR-VL on pre-extracted cell crops (no labels in prompt)."""
from __future__ import annotations
import argparse, base64, json, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import urllib.request
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
PROMPT='Read the single Chinese character in the center of the image. Return only that character, or ? if unreadable.'
CJK=re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')

def call(p,model,timeout=300):
 b=base64.b64encode(Path(p).read_bytes()).decode()
 body={'model':model,'stream':False,'messages':[{'role':'user','content':PROMPT,'images':[b]}]}
 req=urllib.request.Request('http://localhost:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=timeout) as r: d=json.load(r)
 txt=(d.get('message') or {}).get('content','').strip()
 m=CJK.search(txt); ch=m.group(0) if m else ('?' if txt else '')
 return ch,txt,d

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--kind',choices=['calib28','oracle100'],required=True)
 ap.add_argument('--out',default=''); ap.add_argument('--workers',type=int,default=2)
 ap.add_argument('--model',default='enaval/PaddleOCR-VL-1.6-0.9B-Backup')
 args=ap.parse_args()
 rows=json.load(open(W/'preview'/f'{args.kind}_key.json'))['cells']
 out=Path(args.out or (W/'preview'/f'{args.kind}_paddleocr_vl.jsonl')); done=set()
 if out.exists():
  for l in open(out): done.add(json.loads(l)['sid'])
 todo=[r for r in rows if r['sid'] not in done]
 print('todo',len(todo),'done',len(done),flush=True)
 def work(r):
  p=W/'vlm_crops'/args.kind/f'{r["sid"]}.png'
  if not p.exists(): return {**r,'vlm_char':'','error':'no_crop'}
  try:
   ch,raw,d=call(p,args.model)
   return {**r,'vlm_char':ch,'raw':raw,'source':'ollama-paddleocr-vl','model':args.model,
           'prompt':PROMPT,'usage':{k:d.get(k) for k in ('prompt_eval_count','eval_count','total_duration')}}
  except Exception as e: return {**r,'error':str(e)[:300]}
 with ThreadPoolExecutor(max_workers=args.workers) as ex, open(out,'a') as f:
  for i,rec in enumerate(ex.map(work,todo)):
   f.write(json.dumps(rec,ensure_ascii=False)+'\n'); f.flush()
   if i and i%10==0: print('done',i,flush=True)
 print('->',out)

if __name__=='__main__': main()
