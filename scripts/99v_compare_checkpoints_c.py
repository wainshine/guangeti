"""3 x 20-character visual comparison across checkpoints.

Rows: real target, previous v1.2.0 ep030, new ep010/020/030/040.
"""
from __future__ import annotations
import json, random
from pathlib import Path
import numpy as np, torch
from PIL import Image, ImageDraw, ImageFont
from importlib.machinery import SourceFileLoader

ROOT=Path(__file__).resolve().parents[1]
ev=SourceFileLoader('ev',str(ROOT/'scripts/82_eval_c.py')).load_module()
torch.set_num_threads(1)
S=112
font=ImageFont.truetype(str(ROOT/'data/base/LXGWWenKai-Regular.ttf'),14)
d=np.load(ROOT/'work-c/pairs_clean.npz',allow_pickle=True)
X,Y,chars=d['X'],d['Y'],[str(c) for c in d['chars']]
X=X.astype(np.float32)/127.5-1.0; Y=Y.astype(np.float32)/127.5-1.0
rng=random.Random(20261030)
sel=rng.sample(range(len(chars)),60)
models=[('上版 ep030',ROOT/'work-c/ckpt/c_ep030.pt'),
        ('本次 ep010',ROOT/'work-c/ckpt/v1.2.1/c_ep010.pt'),
        ('本次 ep020',ROOT/'work-c/ckpt/v1.2.1/c_ep020.pt'),
        ('本次 ep030',ROOT/'work-c/ckpt/v1.2.1/c_ep030.pt'),
        ('本次 ep040',ROOT/'work-c/ckpt/v1.2.1/c_ep040.pt')]
Gs=[ev.load_gan(str(p)) for _,p in models]
def img(a):
    return np.clip((a+1)*127.5,0,255).astype(np.uint8)
for sheet in range(3):
    ids=sel[sheet*20:(sheet+1)*20]
    M=96; W=M+20*S; H=7*S
    out=Image.new('L',(W,H),255); dr=ImageDraw.Draw(out)
    rows=['真迹','上版 ep030','本次 ep010','本次 ep020','本次 ep030','本次 ep040']
    for r,lab in enumerate(rows):
        dr.text((4,(r+1)*S+44),lab,font=font,fill=0)
    for j,i in enumerate(ids):
        dr.text((M+j*S+S//2,3),chars[i],font=font,fill=0,anchor='ma')
        out.paste(Image.fromarray(img(Y[i])).resize((S,S)),(M+j*S,S))
        for k,G in enumerate(Gs):
            with torch.no_grad():
                xin=np.repeat(X[i:i+1][:,None],3,axis=1).astype(np.float32)
                g=G(torch.tensor(xin).to(next(G.parameters()).device)).cpu().numpy()[0,0]
            out.paste(Image.fromarray(img(g)).resize((S,S)),(M+j*S,(k+2)*S))
    out.save(ROOT/f'work-c/preview/compare_{sheet+1}.png')
    print('sheet',sheet+1,'chars',''.join(chars[i] for i in ids))
