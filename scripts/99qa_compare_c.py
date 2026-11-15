#!/usr/bin/env python3
"""C-line visual comparison: target, WenKai, v1.3 ep090, v1.4 ep020."""
import random, sys
from pathlib import Path
import numpy as np, torch
from PIL import Image, ImageDraw, ImageFont
from importlib.machinery import SourceFileLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
ev = SourceFileLoader("ev", str(ROOT / "scripts/82_eval_c.py")).load_module()
torch.set_num_threads(1)
d = np.load(ROOT / "work-c/pairs_holdout.npz", allow_pickle=True)
X = d["X"].astype(np.float32) / 127.5 - 1.0
Y = d["Y"].astype(np.float32) / 127.5 - 1.0
chars = [str(c) for c in d["chars"]]
rng = random.Random(0)
sel = rng.sample(range(len(chars)), 30)
S, M = 112, 170
ref = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 230)
lab = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 15)
def arr(a): return np.clip((a + 1) * 127.5, 0, 255).astype(np.uint8)
def glyph(ch):
    im = Image.new("L", (256, 256), 0)
    ImageDraw.Draw(im).text((128, 225), ch, fill=255, font=ref, anchor="ms")
    return np.array(im)
models = [("v1.3 ep090", ROOT / "work-c/ckpt/v1.3/c_ep090.pt"),
          ("v1.4 ep020", ROOT / "work-c/ckpt/v1.4/c_best.pt")]
Gs = [(name, ev.load_gan(str(p))) for name, p in models]
rows = ["真迹", "文楷参照"] + [n for n, _ in models]
out = Image.new("L", (M + 30 * S, (1 + len(rows)) * S), 255)
dr = ImageDraw.Draw(out)
for r, name in enumerate(rows):
    dr.text((4, (r + 1) * S + 44), name, font=lab, fill=0)
for j, i in enumerate(sel):
    dr.text((M + j * S + S // 2, 2), chars[i], font=lab, fill=0, anchor="ma")
    out.paste(Image.fromarray(arr(Y[i])).resize((S, S)), (M + j * S, S))
    out.paste(Image.fromarray(glyph(chars[i])).resize((S, S)), (M + j * S, 2 * S))
    x = np.repeat(X[i:i+1][:, None], 3, axis=1).astype(np.float32)
    for k, (_, G) in enumerate(Gs):
        with torch.no_grad():
            g = G(torch.tensor(x).to(next(G.parameters()).device)).cpu().numpy()[0, 0]
        out.paste(Image.fromarray(arr(g)).resize((S, S)), (M + j * S, (k + 3) * S))
out.save(ROOT / "work-c/qa/compare.png")
print("saved work-c/qa/compare.png", out.size)
print("chars", "".join(chars[i] for i in sel))
