"""Validate real glyph labels against all 20,992 base-font glyph shapes."""
import json, sys
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).parent))
from select_lib import norm_glyph
ROOT = Path(__file__).resolve().parents[1]
S = 48
BLOCK = (0x4E00, 0x9FFF)
font = ImageFont.truetype(str(ROOT/'data'/'base'/'LXGWWenKai-Regular.ttf'), 256)

def base_vec(ch):
    im = Image.new('L', (256,256), 0)
    ImageDraw.Draw(im).text((0, 880*256/1000), ch, font=font, fill=255, anchor='ls')
    orig = np.array(im)
    a = 255 - orig
    ys,xs = np.nonzero(orig>64)
    if len(ys)==0: return None
    x0,x1,y0,y1 = xs.min(),xs.max()+1,ys.min(),ys.max()+1
    side = max(x1-x0,y1-y0)*1.08
    cx,cy = (x0+x1)/2,(y0+y1)/2
    xa,ya,xb,yb = int(cx-side/2),int(cy-side/2),int(cx+side/2),int(cy+side/2)
    pad = max(0,-xa)+max(0,-ya)+max(0,xb-256)+max(0,yb-256)
    if pad:
        a = cv2.copyMakeBorder(a, max(0,-ya), max(0,yb-256), max(0,-xa), max(0,xb-256), cv2.BORDER_CONSTANT, value=255)
        xa,ya,xb,yb = max(0,xa),max(0,ya),min(256-0,xb),min(256,yb)
        xb=min(a.shape[1],xb); yb=min(a.shape[0],yb)
    crop = a[ya:yb, xa:xb]
    if crop.size==0: return None
    small = cv2.resize(crop,(S,S),interpolation=cv2.INTER_AREA).astype(np.float32)/255
    ink = (small < 0.55).astype(np.float32)
    return cv2.GaussianBlur(ink,(0,0),1.0).ravel()

chars = [chr(c) for c in range(BLOCK[0],BLOCK[1]+1)]
B = np.zeros((len(chars), S*S), np.float32)
for i,ch in enumerate(chars):
    v = base_vec(ch)
    if v is not None: B[i]=v
B /= (np.linalg.norm(B,axis=1,keepdims=True)+1e-6)

chosen = [json.loads(l) for l in open(ROOT/'work'/'chosen.jsonl')]
idx = {ch:i for i,ch in enumerate(chars)}
V = np.zeros((len(chosen), S*S), np.float32)
for i,r in enumerate(chosen):
    v,_ = norm_glyph(ROOT/'work'/'cells'/r['file'])
    if v is not None:
        ink = (v < 0.55).astype(np.float32)
        V[i]=cv2.GaussianBlur(ink,(0,0),1.0).ravel()
V /= (np.linalg.norm(V,axis=1,keepdims=True)+1e-6)
score = V @ B.T
out=[]
for i,r in enumerate(chosen):
    s = score[i].copy()
    own = s[idx[r['label']]]
    s[idx[r['label']]] = -9
    j = int(np.argmax(s))
    out.append(dict(char=r['label'], best=chars[j], own=float(own), best_s=float(s[j]),
                    n=r['n_samples'], file=r['file']))
out.sort(key=lambda o: o['best_s']-o['own'], reverse=True)
flag=[o for o in out if o['best']!=o['char'] and (o['best_s']-o['own'])>0.12]
print('flagged',len(flag),'of',len(out))
for o in flag[:60]: print(f"{o['char']} -> {o['best']}  (own {o['own']:.2f} vs {o['best_s']:.2f}) n={o['n']}")
json.dump(out, open(ROOT/'work'/'real_check.json','w'), ensure_ascii=False)
