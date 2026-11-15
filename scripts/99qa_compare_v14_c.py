#!/usr/bin/env python3
"""v1.4 epoch comparison, same 16-char layout as 99zu/99zt; no metrics/ranking."""
import importlib.util, json, sys
from pathlib import Path
import numpy as np, torch
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "work-c"
sys.path.insert(0, str(ROOT / "scripts"))
import generate_lib as gl
spec = importlib.util.spec_from_file_location("gan", ROOT / "scripts/21_train_gan.py")
gan = importlib.util.module_from_spec(spec); spec.loader.exec_module(gan)
torch.set_num_threads(1)
font_path = ROOT / "data/base/LXGWWenKai-Regular.ttf"
S, D = 256, 100
font = ImageFont.truetype(str(font_path), S)
small = ImageFont.truetype(str(font_path), 11)
ckpts = [("v13", W/"ckpt/v1.3/c_ep090.pt")]
ckpts += [(f"ep{e:03d}", W/f"ckpt/v1.4/c_ep{e:03d}.pt") for e in (10,20,30,40)]
ckpts += [("ep049", W/"ckpt/v1.4/c.pt")]
d = np.load(W/"pairs_holdout.npz", allow_pickle=True)
chars = [str(c) for c in d["chars"]]
idx = np.linspace(0, len(chars)-1, 16).round().astype(int).tolist()
real_chars = [chars[i] for i in idx]
real_X, real_Y = d["X"][idx], d["Y"][idx] > 127
no_chars = list("们她吧吗呢啊嗯谁您咱咋喵咩嗨喂哟")
real_set = set(json.load(open(W/"real_glyph_sources.json")))
assert not any(c in real_set for c in no_chars)

def run(Xraw):
    X = torch.from_numpy((Xraw.astype(np.float32)/127.5-1)[:,None].repeat(3,1)).float()
    outs = {}
    for name, p in ckpts:
        ck = torch.load(p, map_location="cpu")
        G = gan.Generator(); G.load_state_dict(ck["G"]); G.eval()
        with torch.no_grad(): outs[name] = G(X).numpy()[:,0]
        del G
    return outs
def draw(chars, Xraw, outs, realY, title, suffix):
    left, top = 62, 24
    ncol, nrow = len(chars), 1 + len(ckpts) + (1 if realY is not None else 0)
    im = Image.new("RGB", (left+ncol*D, top+nrow*(D+22)+60), "white")
    dr = ImageDraw.Draw(im)
    def put(a,x,y): im.paste(Image.fromarray(np.clip((a+1)*127.5,0,255).astype(np.uint8)).convert("L").resize((D,D)),(x,y))
    for j,c in enumerate(chars): dr.text((left+j*D+D//2-8,3),c,font=small,fill="black")
    for j,a in enumerate(Xraw): put(a.astype(np.float32)/127.5-1,left+j*D,top)
    dr.text((2,top+D//2-6),"input",font=small,fill="black")
    for r,(name,p) in enumerate(ckpts):
        y=top+(r+1)*(D+22)
        for j in range(ncol): put(outs[name][j],left+j*D,y)
        dr.text((2,y+D//2-6),name,font=small,fill="black")
    if realY is not None:
        y=top+(len(ckpts)+1)*(D+22)
        for j in range(ncol): put(realY[j].astype(np.float32)*2-1,left+j*D,y)
        dr.text((2,y+D//2-6),"real",font=small,fill="black")
    dr.text((left,top+nrow*(D+22)+16),title,font=small,fill="black")
    out=W/"preview"/suffix; im.save(out); print(out,im.size)

outs_real = run(real_X)
draw(real_chars, real_X, outs_real, real_Y,
     "real holdout chars — v1.3 ep090 vs v1.4 snapshots; no Dice shown",
     "v14_ep10_20_30_40_49_real.png")
outs_no = run(np.stack([gl.render_base(font,c,S) for c in no_chars]))
draw(no_chars, np.stack([gl.render_base(font,c,S) for c in no_chars]), outs_no, None,
     "NO REAL TARGET — 16 common-ish chars absent from C real pool; visual only",
     "v14_ep10_20_30_40_49_no_real.png")
