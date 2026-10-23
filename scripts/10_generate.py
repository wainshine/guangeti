"""Generate the missing CJK characters (style-transfer model, or brush fallback)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from glyphvec import normalize_to_base, trace  # noqa: E402
from generate_lib import UNet, render_base, raster_to_em  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
S = 256
BLOCK = (0x4E00, 0x9FFF)
MASKFILE = ROOT / "work" / "gen_masks.npy"


def dist_channel(a):
    b = (a > 127).astype(np.uint8)
    d = cv2.distanceTransform(1 - b, cv2.DIST_L2, 5)
    return np.clip(d / 8.0, 0, 1)


def brush_style(a, k1=0, k2=1):
    """Vertical thinning only.

    Measured on 120 held-out glyphs: LXGW WenKai already carries 1.20x the ink of
    the print, and its vertical/horizontal width ratio is 1.08 vs the print's
    1.17.  The previous dilate(5x1)+erode(1x3) pushed ink to 1.26 and the ratio
    to 1.50 -- i.e. it made an already-heavy face heavier and flatter.
    A single vertical erosion lands at ink 1.09 / ratio 1.18, matching the print.
    """
    b = (a > 127).astype(np.uint8)
    if k1:
        b = cv2.dilate(b, cv2.getStructuringElement(cv2.MORPH_RECT, (2 * k1 + 1, 1)))
    if k2:
        b = cv2.erode(b, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 2 * k2 + 1)))
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    return (b > 0).astype(np.uint8)


def field_chunk(args):
    lo, hi, chars, font_path, S, ss, mode = args
    import importlib
    bl = importlib.import_module("brush_lib")
    from PIL import ImageFont as _IF
    font = _IF.truetype(font_path, S)
    rel = np.load(ROOT / "work/stroke_rel_width.npy")
    out = np.zeros((hi - lo, S, S), np.uint8)
    ok = np.zeros(hi - lo, bool)
    for k, ch in enumerate(chars[lo:hi]):
        base = render_base(font, ch, S)
        bm = (base > 127)
        fr = bl.glyph_frames(bm)
        ds = np.ones(max(1, len(fr)))
        if len(fr):
            rng = np.random.RandomState(ord(ch) % (2 ** 31))
            ds = rng.choice(rel, size=len(fr), replace=True)
            ds = ds / max(1e-6, float(ds.mean()))
        if mode == 'ribbon':
            w = np.power(ds, 1.4)
            w = w / max(1e-6, float(w.mean()))     # keep mean ink at 1.0
            m = bl.render_ribbon(fr, scale=0.82, dips=w,
                                 end_skew=0.9, taper=0.2, ss=ss).astype(np.uint8)
        else:
            m = bl.render_field(fr, scale=0.9, dips=ds, ss=ss).astype(np.uint8)
        inter = (m & bm).sum(); union = max(1, (m | bm).sum())
        good = inter / union >= 0.7 and m.sum() > bm.sum() * 0.7
        out[k] = m if good else bm.astype(np.uint8)
        ok[k] = good
    return lo, out, ok


def trace_chunk(args):
    lo, hi, chars, tag = args
    masks = np.load(MASKFILE, mmap_mode="r")
    out = []
    for i in range(lo, hi):
        mask = np.array(masks[i]) > 0
        base_ok = tag["ok"][i]
        ch = chars[i]
        try:
            cs = trace(mask, turdsize=4, alphamax=1.0, opttol=0.25)
            if not cs:
                continue
            em = raster_to_em(cs, S)
        except Exception:
            try:
                from generate_lib import render_base as _rb
                from PIL import ImageFont as _IF
                _f = _IF.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S)
                mask2 = _rb(_f, ch, S) > 127
                cs = trace(mask2, turdsize=4, alphamax=1.0, opttol=0.25)
                em = raster_to_em(cs, S)
            except Exception:
                continue
        if CAPS:
            try:
                import importlib
                cg = importlib.import_module("19_cap_geom")
                hd = np.load(ROOT / "work/cap_h_fit.npy") * CAP_K
                em = cg.apply_caps(em, mask, hd, ord(ch))
            except Exception:
                pass
        em = normalize_to_base(em, ch, blend=1.0, min_scale=0.8, max_scale=1.25)
        out.append((ch, em, "gen" if base_ok else "base"))
    return out


CAPS = False
CAP_K = 1.2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default=str(ROOT / "work" / "style_unet.pt"))
    ap.add_argument("--out", default=str(ROOT / "work" / "generated.jsonl"))
    ap.add_argument("--method", choices=["model", "brush", "field", "ribbon"], default="brush")
    ap.add_argument("--field-ss", type=int, default=2)
    ap.add_argument("--reuse-masks", action="store_true")
    ap.add_argument("--caps", action="store_true", help="apply vector cap replacement")
    ap.add_argument("--cap-k", type=float, default=1.2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    global CAPS, CAP_K
    CAPS = bool(getattr(args, "caps", False))
    CAP_K = float(getattr(args, "cap_k", 1.2))

    real = {json.loads(l)["label"] for l in open(ROOT / "work" / "chosen.jsonl")}
    chars = [chr(c) for c in range(BLOCK[0], BLOCK[1] + 1) if chr(c) not in real]
    if args.limit:
        chars = chars[: args.limit]
    print("to generate", len(chars), "method", args.method, flush=True)
    font = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S)

    model = None
    if args.method == "model":
        import torch
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        model = UNet(base=32).to(device)
        model.load_state_dict(torch.load(args.ckpt, map_location=device))
        model.eval()

    masks = np.zeros((len(chars), S, S), dtype=np.uint8)
    ok = np.zeros(len(chars), dtype=bool)
    if args.reuse_masks and MASKFILE.exists():
        masks = np.load(MASKFILE)
        print("masks reused:", masks.shape, flush=True)
    elif args.method in ("field", "ribbon"):
        import multiprocessing as mp
        ctx = mp.get_context("fork")
        step = 200
        tasks = [(i, min(i + step, len(chars)), chars,
                  str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S, args.field_ss,
                  args.method)
                 for i in range(0, len(chars), step)]
        with ctx.Pool(args.workers) as pool:
            for lo, arr, okv in pool.imap_unordered(field_chunk, tasks):
                masks[lo:lo + len(arr)] = arr
                ok[lo:lo + len(okv)] = okv
        np.save(MASKFILE, masks)
        print("masks saved (field); tracing...", flush=True)
    else:
      B = 64
      for start in range(0, len(chars), B):
          chunk = chars[start:start + B]
          base = np.stack([render_base(font, ch, S) for ch in chunk])
          base_mask = (base > 127).astype(np.uint8)
          if model is not None:
              import torch
              x = torch.from_numpy(base).float().unsqueeze(1) / 255.0
              xd = torch.from_numpy(np.stack([dist_channel(a) for a in base])).float().unsqueeze(1)
              with torch.no_grad():
                  y = torch.sigmoid(model(torch.cat([x, xd], 1).to(device))).cpu().numpy()[:, 0]
              cand = (y > args.threshold).astype(np.uint8)
          else:
              cand = np.stack([brush_style(a) for a in base])
          for i in range(len(chunk)):
              m = cand[i]
              inter = (m & base_mask[i]).sum()
              union = max(1, (m | base_mask[i]).sum())
              iou = inter / union
              good = iou >= 0.7 and m.sum() > base_mask[i].sum() * 0.7
              masks[start + i] = m if good else base_mask[i]
              ok[start + i] = good
          if start % (B * 10) == 0:
              print(f"masks {start}/{len(chars)}", flush=True)
    np.save(MASKFILE, masks)
    print("masks saved; tracing...", flush=True)

    import multiprocessing as mp
    ctx = mp.get_context("fork")
    n = len(chars)
    step = 400
    tasks = [(i, min(i + step, n), chars, {"ok": ok}) for i in range(0, n, step)]
    results = []
    with ctx.Pool(args.workers) as pool:
        for r in pool.imap_unordered(trace_chunk, tasks):
            results.extend(r)
    order = {c: i for i, c in enumerate(chars)}
    results.sort(key=lambda x: order[x[0]])
    with open(args.out, "w") as f:
        for ch, em, src in results:
            f.write(json.dumps({"char": ch, "contours": em, "src": src}, ensure_ascii=False) + "\n")
    print("done", len(results), "of", n)


if __name__ == "__main__":
    main()
