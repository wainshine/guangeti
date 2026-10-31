"""60-char comparison using real A/B GAN outputs (not font renders)."""
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
d=np.load(ROOT/'work-c/pairs_clean.npz',allow_pickle=True)
X=d['X'].astype(np.float32)/127.5-1.0; Y=d['Y'].astype(np.float32)/127.5-1.0
chars=[str(c) for c in d['chars']]; rng=random.Random(20261030); sel=rng.sample(range(len(chars)),60)
def img(a): return np.clip((a+1)*127.5,0,255).astype(np.uint8)
def gen(path):
    G=ev.load_gan(str(path)); out=[]
    with torch.no_grad():
        for i in sel:
            xin=np.repeat(X[i:i+1][:,None],3,axis=1).astype(np.float32)
            out.append(G(torch.tensor(xin)).cpu().numpy()[0,0])
    del G; gc.collect(); return out
rows=[('真迹',None),('A GAN ep090',ROOT/'work/ckpt/m2wt_ep090.pt'),
      ('B GAN ep080',ROOT/'work-b/ckpt/b_ep080.pt'),
      ('上版 C best',ROOT/'work-c/ckpt/c_best.pt'),
      ('上版 C ep034',ROOT/'work-c/ckpt/c_ep034_v120.pt')]
rows += [(f'本次 ep{e:03d}',ROOT/f'work-c/ckpt/v1.2.1/c_ep{e:03d}.pt') for e in range(10,91,10)]
vals={}
for name,p in rows:
    if p is None: continue
    print('load',name,p.name,flush=True); vals[name]=gen(p)
for sheet in range(3):
    W=M+20*S; H=(1+len(rows))*S
    im=Image.new('L',(W,H),255); dr=ImageDraw.Draw(im)
    for r,(lab,_) in enumerate(rows): dr.text((4,(r+1)*S+44),lab,font=font,fill=0)
    for j in range(20):
        k=sheet*20+j; i=sel[k]
        dr.text((M+j*S+S//2,3),chars[i],font=font,fill=0,anchor='ma')
        im.paste(Image.fromarray(img(Y[i])).resize((S,S)),(M+j*S,S))
        for r,(lab,_) in enumerate(rows[1:],1):
            im.paste(Image.fromarray(img(vals[lab][k])).resize((S,S)),(M+j*S,(r+1)*S))
    im.save(ROOT/f'work-c/preview/abgan_compare_{sheet+1}.png')
    print('sheet',sheet+1,''.join(chars[i] for i in sel[sheet*20:(sheet+1)*20]))
