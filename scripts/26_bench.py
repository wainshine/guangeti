"""Three-class benchmark: seen / unseen / no-ground-truth, same rules for every method.

class A (work/bench_seen.json)   : chars the learned models were trained on
class B (work/bench_unseen.json) : chars no learned model has seen, but the book has them
class C (work/bench_noreal.json) : chars absent from the book -> sanity metrics only
"""
from __future__ import annotations

import argparse, glob, json, sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B
from fontbuild import VERSION  # noqa: E402
from generate_lib import ribbon_scale as _rs  # noqa: E402
from importlib import import_module
ev = import_module("18_eval")
from importlib.util import spec_from_file_location, module_from_spec

S = 256


GAN_PATH = ROOT / "work/zi2zi_gan.pt"
GAN_LABEL = "B·zi2zi-GAN"
CLASS_FILES = {"A": str(ROOT / "work" / "bench_seen.json"),
               "B": str(ROOT / "work" / "bench_unseen.json"),
               "C": str(ROOT / "work" / "bench_noreal.json")}


def leak_note(class_path, ckpt_path):
    """How many chars of this benchmark class were in the checkpoint's training set."""
    split = Path(str(ckpt_path).replace(".pt", "_split.json"))
    if not split.exists():
        return "unknown"
    try:
        tr = set(json.loads(split.read_text())["train_chars"])
    except Exception:
        return "unknown"
    cs = json.loads(Path(class_path).read_text())
    n = sum(c in tr for c in cs)
    return f"{n}/{len(cs)}"


def load_gan():
    spec = spec_from_file_location("gan", ROOT / "scripts/21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    g = gan.Generator()
    g.load_state_dict(torch.load(GAN_PATH, map_location="cpu")["G"]); g.eval()
    return g


def load_unet():
    spec = spec_from_file_location("gl", ROOT / "scripts/generate_lib.py")
    gl = module_from_spec(spec); spec.loader.exec_module(gl)
    u = gl.UNet(base=32); u.load_state_dict(torch.load(ROOT / "work/style_dice.pt", map_location="cpu")); u.eval()
    return u, gl


def em_render(path, ch):
    f = ImageFont.truetype(str(path), S)
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).text((0, 880 * S / 1000), ch, fill=255, font=f, anchor="ls")
    return np.array(im) > 127


def jit(dirname, ch):
    fs = glob.glob(str(ROOT / dirname / "*" / "generated" / f"*U+{ord(ch):04X}*.png"))
    return np.array(Image.open(fs[0]).convert("L").resize((S, S))) < 128 if fs else None


