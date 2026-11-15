#!/usr/bin/env python3
"""v1.4 ep snapshot comparison in the old 99zm/99zu 16-char layout."""
import importlib.util, json, sys
from pathlib import Path
import numpy as np, torch
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]; W=ROOT/'work-c'
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('gan',ROOT/'scripts/21_train_gan.py'); gan=importlib.util.module_from_spec(spec); spec.loader.exec_module(gan)
torch.set_num_threads(1)
d=np.load(W/'pairs_holdout.npz',allow_pickle=True); chars=[str(c) for c in d['chars']]
idx=np.linspace(0,len(chars)-1,16).round().astype(int).tolist()
X=torch.from_numpy(d['X'][idx].astype(np.float32)/127.5-1)[:,None].repeat(1,3,1,1)
Y=d['Y'][idx]>127
ckpts=[('v13',W/'ckpt/v1.3/c_ep090.pt')]+[(f'ep{e:03d}',W/f'ckpt/v1.4/c_ep{e:03d}.pt') for e in (10,20,30,40)]+[('ep049',W/'ckpt/v1.4/c.pt')]
outs={}
for name,p in ckpts:
 ck=torch.load(p,map_location='cpu'); G=gan.Generator(); G.load_state_dict(ck['G']); G.eval()
 with torch.no_grad(): outs[name]=G(X).numpy()[:,0]
 del G
S=100; left=62; top=26; ncol=len(idx); nrow=2+len(ckpts)
im=Image.new('RGB',(left+ncol*S,top+nrow*(S+22)+130),'white'); dr=ImageDraw.Draw(im)
font=ImageFont.truetype(str(ROOT/'data/base/LXGWWenKai-Regular.ttf'),14); small=ImageFont.truetype(str(ROOT/'data/base/LXGWWenKai-Regular.ttf'),11)
def put(a,x,y): im.paste(Image.fromarray(np.clip((a+1)*127.5,0,255).astype(np.uint8)).convert('L').resize((S,S)),(x,y))
for j,i in enumerate(idx): dr.text((left+j*S+S//2-8,4),chars[i],font=font,fill='black')
for j,i in enumerate(idx): put(d['X'][i].astype(np.float32)/127.5-1,left+j*S,top)
dr.text((2,top+S//2-6),'input',font=small,fill='black')
for r,(name,p) in enumerate(ckpts):
 y=top+(r+1)*(S+22)
 for j in range(ncol): put(outs[name][j],left+j*S,y)
 dr.text((2,y+S//2-6),name,font=small,fill='black')
y=top+(len(ckpts)+1)*(S+22)
for j in range(ncol): put(Y[j].astype(np.float32)*2-1,left+j*S,y)
dr.text((2,y+S//2-6),'real',font=small,fill='black')
yy=y+S+30
vals={'v13':'ep090 valDice 0.361 (v1.3 log)','ep010':'ep010 valDice 0.453','ep020':'ep020 valDice 0.480 (best)','ep030':'ep030 valDice 0.477','ep040':'ep040 valDice 0.466','ep049':'ep049 valDice 0.452 (stop)'}
for k,(name,_) in enumerate(ckpts): dr.text((left,yy+k*18),vals[name],font=small,fill='black')
out=W/'preview/v14_ep_compare.png'; im.save(out)
json.dump({'chars':[chars[i] for i in idx],'rows':vals},open(W/'preview/v14_ep_metrics.json','w'),ensure_ascii=False,indent=1)
print('saved',out,im.size)
