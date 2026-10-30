"""C-line: generate the missing CJK characters (GAN with a cheap guard, ribbon fallback).

Forked from `60_generate_b.py`; every path points at work-c/ and the ribbon fallback
uses the C-specific ink fit (`generate_lib.ribbon_scale_c`).  The GAN itself is the
same recipe that shipped in A/B: single instance, 5-layer PatchGAN, hinge, augment.

  python3 scripts/77_generate_c.py --method gan --workers 6 --res 512 --simplify 2.0 \
          --ckpt work-c/ckpt/c_ep080.pt --out work-c/generated_gan.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from glyphvec import (adjust_mask_area, base_bounds, contour_bounds, denoise_mask,  # noqa: E402
                      normalize_to_base, target_ink_256, trace)
from shiji_page import repair_counters  # noqa: E402
import brush_lib as B  # noqa: E402
from generate_lib import raster_to_em, render_base, ribbon_scale_c  # noqa: E402

try:
    from opencc import OpenCC
    _S2T = OpenCC("s2t")
except Exception:                       # pragma: no cover - optional dependency
    _S2T = None

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "work-c"
S = 256
BLOCK = (0x4E00, 0x9FFF)
BASE_FONT = ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"

_GAN_CACHE = None
_GAN_HT = None
CFG = {}


def _load_gan(path: str, res: int):
    import importlib.util as iu
    import torch
    spec = iu.spec_from_file_location("ganlib", ROOT / "scripts" / "21_train_gan.py")
    m = iu.module_from_spec(spec)
    spec.loader.exec_module(m)
    g = m.Generator()
    g.load_state_dict(torch.load(path, map_location="cpu")["G"])
    g.eval()
    return g


def gan_chunk(args):
    """GAN output with a *cheap* guard: empty / ink out of band / components off by >3.

    Deliberately not the E24 topology gate (that reverted 85% of glyphs); the GAN is
    trusted unless the output is obviously broken, in which case the ribbon renderer
    draws the glyph from the WenKai skeleton.
    """
    import importlib
    import torch
    torch.set_num_threads(1)
    try:
        import cv2 as _c2
        _c2.setNumThreads(1)
    except Exception:
        pass
    global _GAN_CACHE, _GAN_HT
    if _GAN_CACHE is None:
        _GAN_CACHE = _load_gan(CFG["ckpt"], CFG["gan_res"])
    gan = _GAN_CACHE
    ht_path = CFG.get("ckpt_hardtail") or ""
    if ht_path and _GAN_HT is None:
        _GAN_HT = _load_gan(ht_path, CFG["gan_res"])
    ht = _GAN_HT if ht_path else None
    bl = importlib.import_module("brush_lib")
    rel = np.load(CFG["rel_width"])
    lo, hi, chars, font_path, S = args
    GAN_RES = CFG["gan_res"]
    font = ImageFont.truetype(font_path, S)
    font_gan = ImageFont.truetype(font_path, GAN_RES)
    thr = CFG["threshold"]
    out = []
    for ch in chars[lo:hi]:
        base = render_base(font, ch, S)
        wm = base > 127
        # feed the model at its training resolution (256); running it at 512 doubles
        # the stroke width in pixels and the output comes out ~25% heavier (A-line E35)
        gin = render_base(font_gan, ch, GAN_RES)
        a = (gin.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            g = gan(torch.from_numpy(a).float()).numpy()[0, 0] > thr
        if S != GAN_RES:
            g = cv2.resize(g.astype(np.uint8) * 255, (S, S), interpolation=cv2.INTER_LINEAR) > 127
        n, _l, st, _ = cv2.connectedComponentsWithStats(g.astype(np.uint8), 8)
        amin = max(6, int(round(20 * (S / 256.0) ** 2)))   # area scales with resolution
        comps = sum(1 for i in range(1, n) if st[i, 4] >= amin)
        nw, _l2, sw, _ = cv2.connectedComponentsWithStats(wm.astype(np.uint8), 8)
        comps_w = sum(1 for i in range(1, nw) if sw[i, 4] >= amin)
        ink = float(g.sum()) / max(1.0, float(wm.sum()))
        ok = (g.sum() > 200 * (S / 256.0) ** 2
              and CFG["ink_lo"] <= ink <= CFG["ink_hi"]
              and abs(comps - comps_w) <= CFG["comp_tol"])
        tag = "gen" if ok else "base"
        if not ok and ht is not None:
            # hard-tail checkpoint: same guard, same thresholds, only a second opinion
            with torch.no_grad():
                g2 = ht(torch.from_numpy(a).float()).numpy()[0, 0] > thr
            if S != GAN_RES:
                g2 = cv2.resize(g2.astype(np.uint8) * 255, (S, S),
                                interpolation=cv2.INTER_LINEAR) > 127
            n2, _l3, st2, _ = cv2.connectedComponentsWithStats(g2.astype(np.uint8), 8)
            comps2 = sum(1 for i in range(1, n2) if st2[i, 4] >= amin)
            ink2 = float(g2.sum()) / max(1.0, float(wm.sum()))
            ok2 = (g2.sum() > 200 * (S / 256.0) ** 2
                   and CFG["ink_lo"] <= ink2 <= CFG["ink_hi"]
                   and abs(comps2 - comps_w) <= CFG["comp_tol"])
            if ok2:
                g, ok, tag = g2, True, "gen_ht"
        if not ok:
            fr = bl.glyph_frames(wm, S)
            rng = np.random.RandomState(ord(ch) % (2 ** 31))
            raw = rng.choice(rel, size=len(fr), replace=True)
            raw /= max(1e-6, raw.mean())
            w = np.power(raw, 1.4)
            w /= max(1e-6, w.mean())
            comp256 = float(wm.sum()) * (256.0 / S) ** 2
            g = bl.render_ribbon(fr, scale=ribbon_scale_c(comp256), dips=w,
                                 end_skew=0.9, taper=0.2, size=S, ss=2)
        out.append((ch, g, tag, ok))
    return lo, out


def ribbon_chunk(args):
    lo, hi, chars, font_path, S = args
    import importlib
    bl = importlib.import_module("brush_lib")
    rel = np.load(CFG["rel_width"])
    font = ImageFont.truetype(font_path, S)
    out = []
    for ch in chars[lo:hi]:
        wm = render_base(font, ch, S) > 127
        fr = bl.glyph_frames(wm, S)
        rng = np.random.RandomState(ord(ch) % (2 ** 31))
        raw = rng.choice(rel, size=len(fr), replace=True) if len(fr) else np.ones(max(1, len(fr)))
        raw /= max(1e-6, raw.mean())
        w = np.power(raw, 1.4)
        w /= max(1e-6, w.mean())
        stage = "gen"
        if len(fr):
            comp256 = float(wm.sum()) * (256.0 / S) ** 2
            m = bl.render_ribbon(fr, scale=ribbon_scale_c(comp256), dips=w,
                                 end_skew=0.9, taper=0.2, size=S, ss=2)
            good = m.sum() > wm.sum() * 0.5
            g = m if good else wm
            stage = "gen" if good else "base"
        else:
            g = wm
            stage = "base"
        out.append((ch, g, stage, stage == "gen"))
    return lo, out


def _simplify(contours, eps):
    res = []
    for c in contours:
        pts = [np.array(c["start"], float)]
        for sg in c["segs"]:
            if sg[0] == "L":
                pts.append(np.array(sg[1:3], float))
            else:
                p0 = pts[-1]
                p1 = np.array(sg[1:3], float)
                p2 = np.array(sg[3:5], float)
                p3 = np.array(sg[5:7], float)
                n = max(2, int(np.linalg.norm(p3 - p0) / 1.5))
                for t in np.linspace(0, 1, n)[1:]:
                    u = 1 - t
                    pts.append(u ** 3 * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t ** 3 * p3)
        poly = np.array(pts, np.float32).reshape(-1, 1, 2)
        ap = cv2.approxPolyDP(poly, eps, True).reshape(-1, 2)
        if len(ap) < 3:
            res.append(c)
            continue
        res.append({"start": [float(ap[0][0]), float(ap[0][1])],
                    "segs": [["L", float(p[0]), float(p[1])] for p in ap[1:]]})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(WB))
    ap.add_argument("--method", choices=["gan", "ribbon"], default="gan")
    ap.add_argument("--ckpt", default=str(WB / "ckpt" / "c_ep034_v120.pt"),
                    help="release checkpoint; see data/release-c.json")
    ap.add_argument("--rel-width", default=str(WB / "stroke_rel_width.npy"))
    ap.add_argument("--out", default=str(WB / "generated_gan.jsonl"))
    ap.add_argument("--res", type=int, default=512)
    ap.add_argument("--gan-res", type=int, default=256, help="must equal the training resolution")
    ap.add_argument("--threshold", type=float, default=0.30,
                    help="GAN output threshold. Default is the released operating point "
                         "(data/release-c.json: +0.30); v1.0.0 shipped -0.30")
    ap.add_argument("--ink-lo", type=float, default=0.42,
                    help="guard band on generated/WenKai ink.  The C targets are only "
                         "~0.59 of WenKai (A 0.82, B 0.71), so A/B's 0.6 lower bound "
                         "rejects perfectly good glyphs")
    ap.add_argument("--ink-hi", type=float, default=1.20)
    ap.add_argument("--comp-tol", type=int, default=6,
                    help="allowed difference in component count vs WenKai; C's thin "
                         "strokes fragment more than A/B's")
    ap.add_argument("--simplify", type=float, default=2.0)
    ap.add_argument("--ckpt-hardtail", default="",
                    help="secondary checkpoint tried only for characters the primary one "
                         "fails the guard on. Deterministic: the primary always gets first "
                         "refusal, so a char never switches model between runs "
                         "(PLAN-hybrid / B/E12)")
    ap.add_argument("--hole-repair", action="store_true", default=True,
                    help="escalate the closing kernel for glyphs whose counter did not "
                         "survive the model's output (audit rev3 2-3). On by default; "
                         "pass --no-hole-repair to disable")
    ap.add_argument("--no-hole-repair", dest="hole_repair", action="store_false")
    ap.add_argument("--close", type=int, default=1,
                    help="morphological closing (px) applied to the GAN output before tracing; "
                         "the released kernel is 1 (data/release-c.json)")
    ap.add_argument("--struct-guard", action="store_true", default=True,
                    help="for simplified codepoints, fall back to the ribbon renderer when "
                         "the GAN output changes the character's component count by >2 "
                         "(the model sometimes turns 鸟 into 鳥); needs opencc. On by "
                         "default in v1.0.1")
    ap.add_argument("--no-struct-guard", dest="struct_guard", action="store_false")
    ap.add_argument("--no-ink-normalize", dest="ink_normalize", action="store_false",
                    help="keep the per-character weight variation (off-curve glyphs)")
    ap.add_argument("--ink-a", type=float, default=38.7258)
    ap.add_argument("--ink-gain", type=float, default=1.10,
                    help="compensate the ~9%% area lost by the 256 px raster threshold "
                         "and potrace smoothing (measured on the C clean set)")
    ap.add_argument("--ink-exp", type=float, default=0.5701)
    ap.add_argument("--turdsize", type=int, default=3,
                    help="potrace speck filter for the generated mask (C scans are dusty)")
    ap.add_argument("--no-denoise", dest="denoise", action="store_false")
    ap.add_argument("--blend", type=float, default=0.8,
                    help="bbox blend toward WenKai after tracing; the released value is 0.8, "
                         "matching the normalisation used for the training targets")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="comma separated characters (repair a few)")
    ap.add_argument("--out-append", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    wd = Path(args.work)
    CFG.update(ckpt=args.ckpt, rel_width=args.rel_width, gan_res=args.gan_res,
               threshold=args.threshold, ink_lo=args.ink_lo, ink_hi=args.ink_hi,
               comp_tol=args.comp_tol, ckpt_hardtail=args.ckpt_hardtail)
    real = {json.loads(l)["label"] for l in open(wd / "chosen.jsonl")}
    chars = [chr(c) for c in range(BLOCK[0], BLOCK[1] + 1) if chr(c) not in real]
    if args.only:
        want = {c for c in args.only.split(",") if c}
        chars = [c for c in chars if c in want]
    if args.limit:
        chars = chars[: args.limit]
    # cross-check against the released operating point (data/release-c.json); this only
    # warns — it must never change what the command line asked for.
    try:
        rel = json.load(open(ROOT / "data" / "release-c.json"))
        if args.method == "gan":
            if abs(args.threshold - rel["threshold"]) > 1e-9:
                print(f"WARNING: --threshold {args.threshold} != released {rel['threshold']}",
                      flush=True)
            if args.close != rel["close"]:
                print(f"WARNING: --close {args.close} != released {rel['close']}", flush=True)
            if bool(args.hole_repair) != bool(rel["hole_repair"]):
                print("WARNING: --hole-repair differs from the released setting", flush=True)
            if abs(args.blend - rel.get("blend", 0.8)) > 1e-9:
                print(f"WARNING: --blend {args.blend} != released {rel.get('blend')}", flush=True)
            if bool(args.struct_guard) != bool(rel.get("struct_guard", True)):
                print("WARNING: --struct-guard differs from the released setting", flush=True)
    except (OSError, KeyError, json.JSONDecodeError):
        pass
    print("to generate", len(chars), "method", args.method, "threshold", args.threshold,
          "-> skip", len(real), "real chars", flush=True)

    import multiprocessing as mp
    ctx = mp.get_context("fork")
    S2 = int(args.res)
    fn = gan_chunk if args.method == "gan" else ribbon_chunk
    step = max(8, int(40 * (256.0 / S2) ** 2)) if S2 > 256 else 40
    step = max(step, 8)
    tasks = [(i, min(i + step, len(chars)), chars, str(BASE_FONT), S2)
             for i in range(0, len(chars), step)]
    fb, done = [], 0
    wk_font = ImageFont.truetype(str(BASE_FONT), 256) if args.struct_guard else None
    wk_font_big = ImageFont.truetype(str(BASE_FONT), S2) if args.struct_guard else None
    rel = np.load(args.rel_width)
    def _comps(m):
        n, _l, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
        return sum(1 for i in range(1, n) if st[i, 4] >= 20)
    def _ribbon_mask(ch):
        # render the mask AND its skeleton frames at the target raster size.
        # Using 256-px frames on a 512-px canvas put the glyph in the top-left
        # quarter (the 455-char guard fallback bug, audit 2026-10-30 P1).
        wm256 = render_base(wk_font, ch, 256) > 127
        wm = render_base(wk_font_big, ch, S2) > 127
        fr = B.glyph_frames(wm, S2)
        if not fr:
            return None
        r = np.random.RandomState(ord(ch) % (2 ** 31))
        raw = r.choice(rel, size=len(fr), replace=True)
        raw /= max(1e-6, raw.mean())
        w = np.power(raw, 1.4)
        w /= max(1e-6, w.mean())
        scale = float(np.clip(ribbon_scale_c(float(wm256.sum())) * 1.1, 0.3, 1.2))
        return B.render_ribbon(fr, scale=scale, dips=w, end_skew=0.9, taper=0.2,
                               size=S2, ss=2)
    with ctx.Pool(args.workers) as pool, open(args.out, "w") as fh:
        for lo, rows in pool.imap_unordered(fn, tasks):
            for ch, g, tag, ok in rows:
                if not ok:
                    fb.append(ch)
                gm = g.astype(bool)
                if args.close:
                    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (args.close, args.close))
                    gm = cv2.morphologyEx(gm.astype(np.uint8), cv2.MORPH_CLOSE, k) > 0
                if args.denoise:
                    gm = denoise_mask(gm, rel=0.002, min_px=60)
                if args.struct_guard and _S2T is not None and _S2T.convert(ch) != ch:
                    wm = render_base(wk_font, ch, 256) > 127
                    small = cv2.resize(gm.astype(np.uint8) * 255, (256, 256),
                                       interpolation=cv2.INTER_AREA) > 127
                    if abs(_comps(small) - _comps(wm)) > 2:
                        rm = _ribbon_mask(ch)
                        if rm is not None:
                            gm = rm
                            tag = "base"
                if args.hole_repair:
                    # kernels are in the 512 raster: twice the 300-dpi mask sizes
                    gm, _ = repair_counters(gm, ch, base_close=args.close,
                                            extra=(9, 15, 21, 27, 33, 39, 49, 59, 69),
                                            max_ink_gain=0.22, min_hole_area=6)
                if args.ink_normalize:
                    tgt = target_ink_256(ch, args.ink_a, args.ink_exp) * args.ink_gain
                    if tgt > 0:
                        ys, xs = np.nonzero(gm)
                        if len(ys) > 50:
                            w_px = float(xs.max() - xs.min() + 1)
                            h_px = float(ys.max() - ys.min() + 1)
                            k = 1000.0 / S2
                            bb = base_bounds(ch)
                            if bb:
                                we, he = w_px * k, h_px * k
                                tw, th = bb[2] - bb[0], bb[3] - bb[1]
                                sx = min(max((0.8 * tw + 0.2 * we) / max(1e-6, we), 0.8), 1.25)
                                sy = min(max((0.8 * th + 0.2 * he) / max(1e-6, he), 0.8), 1.25)
                                sc = k * 256.0 / 1000.0
                                gm = adjust_mask_area(gm, tgt / max(1e-6, sc * sx * sc * sy))
                # turdsize 3 (C): paper dust is already removed by denoise_mask, so the
                # speck filter only needs to drop true 1-2 px dust
                # speck contours.  A counter sealed by closing can be small, so the
                # denoise runs *before* the repair, never after.
                cs = trace(gm, turdsize=args.turdsize, alphamax=0.4, opttol=0.5)
                if not cs:
                    fb.append(ch)
                    continue
                em = raster_to_em(cs, S2)
                em = normalize_to_base(em, ch, blend=args.blend, min_scale=0.8, max_scale=1.25)
                if args.simplify > 0:
                    em = _simplify(em, args.simplify)
                fh.write(json.dumps({"char": ch, "contours": em, "src": tag},
                                    ensure_ascii=False) + "\n")
            done += 1
            if done % 10 == 0:
                print(f"  chunks {done}/{len(tasks)}", flush=True)
    (wd / "gan_fallback.json").write_text(json.dumps(fb, ensure_ascii=False))
    print(f"done {sum(1 for _ in open(args.out))} of {len(chars)}; fallback {len(fb)}", flush=True)


if __name__ == "__main__":
    main()
