"""60-char comparison: real, A/B current, old best, old ep034, new ep010..090."""
from __future__ import annotations
import json, random, gc
from pathlib import Path
import numpy as np, torch
from PIL import Image, ImageDraw, ImageFont
from importlib.machinery import SourceFileLoader

ROOT=Path(__file__).resolve().parents[1]
ev=SourceFileLoader('ev',str(ROOT/'scripts/82_eval_c.py')).load_module()
torch.set_num_threads(1)
S=112; M=150
label_font=ImageFont.truetype(str(ROOT/'data/base/LXGWWenKai-Regular.ttf'),13)
d=np.load(ROOT/'work-c/pairs_clean.npz',allow_pickle=True)
X=d['X'].astype(np.float32)/127.5-1.0
Y=d['Y'].astype(np.float32)/127.5-1.0
chars=[str(c) for c in d['chars']]
rng=random.Random(20261030); sel=rng.sample(range(len(chars)),60)

def arrimg(a): return np.clip((a+1)*127.5,0,255).astype(np.uint8)

def fontimg(fp,ch):
    try: f=ImageFont.truetype(str(fp),230)
    except Exception: return np.zeros((256,256),np.uint8)
    im=Image.new('L',(256,256),0); ImageDraw.Draw(im).text((128,225),ch,fill=255,font=f,anchor='ms')
    m=np.array(im)>127; ys,xs=np.nonzero(m)
    if not len(ys): return np.array(im)
    crop=im.crop((xs.min(),ys.min(),xs.max()+1,ys.max()+1))
    w,h=crop.size; sc=min(220/w,220/h)
    crop=crop.resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.LANCZOS)
    out=Image.new('L',(256,256),0); out.paste(crop,((256-crop.width)//2,(256-crop.height)//2)); return np.array(out)

A=ROOT/'build/GuanGeKai-Regular.ttf'; B=ROOT/'build/GuanGeKai-B-Regular.ttf'
out=[]
for i in sel:
    out.append({'真迹':arrimg(Y[i]),'A 当前 v1.7.2':fontimg(A,chars[i]),'B 当前 v1.2.4':fontimg(B,chars[i])})
models=[('上版 best',ROOT/'work-c/ckpt/c_best.pt'),('上版 v1.2.0 ep034',ROOT/'work-c/ckpt/c_ep034_v120.pt')]
models += [(f'本次 ep{e:03d}',ROOT/f'work-c/ckpt/v1.2.1/c_ep{e:03d}.pt') for e in range(10,91,10)]
for name,p in models:
    print('load',name,p.name,flush=True)
    G=ev.load_gan(str(p))
    vals=[]
    with torch.no_grad():
        for j,i in enumerate(sel):
            xin=np.repeat(X[i:i+1][:,None],3,axis=1).astype(np.float32)
            vals.append(G(torch.tensor(xin)).cpu().numpy()[0,0])
    for j,v in enumerate(vals): out[j][name]=arrimg(v)
    del G; gc.collect()
rows=['真迹','A 当前 v1.7.2','B 当前 v1.2.4']+[m[0] for m in models]
for sheet in range(3):
    W=M+20*S; H=(1+len(rows))*S
    im=Image.new('L',(W,H),255); dr=ImageDraw.Draw(im)
    for r,lab in enumerate(rows): dr.text((4,(r+1)*S+44),lab,font=label_font,fill=0)
    for j in range(20):
        i=sheet*20+j
        dr.text((M+j*S+S//2,3),chars[sel[i]],font=label_font,fill=0,anchor='ma')
        for r,lab in enumerate(rows):
            im.paste(Image.fromarray(out[i][lab]).resize((S,S)),(M+j*S,(r+1)*S))
    im.save(ROOT/f'work-c/preview/all_compare_{sheet+1}.png')
    print('sheet',sheet+1,''.join(chars[i] for i in sel[sheet*20:(sheet+1)*20]))
