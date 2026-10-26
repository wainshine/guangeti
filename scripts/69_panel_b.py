"""B-line comparison panel: book glyph vs WenKai / ribbon / GAN checkpoints.

Rows: 真跡（書上原字）· 霞鶩文楷 · ribbon · 每個 GAN 檢查點
Columns: N characters drawn from the single-occurrence clean set (never trained on).

  python3 scripts/69_panel_b.py --gan work-b/ckpt/b_ep040.pt --n 24 \
          --out docs/images/eval-panel-b.png
"""
from __future__ import annotations

import argparse
import sys
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import torch
torch.set_num_threads(1)   # audit 3-25: CPU inference must stay single-threaded
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B  # noqa: E402
from generate_lib import ribbon_scale_b  # noqa: E402

S = 256
CELL = 128


def load_gan(path):
    spec = spec_from_file_location("ganlib", ROOT / "scripts" / "21_train_gan.py")
    m = module_from_spec(spec)
    spec.loader.exec_module(m)
    g = m.Generator()
    g.load_state_dict(torch.load(path, map_location="cpu")["G"])
    g.eval()
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--eval-data", default="")
    ap.add_argument("--gan", action="append", default=[])
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--thr", type=float, default=-0.30,
                    help="GAN output threshold. Must match the released operating point "
                         "(audit 2-7: it used to be hardcoded 0, so the panel showed a "
                         "heavier font than the one shipped)")
    ap.add_argument("--out", default=str(ROOT / "docs" / "images" / "eval-panel-b.png"))
    args = ap.parse_args()
    wd = Path(args.work)
    data = Path(args.eval_data) if args.eval_data else wd / "pairs_single.npz"
    d = np.load(data, allow_pickle=True)
    X, Y, chars = d["X"], d["Y"], [str(c) for c in d["chars"]]
    sel = np.random.RandomState(0).choice(len(X), min(args.n, len(X)), replace=False)
    rel = np.load(wd / "stroke_rel_width.npy")

    rows = [("真跡", [Y[i] for i in sel]),
            ("霞鶩文楷", [X[i] for i in sel])]

    def ribbon(i, ch=None):
        wm = X[i] > 127
        fr = B.glyph_frames(wm, S)
        # audit 3-23: production seeds by ord(ch); seeding by array index here meant the
        # evaluated glyph used a different ribbon-width sample than the shipped one
        r = np.random.RandomState(int(ord(ch) % (2 ** 31)) if ch else int(i))
        raw = r.choice(rel, size=len(fr), replace=True)
        raw /= max(1e-6, raw.mean())
        w = np.power(raw, 1.4)
        w /= max(1e-6, w.mean())
        return (B.render_ribbon(fr, scale=ribbon_scale_b(float(wm.sum())), dips=w,
                                end_skew=0.9, taper=0.2, size=S, ss=2) > 0).astype(np.uint8) * 255

    rows.append(("ribbon", [ribbon(i, chars[i]) for i in sel]))
    for path in args.gan:
        G = load_gan(path)
        outs = []
        for i in sel:
            a = (X[i].astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
            with torch.no_grad():
                m = G(torch.from_numpy(a).float()).numpy()[0, 0] > args.thr
            outs.append(m.astype(np.uint8) * 255)
        rows.append((Path(path).stem, outs))

    lab_w = 96
    W = lab_w + len(sel) * CELL
    H = len(rows) * CELL + 30
    img = Image.new("L", (W, H), 255)
    dr = ImageDraw.Draw(img)
    f = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), 20)
    small = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), 14)
    for r, (name, ims) in enumerate(rows):
        dr.text((6, r * CELL + CELL // 2 - 10), name, font=f, fill=0)
        for c, im in enumerate(ims):
            a = np.array(Image.fromarray(im).resize((CELL - 4, CELL - 4), Image.LANCZOS))
            img.paste(Image.fromarray(a), (lab_w + c * CELL + 2, r * CELL + 2))
    for c, i in enumerate(sel):
        dr.text((lab_w + c * CELL + 4, H - 22), chars[i], font=small, fill=0)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print("panel ->", args.out, img.size, "rows:", [r[0] for r in rows])


if __name__ == "__main__":
    main()
