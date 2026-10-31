"""60 synthetic-only chars (no C real sample): WenKai input + A/B/C GAN outputs."""
from __future__ import annotations
import random, gc
from pathlib import Path
import numpy as np, torch
from PIL import Image, ImageDraw, ImageFont
from importlib.machinery import SourceFileLoader
ROOT=Path(__file__).resolve().parents[1]
ev=SourceFileLoader('ev',str(ROOT/'scripts/82_eval_c.py')).load_module()
torch.set_num_threads(1)
S=112; M=150
font=ImageFont.truetype(str(ROOT/'data/base/LXGWWenKai-Regular.ttf'),13)
wk=ImageFont.truetype(str(ROOT/'data/base/LXGWWenKai-Regular.ttf'),230)
chosen={__import__('json').loads(l)['label'] for l in open(ROOT/'work-c/chosen.jsonl')}
pool=[chr(c) for c in range(0x4E00,0xA000) if chr(c) not in chosen]
rng=random.Random(20261031); sel=rng.sample(pool,60)
def img(a): return np.clip((a+1)*127.5,0,255).astype(np.uint8)
def ximg(ch):
    im=Image.new('L',(256,256),0); ImageDraw.Draw(im).text((128,225),ch,fill=255,font=wk,anchor='ms')
    m=np.array(im)>127; ys,xs=np.nonzero(m)
    if not len(ys): return np.zeros((256,256),np.float32)-1
    cr=im.crop((xs.min(),ys.min(),xs.max()+1,ys.max()+1)); w,h=cr.size; sc=min(220/w,220/h)
    cr=cr.resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.LANCZOS)
    out=Image.new('L',(256,256),0); out.paste(cr,((256-cr.width)//2,(256-cr.height)//2))
    return np.array(out,np.float32)/127.5-1.0
X=[ximg(c) for c in sel]
rows=[('A GAN ep090',ROOT/'work/ckpt/m2wt_ep090.pt'),('B GAN ep080',ROOT/'work-b/ckpt/b_ep080.pt'),
      ('上版 C best',ROOT/'work-c/ckpt/c_best.pt'),('上版 C ep034',ROOT/'work-c/ckpt/c_ep034_v120.pt')]
rows += [(f'本次 ep{e:03d}',ROOT/f'work-c/ckpt/v1.2.1/c_ep{e:03d}.pt') for e in range(10,91,10)]
vals={}
for name,p in rows:
    print('load',name,p.name,flush=True); G=ev.load_gan(str(p)); out=[]
    with torch.no_grad():
        for i in range(len(sel)):
            xin=np.repeat(X[i][None][None],3,axis=1).astype(np.float32)
            out.append(G(torch.tensor(xin)).cpu().numpy()[0,0])
    vals[name]=out; del G; gc.collect()
for sheet in range(3):
    W=M+20*S; H=(2+len(rows))*S
    im=Image.new('L',(W,H),255); dr=ImageDraw.Draw(im)
    labels=['文楷输入']+[r[0] for r in rows]
    for r,lab in enumerate(labels): dr.text((4,(r+1)*S+44),lab,font=font,fill=0)
    for j in range(20):
        k=sheet*20+j
        dr.text((M+j*S+S//2,3),sel[k],font=font,fill=0,anchor='ma')
        im.paste(Image.fromarray(img(X[k])).resize((S,S)),(M+j*S,S))
        for r,(lab,_) in enumerate(rows,1):
            im.paste(Image.fromarray(img(vals[lab][k])).resize((S,S)),(M+j*S,(r+1)*S))
    im.save(ROOT/f'work-c/preview/synth_compare_{sheet+1}.png')
    print('sheet',sheet+1,''.join(sel[sheet*20:(sheet+1)*20]))
