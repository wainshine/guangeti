"""Probe: does 600 dpi recover counters that 300 dpi loses? (audit P0 root cause 1)"""
import sys, json, collections
from pathlib import Path
import numpy as np, cv2, pymupdf
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from pageproc import ink_mask, clean_text_mask
from PIL import Image, ImageDraw, ImageFont

def holes(m):
    if m.size == 0: return 0
    bg = (m < 127).astype(np.uint8); n, lab, st, _ = cv2.connectedComponentsWithStats(bg, 8)
    h, w = m.shape
    return sum(1 for i in range(1, n)
               if not (st[i][0] == 0 or st[i][1] == 0 or st[i][0]+st[i][2] == w or st[i][1]+st[i][3] == h)
               and st[i][4] > 20)

meta = {json.loads(l)["file"]: json.loads(l) for l in open(ROOT/"work/cells.jsonl")}
wk = ImageFont.truetype(str(ROOT/"data/base/LXGWWenKai-Regular.ttf"), 256)
def wk_holes(ch, S=256):
    im = Image.new("L",(S,S),0); ImageDraw.Draw(im).text((0,int(S*0.88)),ch,fill=255,font=wk,anchor="ls")
    a=(np.array(im)>127); return holes((~a).astype(np.uint8)*255)

seen=set(); rows=[]
for l in open(ROOT/"work/chosen.jsonl"):
    r=json.loads(l); ch=r["label"]
    if ch in seen or wk_holes(ch)==0: continue
    seen.add(ch); rows.append(r)
    if len(rows)>=200: break

doc = pymupdf.open(str(ROOT/"四书白文.18卷.旧传明.姜立纲.pdf"))
cache={}; out=[]; rec=0
for i,r in enumerate(rows):
    f=r["file"]; m0=meta[f]; pno=int(f[1:5])-1
    if pno not in cache:
        pix=doc[pno].get_pixmap(dpi=600)
        rgb=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3).copy()
        bw,_=ink_mask(rgb); cache[pno]=clean_text_mask(bw)
    mk=cache[pno]
    k=2; pad=12
    x0,y0=max(0,m0["x0"]*k-pad),max(0,m0["y0"]*k-pad)
    x1=min(mk.shape[1],m0["x1"]*k+pad); y1=min(mk.shape[0],m0["y1"]*k+pad)
    h600=holes(mk[y0:y1,x0:x1])
    m300=cv2.imread(str(ROOT/"work/masks"/f),0)
    h300=holes(m300) if m300 is not None else -1
    w=wk_holes(r["label"])
    out.append({"char":r["label"],"file":f,"h300":h300,"h600":h600,"wk":w})
    if h300<w and h600>=w: rec+=1
    if (i+1)%25==0: print(f"{i+1}/{len(rows)}", flush=True)
json.dump(out, open(ROOT/"work/hidpi_probe.json","w"), ensure_ascii=False, indent=1)
gain=[o for o in out if o["h300"]<o["wk"]]
print("tested",len(out),"| 300 缺孔",len(gain),"| 600 恢复",rec,
      f"({rec/max(1,len(gain))*100:.0f}% of deficient)")