def holes(m, minarea=20):
    """Count significant counters only: small speck holes make raw counts noisy."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats((~m).astype(np.uint8), 8)
    c = 0
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < minarea:
            continue
        if x <= 1 or y <= 1 or x + w >= m.shape[1] - 1 or y + h >= m.shape[0] - 1:
            continue
        c += 1
    return c


def build():
    G = load_gan(); U, gl = load_unet()
    REL = np.load(ROOT / "work/stroke_rel_width.npy")

    def ribbon(ch):
        m = em_render(ROOT / "data/base/LXGWWenKai-Regular.ttf", ch)
        fr = B.glyph_frames(m)
        rng = np.random.RandomState(ord(ch) % (2 ** 31))
        raw = rng.choice(REL, size=len(fr), replace=True)
        w = np.power(raw, 1.4); w = w / max(1e-6, float(w.mean()))
        return B.render_ribbon(fr, scale=_rs(float(m.sum())), dips=w, end_skew=0.9, taper=0.2)

    def gan_fn(ch):
        x = gl.render_base(ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S), ch, S)
        a = (x.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            return G(torch.from_numpy(a).float()).numpy()[0, 0] > 0

    def unet_fn(ch):
        x = gl.render_base(ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S), ch, S)
        xd = np.clip(cv2.distanceTransform(1 - (x > 127).astype(np.uint8), cv2.DIST_L2, 5) / 8, 0, 1)
        t = torch.from_numpy(np.stack([x.astype(np.float32) / 255, xd])[None]).float()
        with torch.no_grad():
            return torch.sigmoid(U(t)).numpy()[0, 0] > 0.5

    return [
        ("思源宋体", lambda ch: em_render(ROOT / "data/base/NotoSerifSC-Light.otf", ch)),
        ("霞鹜文楷", lambda ch: em_render(ROOT / "data/base/LXGWWenKai-Regular.ttf", ch)),
        (f"A·ribbon (v{VERSION})", ribbon),
        ("U-Net (E3)", unet_fn),
        ("JiT 零样本", lambda ch, k=CLS[0]: jit(JIT[k][0], ch)),
        ("JiT LoRA-40", lambda ch, k=CLS[0]: jit(JIT[k][1], ch)),
        ("JiT LoRA-600", lambda ch, k=CLS[0]: jit(JIT[k][2], ch)),
        (GAN_LABEL, gan_fn),
    ]


CLS = ["A"]
JIT = {
    "A": ("data/jit_zeroA", "data/jit_l40A", "data/jit_l600A"),
    "B": ("data/zi2zi_eval_zerob", "data/zi2zi_eval_lora40b", "data/zi2zi_eval_lora600b"),
    "C": ("data/jit_zeroC", "data/jit_l40C", "data/jit_l600C"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--classes", default="A,B,C")
    ap.add_argument("--gan", default=str(ROOT / "work" / "zi2zi_gan.pt"),
                    help="checkpoint of the zi2zi-GAN row")
    ap.add_argument("--gan-label", default="B·zi2zi-GAN")
    args = ap.parse_args()
    global GAN_PATH, GAN_LABEL
    GAN_PATH = Path(args.gan)
    GAN_LABEL = args.gan_label
    sets = {"A": "work/bench_seen.json", "B": "work/bench_unseen.json", "C": "work/bench_noreal.json"}
    d = np.load(ROOT / "work/pairs/pairs.npz", allow_pickle=True)
    chars = [str(c) for c in d["chars"]]; Y = d["Y"]; pos = {c: i for i, c in enumerate(chars)}
    out = {}
    for key in args.classes.split(","):
        CLS[0] = key
        methods = build()
        cs = json.load(open(ROOT / sets[key]))
        real = [c for c in cs if c in pos]
        real_cap = []
        for c in real:
            real_cap += [p[2] / p[-1] for p in ev.cap_profiles(Y[pos[c]] > 127)]
        rows = {}
        for name, fn in methods:
            D, ink, cap, st, hok, hn = [], [], [], [], 0, 0
            missing = 0
            for c in cs:
                m = fn(c)
                if m is None:
                    missing += 1
                    continue
                if key in ("A", "B"):
                    t = Y[pos[c]] > 127
                    D.append(B.dice(m, t)); ink.append(m.sum() / max(1, t.sum()))
                    cap += [p[2] / p[-1] for p in ev.cap_profiles(m)]
                    hok += int(holes(m) == holes(t)); hn += 1
                    for f in B.glyph_frames(m):
                        n = len(f["pts"])
                        if n < 24: continue
                        r = f["r_obs"]; med = float(np.median(r[n // 3:2 * n // 3]))
                        if med >= 2: st.append(float(np.std(r / med)))
                else:
                    base = em_render(ROOT / "data/base/LXGWWenKai-Regular.ttf", c)
                    ink.append(m.sum() / max(1, base.sum()))
                    hok += int(holes(m) == holes(base)); hn += 1
            if missing:
                print(f"  WARNING: {name} has no output for {missing}/{len(cs)} chars "
                      f"(missing input dirs?) — its row is not comparable")
            r = {"n": len(ink)}
            if key in ("A", "B") and D:
                r.update(dice=round(float(np.mean(D)), 3),
                         cap_mid=round(float(np.median(cap)), 3),
                         cap_ks=round(float(ks_2samp(real_cap, cap).statistic), 3),
                         stroke_std=round(float(np.median(st)), 3) if st else None,
                         hole_agree=f"{hok}/{hn}")
            r["ink"] = round(float(np.mean(ink)), 3)
            if key == "C":
                r["hole_agree"] = f"{hok}/{hn}"
            rows[name] = r
        out[key] = rows
        leak = leak_note(CLASS_FILES.get(key, ""), GAN_PATH) if key in ("A", "B") else "n/a"
        print(f"\n== class {key} (n={len(cs)})  {GAN_LABEL} 训练集覆盖: {leak}")
        print(f"{'method':18s} {'n':>4s} {'Dice':>6s} {'ink':>6s} {'cap':>6s} {'KS':>6s} {'std':>6s} {'holes':>8s}")
        for name, r in rows.items():
            print(f"{name:18s} {r['n']:4d} {r.get('dice',0):6.3f} {r['ink']:6.3f} {r.get('cap_mid',0):6.3f} "
                  f"{r.get('cap_ks',0):6.3f} {r.get('stroke_std') or 0:6.3f} {r.get('hole_agree','-'):>8s}")
    dump = ROOT / "work/bench_results.json"
    merged = {}
    if dump.exists():
        try:
            merged = json.loads(dump.read_text())
        except Exception:
            merged = {}
    for cls, methods in out.items():          # keep rows from earlier runs
        merged.setdefault(cls, {}).update(methods)
    dump.write_text(json.dumps(merged, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
