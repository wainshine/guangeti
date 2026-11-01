"""No-real-target comparison with the same row structure as the real sheet.

Rows: input / v1.2.1 / ep10..ep80 / best / real N/A (no real glyph exists).
All generation is CPU, matching 77_generate_c.py / 82_eval_c.py.
"""
import sys, json, importlib.util, numpy as np, torch
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
sys.path.insert(0,str(ROOT/'scripts'))
import generate_lib as gl
spec=importlib.util.spec_from_file_location('gan',ROOT/'scripts/21_train_gan.py'); gan=importlib.util.module_from_spec(spec); spec.loader.exec_module(gan)
COMMON='们她吧吗呢啊嗯谁您咱咋喵咩嗨喂哟'
chars=list(COMMON)
real=set(json.load(open(W/'real_glyph_sources.json')))
assert not any(c in real for c in chars), [c for c in chars if c in real]
S=256; D=100; font_path=ROOT/'data/base/LXGWWenKai-Regular.ttf'; font=ImageFont.truetype(str(font_path),S)
base=[gl.render_base(font,c,S) for c in chars]
X=torch.from_numpy((np.stack(base).astype(np.float32)/127.5-1)[:,None].repeat(3,1)).float()
ckpts=[('v121',W/'ckpt/v1.2.1/c_ep090.pt')]+[(f'ep{e}',W/f'ckpt/v1.3/c_ep{e:03d}.pt') for e in (10,20,30,40,50,60,70,80)]
if (W/'ckpt/v1.3/c_best.pt').exists(): ckpts.append(('best',W/'ckpt/v1.3/c_best.pt'))
outs={}; metrics=[]
for name,p in ckpts:
 ck=torch.load(p,map_location='cpu'); G=gan.Generator(); G.load_state_dict(ck['G']); G.eval()
 with torch.no_grad(): y=G(X).numpy()[:,0]
 outs[name]=y
 ink=float((y>0).sum()/max(1,(np.stack(base)>127).sum()))
 metrics.append({'name':name,'epoch':int(ck.get('epoch',0)),'ink_vs_input':ink})
 print(name,metrics[-1],flush=True)
left=54; top=24; ncol=len(chars); nrow=1+len(ckpts)+1  # input + checkpoints + real N/A
im=Image.new('RGB',(left+ncol*D, top+nrow*(D+22)+230),(255,255,255)); dr=ImageDraw.Draw(im)
small=ImageFont.truetype(str(font_path),11)
def put(a,x,y): im.paste(Image.fromarray(np.clip((a+1)*127.5,0,255).astype(np.uint8)).convert('L').resize((D,D)),(x,y))
for j,c in enumerate(chars): dr.text((left+j*D+D//2-8,3),c,font=small,fill='black')
for j,a in enumerate(base): put(a.astype(np.float32)/127.5-1,left+j*D,top)
dr.text((2,top+D//2-6),'input',font=small,fill='black')
for r,(name,p) in enumerate(ckpts):
 y=top+(r+1)*(D+22)
 for j in range(ncol): put(outs[name][j],left+j*D,y)
 dr.text((2,y+D//2-6),name,font=small,fill='black')
# explicit no-real row, same slot as 'real'
y=top+(len(ckpts)+1)*(D+22)
for j in range(ncol):
 dr.rectangle((left+j*D,y,left+(j+1)*D-1,y+D-1),outline=(180,180,180))
 dr.text((left+j*D+20,y+D//2-8),'—',font=small,fill=(120,120,120))
dr.text((2,y+D//2-6),'real',font=small,fill='black')
yy=top+nrow*(D+22)+16
dr.text((left,yy),'NO REAL TARGET — 16 common-ish chars absent from C real-glyph pool',font=small,fill='black')
for k,m in enumerate(metrics):
 dr.text((left,yy+20+k*16),f"{m['name']:4s} ep{m['epoch']:03d}  ink_vs_input {m['ink_vs_input']:.3f}",font=small,fill='black')
out=W/'preview/v13_no_real_compare.png'; im.save(out)
json.dump({'chars':chars,'metrics':metrics,'note':'all chars absent from real_glyph_sources; no real row exists; CPU inference'},open(W/'preview/v13_no_real_metrics.json','w'),ensure_ascii=False,indent=1)
print('saved',out,im.size)
