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


_GAN_CACHE = None


def gan_chunk(args):
    """GAN output with a *cheap* guard: empty / ink out of band / components off by >3.

    This is deliberately NOT the E24 gate (counters must equal WenKai), which reverted 85%
    of glyphs. Here the GAN is trusted unless the output is obviously broken.
    """
    import importlib
    import cv2 as _cv
    import torch
    from PIL import ImageFont
    from generate_lib import render_base, ribbon_scale
    import importlib.util as iu
    torch.set_num_threads(1)      # one thread per worker
    try:
        import cv2 as _c2
        _c2.setNumThreads(1)
    except Exception:
        pass
    global _GAN_CACHE
    if _GAN_CACHE is None:
        spec = iu.spec_from_file_location("ganlib", ROOT / "scripts" / "21_train_gan.py")
        m = iu.module_from_spec(spec); spec.loader.exec_module(m)
        g = m.Generator()
        g.load_state_dict(torch.load(ROOT / "work" / "ckpt" / "m2_ep080.pt", map_location="cpu")["G"])
        g.eval()
        _GAN_CACHE = g
    gan = _GAN_CACHE
    bl = importlib.import_module("brush_lib")
    rel = np.load(ROOT / "work" / "stroke_rel_width.npy")
    lo, hi, chars, font_path, S = args
    font = ImageFont.truetype(font_path, S)
    out = []
    for ch in chars[lo:hi]:
        base = render_base(font, ch, S)
        wm = base > 127
        a = (base.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            # threshold -0.05: M2 sweep shows it puts median ink at 0.999
            # (threshold is a weak lever here: Dice varies only 0.547–0.554 across the range)
            g = gan(torch.from_numpy(a).float()).numpy()[0, 0] > -0.05
        # ---- cheap guard
        n, _l, st, _ = _cv.connectedComponentsWithStats(g.astype(np.uint8), 8)
        comps = sum(1 for i in range(1, n) if st[i, 4] >= 20)
        nw, _l2, sw, _ = _cv.connectedComponentsWithStats(wm.astype(np.uint8), 8)
        comps_w = sum(1 for i in range(1, nw) if sw[i, 4] >= 20)
        ink = float(g.sum()) / max(1.0, float(wm.sum()))
        ok = g.sum() > 200 and 0.6 <= ink <= 1.5 and abs(comps - comps_w) <= 3
        if not ok:
            fr = bl.glyph_frames(wm, S)
            rng = np.random.RandomState(ord(ch) % (2 ** 31))
            raw = rng.choice(rel, size=len(fr), replace=True); raw /= max(1e-6, raw.mean())
            w = np.power(raw, 1.4); w /= max(1e-6, w.mean())
            g = bl.render_ribbon(fr, scale=ribbon_scale(float(wm.sum())), dips=w,
                                 end_skew=0.9, taper=0.2, size=S, ss=2)
        out.append((ch, g, "gen" if ok else "base", ok))
    return lo, out


def gated_chunk(args):
    """GAN -> topology repair (vs content font) -> ribbon fallback, per chunk."""
    global _GAN_CACHE
    lo, hi, chars, font_path, S = args
    import importlib, importlib.util as iu

    import torch
    from PIL import ImageFont
    torch.set_num_threads(1)
    if _GAN_CACHE is None:
        spec = iu.spec_from_file_location("ganlib", ROOT / "scripts" / "21_train_gan.py")
        m = iu.module_from_spec(spec); spec.loader.exec_module(m)
        g = m.Generator()
        g.load_state_dict(torch.load(ROOT / "work" / "zi2zi_gan.pt", map_location="cpu")["G"])
        g.eval()
        _GAN_CACHE = g
    gan = _GAN_CACHE
    bl = importlib.import_module("brush_lib")
    rel = np.load(ROOT / "work" / "stroke_rel_width.npy")
    font = ImageFont.truetype(font_path, S)
    n = hi - lo
    out = np.zeros((n, S, S), np.uint8)
    okv = np.zeros(n, bool)

    def _holes(m, minarea=20):
        import cv2
        k, lab, stats, _ = cv2.connectedComponentsWithStats((~m).astype(np.uint8), 8)
        res = []
        for i in range(1, k):
            x, y, w, h, a = stats[i]
            if a < minarea or x <= 1 or y <= 1 or x + w >= m.shape[1] - 1 or y + h >= m.shape[0] - 1:
                continue
            res.append((a, (lab == i)))
        return res

    def _gate(m, ref, tiny=60):
        """Never reshape the glyph: fill only tiny speck holes, then accept or fall back."""
        hm, hr = _holes(m, 8), _holes(ref)
        if len(hm) > len(hr):
            for a, mask in hm:
                if a < tiny and not any((mask & rmask).any() for _, rmask in hr):
                    m |= mask
        return m

    for j, ch in enumerate(chars[lo:hi]):
        base = render_base(font, ch, S)
        ref = base > 127
        a = (base.astype(np.float32) / 127.5 - 1.0)[None].repeat(3, 0)[None]
        with torch.no_grad():
            # threshold -0.05: M2 sweep shows it puts median ink at 0.999
            # (threshold is a weak lever here: Dice varies only 0.547–0.554 across the range)
            g = gan(torch.from_numpy(a).float()).numpy()[0, 0] > -0.05
        g = _gate(g, ref)
        if len(_holes(g)) != len(_holes(ref)):
            fr = bl.glyph_frames(ref)
            rng = np.random.RandomState(ord(ch) % (2 ** 31))
            raw = rng.choice(rel, size=len(fr), replace=True)
            w = np.power(raw, 1.4); w = w / max(1e-6, float(w.mean()))
            from generate_lib import ribbon_scale as _rs
            g = bl.render_ribbon(fr, scale=_rs(float(ref.sum())), dips=w, end_skew=0.9, taper=0.2)
        out[j] = g.astype(np.uint8)
        okv[j] = True
    return lo, out, okv


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
            # The print's ink/WenKai ratio falls with complexity (0.99 at 10k px -> 0.76 at 22k),
            # so a single global scale makes simple glyphs too light and dense ones too heavy.
            # Fit on the 1,675 pairs: ratio = 20.619 * ink^-0.330; ribbon ink ~= 1.06 * scale.
            from generate_lib import ribbon_scale as _rs
            scale_i = _rs(float(bm.sum()))
            m = bl.render_ribbon(fr, scale=scale_i, dips=w,
                                 end_skew=0.9, taper=0.2, ss=ss).astype(np.uint8)
        else:
            m = bl.render_field(fr, scale=0.9, dips=ds, ss=ss).astype(np.uint8)
        # Structural guard: ribbon is built from the base skeleton, so structure is what
        # matters. The old IoU>=0.7 test rejected 20.9% of glyphs whose dip simply made them
        # thinner; accept instead whenever the topology (components + counters) is unchanged.
        def _topo(mask):
            import cv2 as _cv
            mb = mask.astype(bool)
            n, lab, st, _ = _cv.connectedComponentsWithStats(mb.astype(np.uint8), 8)
            comps = sum(1 for i in range(1, n) if st[i, 4] >= 20)
            nh, hl, hs, _ = _cv.connectedComponentsWithStats(((~mb).astype(np.uint8)), 8)
            holes = sum(1 for i in range(1, nh) if hs[i, 4] >= 20
                        and hs[i, 0] > 1 and hs[i, 1] > 1
                        and hs[i, 0] + hs[i, 2] < mask.shape[1] - 1
                        and hs[i, 1] + hs[i, 3] < mask.shape[0] - 1)
            return comps, holes
        inter = (m & bm).sum(); union = max(1, (m | bm).sum())
        iou = inter / union
        # accept when either the topology is intact or the shape is still close;
        # the old rule (IoU only) silently dropped the most strongly styled glyphs
        good = (_topo(m) == _topo(bm) or iou >= 0.7) and m.sum() > bm.sum() * 0.5
        out[k] = m if good else bm.astype(np.uint8)
        ok[k] = good
    return lo, out, ok


SIMPLIFY = 0.0


def _simplify(contours, eps):
    """Replace curves with a polyline and drop points within eps (font units)."""
    res = []
    for c in contours:
        pts = [np.array(c["start"], float)]
        for sg in c["segs"]:
            if sg[0] == "L":
                pts.append(np.array(sg[1:3], float))
            else:
                p0 = pts[-1]
                p1 = np.array(sg[1:3], float); p2 = np.array(sg[3:5], float); p3 = np.array(sg[5:7], float)
                n = max(2, int(np.linalg.norm(p3 - p0) / 1.5))
                for t in np.linspace(0, 1, n)[1:]:
                    u = 1 - t
                    pts.append(u ** 3 * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t ** 3 * p3)
        poly = np.array(pts, np.float32).reshape(-1, 1, 2)
        import cv2 as _cv
        ap = _cv.approxPolyDP(poly, eps, True).reshape(-1, 2)
        if len(ap) < 3:
            res.append(c)
            continue
        res.append({"start": [float(ap[0][0]), float(ap[0][1])],
                    "segs": [["L", float(p[0]), float(p[1])] for p in ap[1:]]})
    return res


def gen_chunk(args):
    """Single-phase worker: render mask -> structural guard -> trace -> em units.

    Runs at any resolution (--res), so the potrace half-pixel tax can be reduced
    by tracing at 512 instead of 256. No global mask array is needed.
    """
    lo, hi, chars, font_path, S, ss, mode = args
    import importlib
    import cv2 as _cv
    import torch as _torch
    bl = importlib.import_module("brush_lib")
    gl = importlib.import_module("generate_lib")
    cg = importlib.import_module("19_cap_geom")
    rel = np.load(ROOT / "work" / "stroke_rel_width.npy")
    font = ImageFont.truetype(font_path, S)
    out = []
    for k, ch in enumerate(chars[lo:hi]):
        bm = render_base(font, ch, S) > 127
        fr = bl.glyph_frames(bm, S)
        rng = np.random.RandomState(ord(ch) % (2 ** 31))
        ds = rng.choice(rel, size=len(fr), replace=True) if len(fr) else np.ones(max(1, len(fr)))
        ds = ds / max(1e-6, float(ds.mean()))
        w = np.power(ds, 1.4)
        w = w / max(1e-6, float(w.mean()))
        comp = float(bm.sum()) * (256.0 / S) ** 2          # complexity in 256-px units
        m = bl.render_ribbon(fr, scale=gl.ribbon_scale(comp), dips=w,
                             end_skew=0.9, taper=0.2, size=S, ss=ss).astype(np.uint8)

        def _topo(mask):
            mb = mask.astype(bool)
            n, _lab, st, _ = _cv.connectedComponentsWithStats(mb.astype(np.uint8), 8)
            comps = sum(1 for i in range(1, n) if st[i, 4] >= 20 * (S / 256.0) ** 2)
            nh, _hl, hs, _ = _cv.connectedComponentsWithStats((~mb).astype(np.uint8), 8)
            amin = 20 * (S / 256.0) ** 2
            holes = sum(1 for i in range(1, nh) if hs[i, 4] >= amin
                        and hs[i, 0] > 1 and hs[i, 1] > 1
                        and hs[i, 0] + hs[i, 2] < mask.shape[1] - 1
                        and hs[i, 1] + hs[i, 3] < mask.shape[0] - 1)
            return comps, holes

        inter = int((m & bm).sum()); union = max(1, int((m | bm).sum()))
        good = (_topo(m) == _topo(bm) or inter / union >= 0.7) and m.sum() > bm.sum() * 0.5
        keep = m if good else bm.astype(np.uint8)
        try:
            cs = trace(keep.astype(bool), turdsize=4, alphamax=0.4, opttol=0.25)
            if not cs:
                raise ValueError("empty trace")
            em = raster_to_em(cs, S)
        except Exception:
            continue
        if CAPS:
            try:
                hd = np.load(ROOT / "work" / "cap_h_fit.npy") * CAP_K
                em = cg.apply_caps(em, keep, hd, ord(ch))
            except Exception:
                pass
        em = normalize_to_base(em, ch, blend=1.0, min_scale=0.8, max_scale=1.25)
        if SIMPLIFY > 0:
            em = _simplify(em, SIMPLIFY)
        out.append((ch, em, "gen" if good else "base"))
    return lo, out


def trace_chunk(args):
    lo, hi, chars, tag = args
    masks = np.load(MASKFILE, mmap_mode="r")
    out = []
    for i in range(lo, hi):
        mask = np.array(masks[i]) > 0
        base_ok = tag["ok"][i]
        ch = chars[i]
        try:
            cs = trace(mask, turdsize=4, alphamax=0.4, opttol=0.25)
            if not cs:
                continue
            em = raster_to_em(cs, S)
        except Exception:
            try:
                from generate_lib import render_base as _rb
                from PIL import ImageFont as _IF
                _f = _IF.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S)
                mask2 = _rb(_f, ch, S) > 127
                cs = trace(mask2, turdsize=4, alphamax=0.4, opttol=0.25)
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
    ap.add_argument("--method", choices=["model", "brush", "field", "ribbon", "gan_gated", "gan"],
                    default="gan",
                    help="default = the shipped method (v1.5.0: GAN with a cheap guard); "
                         "ribbon is the fallback renderer and the v1.3.x shipped method")
    ap.add_argument("--field-ss", type=int, default=2)
    ap.add_argument("--simplify", type=float, default=0.0,
                    help="polygon simplification tolerance in font units (2.0 at 512px keeps quality, cuts nodes ~30%%)")
    ap.add_argument("--res", type=int, default=256,
                    help="render/trace resolution; 512 removes most of the potrace ink tax")
    ap.add_argument("--reuse-masks", action="store_true")
    ap.add_argument("--caps", action="store_true", help="apply vector cap replacement")
    ap.add_argument("--cap-k", type=float, default=1.2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    global CAPS, CAP_K, SIMPLIFY
    CAPS = bool(getattr(args, "caps", False))
    SIMPLIFY = float(getattr(args, "simplify", 0.0))
    CAP_K = float(getattr(args, "cap_k", 1.2))

    real = {json.loads(l)["label"] for l in open(ROOT / "work" / "chosen.jsonl")}
    chars = [chr(c) for c in range(BLOCK[0], BLOCK[1] + 1) if chr(c) not in real]
    if args.limit:
        chars = chars[: args.limit]
    print("to generate", len(chars), "method", args.method, flush=True)
    font = ImageFont.truetype(str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S)

    gan = None
    if args.method == "gan_gated":
        import torch
        import importlib.util as _iu
        _spec = _iu.spec_from_file_location("ganlib", ROOT / "scripts" / "21_train_gan.py")
        _m = _iu.module_from_spec(_spec); _spec.loader.exec_module(_m)
        gan = _m.Generator()
        gan.load_state_dict(torch.load(ROOT / "work" / "zi2zi_gan.pt", map_location="cpu")["G"])
        gan.eval()

    model = None
    if args.method == "model":
        import torch
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        model = UNet(base=32).to(device)
        model.load_state_dict(torch.load(args.ckpt, map_location=device))
        model.eval()

    if args.method == "gan":
        import multiprocessing as mp
        S2 = int(args.res)
        ctx = mp.get_context("fork")
        step = 40
        tasks = [(i, min(i + step, len(chars)), chars,
                  str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S2)
                 for i in range(0, len(chars), step)]
        fb = []
        done = 0
        with ctx.Pool(args.workers) as pool, open(args.out, "w") as fh:
            for lo, rows in pool.imap_unordered(gan_chunk, tasks):
                for ch, g, tag, ok in rows:
                    if not ok:
                        fb.append(ch)          # recorded, but ribbon contours are still emitted
                    cs = trace(g.astype(bool), turdsize=4, alphamax=0.4, opttol=0.5)
                    if not cs:
                        fb.append(ch); continue
                    em = raster_to_em(cs, S2)
                    em = normalize_to_base(em, ch, blend=1.0, min_scale=0.8, max_scale=1.25)
                    if SIMPLIFY > 0:
                        em = _simplify(em, SIMPLIFY)
                    fh.write(json.dumps({"char": ch, "contours": em, "src": tag},
                                        ensure_ascii=False) + "\n")
                done += 1
                if done % 20 == 0:
                    print(f"  chunks {done}/{len(tasks)}", flush=True)
        (ROOT / "work" / "gan_fallback.json").write_text(json.dumps(fb, ensure_ascii=False))
        print(f"done {sum(1 for _ in open(args.out))} of {len(chars)}; fallback {len(fb)}", flush=True)
        return

    if args.method in ("field", "ribbon", "gan_gated") and not args.reuse_masks:
        import multiprocessing as mp
        S2 = int(args.res)
        ctx = mp.get_context("fork")
        step = 60 if S2 >= 512 else (100 if args.method == "gan_gated" else 200)
        step = max(8, int(step * (256.0 / S2) ** 2)) if S2 > 256 else step
        tasks = [(i, min(i + step, len(chars)), chars,
                  str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf"), S2, args.field_ss,
                  args.method) for i in range(0, len(chars), step)]
        done = 0
        results = {}
        with ctx.Pool(args.workers) as pool, open(args.out, "w") as fh:
            for lo, rows in pool.imap_unordered(gen_chunk, tasks):
                results[lo] = rows
                while results and next(iter(sorted(results))) == min(results):
                    key = min(results)
                    for ch, em, tag in results.pop(key):
                        fh.write(json.dumps({"char": ch, "contours": em, "src": tag},
                                            ensure_ascii=False) + "\n")
                    done += 1
                if done % 10 == 0:
                    print(f"  chunks {done}/{len(tasks)} at {S2}px", flush=True)
        print(f"done {sum(1 for _ in open(args.out))} of {len(chars)} at {S2}px", flush=True)
        return

    masks = np.zeros((len(chars), S, S), dtype=np.uint8)
    ok = np.zeros(len(chars), dtype=bool)
    if args.reuse_masks and MASKFILE.exists():
        masks = np.load(MASKFILE)
        print("masks reused:", masks.shape, flush=True)

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
