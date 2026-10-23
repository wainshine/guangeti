"""Unified comparison across all synthesis routes (panel A with ground truth, panel B without)."""
import argparse, glob, json, os, sys
from pathlib import Path
import numpy as np
import torch
import cv2
from PIL import Image, ImageDraw, ImageFont
from scipy.stats import ks_2samp

sys.path.insert(0, str(Path(__file__).parent))
from fontbuild import VERSION  # noqa: E402
from generate_lib import ribbon_scale as _rs  # noqa: E402
import brush_lib as B
ev = __import__("importlib").import_module("18_eval")
ROOT = Path(__file__).resolve().parents[1]
S = 256


def load_pairs():
    d = np.load(ROOT / "work/pairs/pairs.npz", allow_pickle=True)
    return [str(c) for c in d["chars"]], d["X"], d["Y"]


def em_render(font_path, ch):
    f = ImageFont.truetype(font_path, S)
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).text((0, 880 * S / 1000), ch, fill=255, font=f, anchor="ls")
    return np.array(im) > 127


def jit_img(dirpat, ch):
    fs = glob.glob(str(ROOT / dirpat / "*" / "generated" / f"*U+{ord(ch):04X}*.png"))
    if not fs:
        return None
    return np.array(Image.open(fs[0]).convert("L").resize((S, S))) < 128


