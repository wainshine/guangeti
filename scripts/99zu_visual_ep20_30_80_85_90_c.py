"""Visual-only ep20/ep30/ep80/ep85/ep90 comparison; no metrics, no ranking."""
import sys, json, importlib.util, numpy as np, torch
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
sys.path.insert(0,str(ROOT/'scripts'))
import generate_lib as gl
spec=importlib.util.spec_from_file_location('gan',ROOT/'scripts/21_train_gan.py'); gan=importlib.util.module_from_spec(spec); spec.loader.exec_module(gan)
font_path=ROOT/'data/base/LXGWWenKai-Regular.ttf'; S=256; D=100
font=ImageFont.truetype(str(font_path),S); small=ImageFont.truetype(str(font_path),11)
# real set
d=np.load(W/'pairs_holdout.npz',allow_pickle=True); chars=[str(c) for c in d['chars']]
idx=np.linspace(0,len(chars)-1,16).round().astype(int).tolist()
real_chars=[chars[i] for i in idx]; real_Y=d['Y'][idx]>127; real_X=d['X'][idx]
# no-real common set
no_chars=list('们她吧吗呢啊嗯谁您咱咋喵咩嗨喂哟')
ckpts=[('v121',W/'ckpt/v1.2.1/c_ep090.pt'),('ep20',W/'ckpt/v1.3/c_ep020.pt'),('ep30',W/'ckpt/v1.3/c_ep030.pt'),('ep80',W/'ckpt/v1.3/c_ep080.pt'),('ep85',W/'ckpt/v1.3/c_ep085.pt'),('ep90',W/'ckpt/v1.3/c_ep090.pt')]
def run(chars, Xraw):
 X=torch.from_numpy((Xraw.astype(np.float32)/127.5-1)[:,None].repeat(3,1)).float(); outs={}
 for name,p in ckpts:
  ck=torch.load(p,map_location='cpu'); G=gan.Generator(); G.load_state_dict(ck['G']); G.eval()
  with torch.no_grad(): outs[name]=G(X).numpy()[:,0]
 return outs
def draw(chars, input_raw, outs, realY, title, suffix):
 left=54; top=24; ncol=len(chars); nrow=1+len(ckpts)+(1 if realY is not None else 0)
 im=Image.new('RGB',(left+ncol*D, top+nrow*(D+22)+60),(255,255,255)); dr=ImageDraw.Draw(im)
 def put(a,x,y): im.paste(Image.fromarray(np.clip((a+1)*127.5,0,255).astype(np.uint8)).convert('L').resize((D,D)),(x,y))
 for j,c in enumerate(chars): dr.text((left+j*D+D//2-8,3),c,font=small,fill='black')
 for j,a in enumerate(input_raw): put(a.astype(np.float32)/127.5-1,left+j*D,top)
 dr.text((2,top+D//2-6),'input',font=small,fill='black')
 for r,(name,p) in enumerate(ckpts):
  y=top+(r+1)*(D+22)
  for j in range(ncol): put(outs[name][j],left+j*D,y)
  dr.text((2,y+D//2-6),name,font=small,fill='black')
 if realY is not None:
  y=top+(len(ckpts)+1)*(D+22)
  for j in range(ncol): put(realY[j].astype(np.float32)*2-1,left+j*D,y)
  dr.text((2,y+D//2-6),'real',font=small,fill='black')
 dr.text((left,top+nrow*(D+22)+16),title,font=small,fill='black')
 out=W/'preview'/suffix; im.save(out); print(out,im.size)
outs_real=run(real_chars, real_X)
draw(real_chars, real_X, outs_real, real_Y, 'real holdout chars — explicit epoch snapshots; no Dice shown', 'v13_ep20_30_80_85_90_real.png')
outs_no=run(no_chars, np.stack([gl.render_base(font,c,S) for c in no_chars]))
draw(no_chars, np.stack([gl.render_base(font,c,S) for c in no_chars]), outs_no, None, 'NO REAL TARGET — 16 common-ish chars absent from C real pool; visual only', 'v13_ep20_30_80_85_90_no_real.png')
