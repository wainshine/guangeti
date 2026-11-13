"""C-line 大字实验: visual panel + font-level ink curves for the verdict.

Checkpoint-level metrics (Dice / chamfer / 崩坏率) already come from the
parameterised `82_eval_c.py`; this script covers what it does not:

  * a three-row panel  真迹大字 / GAN-big / GAN-base  on the same 大字 clean set
    (the eyeball check for "风格更接近大字真迹");
  * font-level ink curves for GuanGeKai-C-Big vs GuanGeKai-C at several px sizes,
    plus the 真迹 anchor: median ink density of the 大字 clean targets vs the
    小字 clean targets (work-c/pairs_clean.npz).  If the GAN-big style really is
    closer to the 字头 writing, the font ratio C-Big/C should move toward the
    真迹 ratio 大字/小字.

    python3 scripts/104_eval_big_c.py                 # panel + curves
    python3 scripts/104_eval_big_c.py --no-panel      # only the ink table
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
S = 256
EM_TOP = 880.0


def load_gen(ckpt: str):
    import torch
    spec = importlib.util.spec_from_file_location("gan", ROOT / "scripts" / "21_train_gan.py")
    gan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gan)
    G = gan.Generator()
    ck = torch.load(ckpt, map_location="cpu")
    G.load_state_dict(ck["G"])
    G.eval()
    # Release/visual evaluation is CPU-canonical (AUDIT-2026-11-01-MPS-VAL):
    # MPS and CPU disagree on the same checkpoint; never draw the shipped-glyph
    # panel on MPS.
    dev = "cpu"
    G.to(dev)
    return G, dev


def infer(G, dev, X, bs=32):
    import torch
    outs = []
    with torch.no_grad():
        for i in range(0, len(X), bs):
            a = X[i:i + bs].astype(np.float32) / 127.5 - 1.0
            a = np.repeat(a[:, None], 3, 1)
            outs.append(G(torch.from_numpy(a).to(dev)).cpu().numpy())
    return np.concatenate(outs, 0)[:, 0]          # (N,256,256) in [-1,1]


def render_font(path: str, chars, size: int):
    font = ImageFont.truetype(path, size)
    baseline = EM_TOP * size / 1000.0
    fracs = []
    for ch in chars:
        img = Image.new("L", (size, size), 0)
        ImageDraw.Draw(img).text((0, baseline), ch, fill=255, font=font, anchor="ls")
        fracs.append((np.array(img) > 127).mean())
    return fracs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--big-ckpt", default=str(ROOT / "work-c-big/ckpt/cbig.pt"))
    ap.add_argument("--base-ckpt", default=str(ROOT / "work-c/ckpt/v1.3/c_ep090.pt"))
    ap.add_argument("--clean", default=str(ROOT / "work-c-big/pairs_clean.npz"))
    ap.add_argument("--base-clean", default=str(ROOT / "work-c/pairs_clean.npz"))
    ap.add_argument("--font-big", default=str(ROOT / "build/GuanGeKai-C-Big-Regular.ttf"))
    ap.add_argument("--font-base", default=str(ROOT / "build/GuanGeKai-C-Regular.ttf"))
    ap.add_argument("--out", default=str(ROOT / "work-c-big/report"))
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--sizes", type=int, nargs="+", default=[16, 24, 48, 256])
    ap.add_argument("--no-panel", action="store_true")
    ap.add_argument("--no-fonts", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    d = np.load(args.clean, allow_pickle=True)
    X, Y = d["X"], d["Y"]
    chars = [str(c) for c in d["chars"]]
    rng = np.random.RandomState(0)
    sel = np.sort(rng.choice(len(X), min(args.n, len(X)), replace=False))

    result = {}
    if not args.no_panel:
        rows, labels = [Y[sel]], ["real-big"]
        for tag, ck in (("gan-big", args.big_ckpt), ("gan-base", args.base_ckpt)):
            if not ck or not Path(ck).exists():
                print(f"skip {tag}: {ck} missing")
                continue
            G, dev = load_gen(ck)
            g = infer(G, dev, X[sel])
            rows.append(((g > 0) * 255).astype(np.uint8))
            labels.append(tag)
            del G
        H, W = S, S * len(sel)
        sheet = Image.new("L", (W, H * len(rows) + 18 * len(rows)), 0)
        dr = ImageDraw.Draw(sheet)
        for r, (im, lab) in enumerate(zip(rows, labels)):
            dr.text((4, r * (H + 18) + 2), lab, fill=160)
            sheet.paste(Image.fromarray(np.concatenate(list(im), axis=1)),
                        (0, r * (H + 18) + 18))
        sheet.save(out / "panel_big_vs_c.png")
        print(f"panel -> {out / 'panel_big_vs_c.png'}  rows={labels}")

    if not args.no_fonts:
        # 真迹 anchor: ink density of the 大字 clean targets vs the 小字 clean targets
        dens_big = float(np.median([(y > 127).mean() for y in Y]))
        dens_small = None
        if Path(args.base_clean).exists():
            db = np.load(args.base_clean, allow_pickle=True)
            dens_small = float(np.median([(y > 127).mean() for y in db["Y"]]))
        sample_chars = [chars[i] for i in sel]
        curves = {}
        for tag, fp in (("C-Big", args.font_big), ("C", args.font_base)):
            if not Path(fp).exists():
                print(f"skip font {tag}: {fp} missing")
                continue
            curves[tag] = {s: float(np.mean(render_font(fp, sample_chars, s)))
                           for s in args.sizes}
        result["real_ink_density"] = dict(big=dens_big, small=dens_small,
                                          ratio=(dens_big / dens_small
                                                 if dens_small else None))
        result["font_ink"] = curves
        if "C-Big" in curves and "C" in curves:
            result["font_ratio_big_over_c"] = {
                s: curves["C-Big"][s] / curves["C"][s] for s in args.sizes}
        (out / "font_ink.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
        print(json.dumps(result, ensure_ascii=False, indent=1))

        # specimen sheet: same chars, both fonts side by side at 48 px
        if Path(args.font_big).exists() and Path(args.font_base).exists():
            n = len(sample_chars)
            size = 48
            sheet = Image.new("L", (size * n + 8, size * 2 + 40), 255)
            dr = ImageDraw.Draw(sheet)
            for r, (tag, fp) in enumerate((("C-Big", args.font_big), ("C", args.font_base))):
                font = ImageFont.truetype(fp, size)
                bl = EM_TOP * size / 1000.0
                for c_, ch in enumerate(sample_chars):
                    img = Image.new("L", (size, size), 255)
                    ImageDraw.Draw(img).text((2, bl), ch, fill=0, font=font, anchor="ls")
                    sheet.paste(img, (c_ * size + 4, r * (size + 20) + 18))
                dr.text((2, r * (size + 20) + 2), tag, fill=0)
            sheet.save(out / "specimen_big_vs_c.png")
            print(f"specimen -> {out / 'specimen_big_vs_c.png'}")


if __name__ == "__main__":
    main()