def build_methods():
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("gan", ROOT / "scripts/21_train_gan.py")
    gan = module_from_spec(spec); spec.loader.exec_module(gan)
    ck = torch.load(ROOT / "work/zi2zi_gan.pt", map_location="cpu")
    G = gan.Generator(); G.load_state_dict(ck["G"]); G.eval()
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    G.to(dev)

    spec2 = spec_from_file_location("unet", ROOT / "scripts/generate_lib.py")
    gl = module_from_spec(spec2); spec2.loader.exec_module(gl)
    U = gl.UNet(base=32); U.load_state_dict(torch.load(ROOT / "work/style_dice.pt", map_location="cpu")); U.eval()

    REL = np.load(ROOT / "work/stroke_rel_width.npy")

    def ribbon(ch):
        m = em_render(ROOT / "data/base/LXGWWenKai-Regular.ttf", ch)
        fr = B.glyph_frames(m)
        rng = np.random.RandomState(ord(ch) % (2 ** 31))
        ds = rng.choice(REL, size=len(fr), replace=True)
        w = np.power(ds, 1.4); w = w / max(1e-6, float(w.mean()))
        return B.render_ribbon(fr, scale=_rs(float(m.sum())), dips=w, end_skew=0.9, taper=0.2)

    def unet(ch):
        x = gl.render_base(ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S), ch, S)
        xd = np.clip(cv2.distanceTransform(1 - (x > 127).astype(np.uint8), cv2.DIST_L2, 5) / 8, 0, 1)
        t = torch.from_numpy(np.stack([x.astype(np.float32) / 255, xd])[None]).float()
        with torch.no_grad():
            y = torch.sigmoid(U(t)).numpy()[0, 0]
        return y > 0.5

    def gan_fn(ch):
        x = gl.render_base(ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S), ch, S)
        a = (x.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            out = G(torch.from_numpy(a).float().to(dev)).cpu().numpy()[0, 0]
        return out > 0

    return [
        ("真迹", None),
        ("思源宋体", lambda ch: em_render(ROOT / "data/base/NotoSerifSC-Light.otf", ch)),
        ("霞鹜文楷", lambda ch: em_render(ROOT / "data/base/LXGWWenKai-Regular.ttf", ch)),
        (f"A·ribbon (v{VERSION})", ribbon),
        ("U-Net (E3)", unet),
        ("JiT 零样本", lambda ch: jit_img("data/zi2zi_eval_zerob", ch)),
        ("JiT LoRA-40", lambda ch: jit_img("data/zi2zi_eval_lora40b", ch)),
        ("JiT LoRA-600", lambda ch: jit_img("data/zi2zi_eval_lora600b", ch)),
        ("zi2zi-GAN", gan_fn),
    ]


def metrics(m, t, store=None):
    """Per-glyph metrics; cap profiles are accumulated into `store` for a
    population-level KS (a per-glyph KS is far too noisy)."""
    d = {"dice": float(2 * (m & t).sum() / max(1, (m.sum() + t.sum()))),
         "iou": float((m & t).sum() / max(1, (m | t).sum())),
         "ink": float(m.sum() / max(1, t.sum()))}
    cp = [p[2] / p[-1] for p in ev.cap_profiles(m)]
    if store is not None:
        store.setdefault("cap", []).extend(cp)
    if cp:
        d["cap_mid"] = float(np.median(cp))
    st = []
    for f in B.glyph_frames(m):
        n = len(f["pts"])
        if n < 24: continue
        r = f["r_obs"]; med = float(np.median(r[n // 3:2 * n // 3]))
        if med >= 2: st.append(float(np.std(r / med)))
    d["stroke_std"] = float(np.median(st)) if st else None
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--set", default=str(ROOT / "work/eval_clean.json"))
    args = ap.parse_args()
    chars, X, Y = load_pairs()
    pos = {c: i for i, c in enumerate(chars)}
    clean = json.load(open(args.set))[: args.n]
    methods = build_methods()

    real_store = {"cap": []}
    for ch in clean:
        for p in ev.cap_profiles(Y[pos[ch]] > 127):
            real_store["cap"].append(p[2] / p[-1])
    rows = {"真迹": {"cap_mid": round(float(np.median(real_store["cap"])), 3)}}
    for name, fn in methods:
        if fn is None:
            continue
        per, store = [], {"cap": []}
        for ch in clean:
            m = fn(ch)
            if m is None:
                continue
            per.append(metrics(m, Y[pos[ch]] > 127, store))
        if not per:
            continue
        rows[name] = {k: round(float(np.nanmean([p[k] for p in per if p.get(k) is not None])), 3)
                      for k in ("dice", "iou", "ink", "cap_mid", "stroke_std")}
        rows[name]["cap_ks"] = round(float(ks_2samp(real_store["cap"], store["cap"]).statistic), 3)
        rows[name]["n"] = len(per)

    print(json.dumps(rows, ensure_ascii=False, indent=1))
    (ROOT / "work/eval_all.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))

    # panels need at least 8 chars; a small --n run must not overwrite the published images
    if len(clean) < 8:
        print(f"only {len(clean)} chars: metrics written, panels skipped")
        return
    # panel: 8 chars x methods that can actually render them
    probe = clean[0]
    usable = [(n, f) for n, f in methods if f is None or f(probe) is not None]
    sel = []
    for c in clean:
        if len(sel) >= 8:
            break
        if all((fn is None) or (fn(c) is not None) for _, fn in usable):
            sel.append(c)
    methods = usable
    H = len(methods); W = len(sel)
    if W == 0:
        print("panel A skipped: no char has outputs from every usable method")
        return
    sheet = Image.new("L", (S * W, S * H), 0)
    for r, (name, fn) in enumerate(methods):
        for c, ch in enumerate(sel):
            m = Y[pos[ch]] > 127 if fn is None else fn(ch)
            sheet.paste(Image.fromarray((np.asarray(m) * 255).astype(np.uint8)), (c * S, r * S))
    # (no intermediate file: the finished panels go straight to docs/images)
    lab = Image.new("L", (S * W + 160, S * H), 0)
    lab.paste(sheet, (160, 0))
    d = ImageDraw.Draw(lab)
    f = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), 26)
    for r, (name, _) in enumerate(methods):
        d.text((8, r * S + S // 2 - 12), name, font=f, fill=255)
    lab.resize((lab.width // 2, lab.height // 2)).save(ROOT / "docs/images/eval-panelA.png")
    print("panelA ->", ROOT / "docs/images/eval-panelA.png")

    # ---- panel B: characters with NO ground truth (the real use case)
    have = set(chars)
    gen_chars = []
    with open(ROOT / "work/generated.jsonl") as fh:
        for line in fh:
            c = json.loads(line)["char"]
            if c not in have:
                gen_chars.append(c)
            if len(gen_chars) >= 8:
                break
    ship = ImageFont.truetype(str(ROOT / "build/GuanGeKai-Regular.ttf"), S)

    def shipped(ch):
        im = Image.new("L", (S, S), 0)
        ImageDraw.Draw(im).text((0, 880 * S / 1000), ch, fill=255, font=ship, anchor="ls")
        return np.array(im) > 127

    rows_b = [(n, f) for n, f in methods if n in ("思源宋体", "霞鹜文楷", f"A·ribbon (v{VERSION})", "zi2zi-GAN")]
    rows_b.append(("已发布字体", shipped))
    pb = Image.new("L", (S * len(gen_chars) + 160, S * len(rows_b)), 0)
    for r, (name, fn) in enumerate(rows_b):
        for c, ch in enumerate(gen_chars):
            m = fn(ch)
            if m is None:
                continue
            pb.paste(Image.fromarray((np.asarray(m) * 255).astype(np.uint8)), (160 + c * S, r * S))
    db = ImageDraw.Draw(pb)
    for r, (name, _) in enumerate(rows_b):
        db.text((8, r * S + S // 2 - 12), name, font=f, fill=255)
    pb.resize((pb.width // 2, pb.height // 2)).save(ROOT / "docs/images/eval-panelB.png")
    print("panelB ->", ROOT / "docs/images/eval-panelB.png", "chars:", "".join(gen_chars))


if __name__ == "__main__":
    main()
