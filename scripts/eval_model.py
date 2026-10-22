"""Visual eval: model output vs real glyph for held-out characters."""
import argparse, sys
from pathlib import Path
import numpy as np, torch, cv2
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import cv2
from generate_lib import UNet, render_base

def dist_channel(a):
    b = (a > 127).astype(np.uint8)
    d = cv2.distanceTransform(1 - b, cv2.DIST_L2, 5)
    return np.clip(d / 8.0, 0, 1)

ROOT = Path(__file__).resolve().parents[1]

ap = argparse.ArgumentParser()
ap.add_argument("--ckpt", default=str(ROOT/"work"/"style_b.pt"))
ap.add_argument("--n", type=int, default=18)
ap.add_argument("--out", default=str(ROOT/"work"/"preview"/"eval_style.png"))
args = ap.parse_args()
device = "mps" if torch.backends.mps.is_available() else "cpu"
d = np.load(ROOT/"work"/"pairs"/"pairs.npz", allow_pickle=True)
X0 = torch.from_numpy(d["X"]).float().unsqueeze(1)/255.0
chars = list(d["chars"])
rng = np.random.RandomState(0); perm = rng.permutation(len(chars))
val = [chars[i] for i in perm[:120]]
sel = val[:args.n]

m = UNet(base=32).to(device); m.load_state_dict(torch.load(args.ckpt, map_location=device)); m.eval()
font = ImageFont.truetype(str(ROOT/"data"/"base"/"LXGWWenKai-Regular.ttf"), 256)
xs = np.stack([render_base(font, c, 256) for c in sel])
x = torch.from_numpy(xs).float().unsqueeze(1)/255.0
xd = torch.from_numpy(np.stack([dist_channel(a) for a in xs])).float().unsqueeze(1)
with torch.no_grad(): y = torch.sigmoid(m(torch.cat([x, xd],1).to(device))).cpu().numpy()[:,0]

# real glyphs
sys.path.insert(0, str(ROOT/"scripts"))
from glyphvec import trace, transform, to_em  # noqa
import json
norm = json.load(open(ROOT/"work"/"norm.json"))
import pymupdf
meta = {json.loads(l)["file"]: json.loads(l) for l in open(ROOT/"work"/"cells.jsonl")}
chosen = {json.loads(l)["label"]: json.loads(l) for l in open(ROOT/"work"/"chosen.jsonl")}
doc = pymupdf.open(ROOT/"四书白文.18卷.旧传明.姜立纲.pdf")
real_imgs = []
for c in sel:
    r = chosen[c]; mm = meta[r["file"]]; nrm = norm[c]; pad = 6
    a = nrm["scale"]*256/1000.0*nrm["sx"]; b = nrm["scale"]*256/1000.0*nrm["sy"]
    tx = (((mm["x0"]-pad-nrm["slot_cx"])*nrm["scale"]+500)*nrm["sx"]+nrm["dx"])*256/1000.0
    ty = (880-nrm["dy"]-440*nrm["sy"]-(nrm["slot_cy"]-(mm["y0"]-pad))*nrm["scale"]*nrm["sy"])*256/1000.0
    M = np.array([[a,0,tx],[0,b,ty]], np.float32)
    pix = doc[mm["page"]].get_pixmap(dpi=300)
    rgb = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    ink = np.array(Image.open(ROOT/"work"/"masks"/r["file"]).convert("L"))
    w = cv2.warpAffine(ink, M, (256,256), flags=cv2.INTER_LINEAR, borderValue=0)
    real_imgs.append(w)

cols = 9; rows = 2
W = 256*cols; H = 256*rows + 40
sheet = Image.new("L", (W, H), 0)
for i in range(len(sel)):
    sheet.paste(Image.fromarray((np.clip(y[i],0,1)*255).astype(np.uint8)), ((i%cols)*256, (i//cols)*296))
    sheet.paste(Image.fromarray(real_imgs[i]), ((i%cols)*256, (i//cols)*296+0))
sheet = Image.new("L", (W, 2*296*2), 0)
for i in range(len(sel)):
    r = i//cols; c = i%cols
    sheet.paste(Image.fromarray((np.clip(y[i],0,1)*255).astype(np.uint8)), (c*256, r*296))
    sheet.paste(Image.fromarray(real_imgs[i]), (c*256, (rows+r)*296))
sheet.resize((W//2, int(sheet.height/2))).save(args.out)
print("eval saved", args.out, "chars", "".join(sel))
