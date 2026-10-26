"""B-line font-level acceptance: does the shipped TTF hold up as a font?

Metrics that only make sense at the *font* level (not per-glyph model output):

  ink_real / ink_syn   rendered ink area of the synthetic glyphs relative to the genuine
                       ones for the SAME characters (A-line E34's "17% too heavy" check)
  pos_dx / pos_dy      ink-centroid offset from the em box centre, synthetic vs genuine
  small_px             ink ratio at 12/16/24 px (does the weight bias depend on size?)
  fallback             share of characters drawn by the ribbon renderer
  coverage             CJK basic block coverage and the real-subset size

  python3 scripts/68_accept_b.py --font build/GuanGeKai-B-Regular.ttf
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BLOCK = (0x4E00, 0x9FFF)


S = 256          # canvas the book rasters live on (see 08_make_pairs.py)
EM_TOP = 880.0


def render_em(ch, font_path, S=S):
    """Render a character so that 1 em maps to S px with the baseline at 880/1000 S.

    This is the same em->canvas convention `08_make_pairs.render_base` uses, so the
    result is directly comparable with the book rasters in pairs.npz.
    """
    f = ImageFont.truetype(font_path, S)
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).text((0, EM_TOP * S / 1000.0), ch, fill=255, font=f, anchor="ls")
    return np.array(im) > 127


def ink_and_centroid(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return 0, 0.0, 0.0
    return int(len(xs)), float(xs.mean()), float(ys.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--font", default=str(ROOT / "build" / "GuanGeKai-B-Regular.ttf"))
    ap.add_argument("--real", default=str(ROOT / "build" / "GuanGeKai-B-Real.ttf"))
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--px", type=int, default=96)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    wd = Path(args.work)

    prov_p = wd / "provenance_for_accept.json"
    gen = {}
    for line in open(wd / "generated.jsonl"):
        r = json.loads(line)
        gen[r["char"]] = r.get("src", "gen")
    chosen = {json.loads(l)["label"] for l in open(wd / "chosen.jsonl")}
    # sort before sampling: generated.jsonl is written in pool-completion order
    # (audit 3-15), so the file order changes between runs and an unsorted list made
    # the 300-char sample — and therefore the bbox ratio — non-reproducible.
    syn = sorted(c for c in gen if c not in chosen)
    rng = np.random.RandomState(0)
    sample = [syn[i] for i in rng.choice(len(syn), min(args.n, len(syn)), replace=False)]

    f = TTFont(args.font)
    cm = f.getBestCmap()
    real_px = Path(args.real)
    have_real = real_px.exists()

    print(f"font {Path(args.font).name}: {len(cm)} cmap entries; "
          f"chosen {len(chosen)}; generated {len(gen)}; sampling {len(sample)} synthetic chars")

    # 1. weight: ink relative to the *content font* for the same character.
    #    Characters that were generated have no book glyph to compare against, so the
    #    honest normalisation is ink / WenKai-ink, which removes the "rare characters
    #    are simply denser" confound (the A-line E34/E35 lesson).
    WK = str(ROOT / "data" / "base" / "LXGWWenKai-Regular.ttf")

    def rel(ch, font):
        if ord(ch) not in cm:
            return None
        a, ax, ay = ink_and_centroid(render_em(ch, font))
        b, _, _ = ink_and_centroid(render_em(ch, WK))
        if b < 200 or a < 200:
            return None
        return a / b, (ax - S / 2) / S, (ay - S / 2) / S

    rs_syn, rs_real = [], []
    dxs, dys, dxr, dyr = [], [], [], []
    for ch in sample:
        v = rel(ch, args.font)
        if v:
            rs_syn.append(v[0]); dxs.append(v[1]); dys.append(v[2])
    for ch in sorted(chosen):
        v = rel(ch, args.font)
        if v:
            rs_real.append(v[0]); dxr.append(v[1]); dyr.append(v[2])
    if rs_syn and rs_real:
        b = float(np.median(rs_syn)) / float(np.median(rs_real))
        print(f"\nink / WenKai ink        synthetic {np.median(rs_syn):.3f} (n={len(rs_syn)})   "
              f"genuine {np.median(rs_real):.3f} (n={len(rs_real)})")
        print(f"=> synthetic weight bias  {b:.3f}x")
        print(f"centroid vs em centre   synthetic dx {np.median(dxs)*100:+.2f}% dy "
              f"{np.median(dys)*100:+.2f}%   genuine dx {np.median(dxr)*100:+.2f}% dy "
              f"{np.median(dyr)*100:+.2f}%  (em)")

    # 1b. glyph bbox size, synthetic vs genuine (A-line E37 found the GAN output bbox
    #     was 0.949 of the genuine one, which inflates weight after normalisation)
    def bbox(ch, font):
        m = render_em(ch, font)
        ys, xs = np.nonzero(m)
        if len(xs) < 50:
            return None
        return (xs.max() - xs.min()) / S, (ys.max() - ys.min()) / S

    bs, br = [], []
    for ch in sample:
        v = bbox(ch, args.font)
        if v:
            bs.append(v)
    for ch in sorted(chosen):
        v = bbox(ch, args.font)
        if v:
            br.append(v)
    bbox_ratio = None
    if bs and br:
        bs, br = np.array(bs), np.array(br)
        bbox_ratio = round(float(np.median(bs[:, 0]) / np.median(br[:, 0])), 3)
        print(f"\nbbox (em fraction)   synthetic w {np.median(bs[:,0]):.3f} h {np.median(bs[:,1]):.3f}"
              f"   genuine w {np.median(br[:,0]):.3f} h {np.median(br[:,1]):.3f}"
              f"   ratio w {bbox_ratio:.3f}")

    # 2. size dependence of the weight bias: ink / WenKai ink per group, per pixel size
    sizes = {}
    for px in (12, 16, 24, 48):
        def grp(chs):
            vals = []
            for ch in chs:
                if ord(ch) not in cm:
                    continue
                f1 = ImageFont.truetype(args.font, px)
                f2 = ImageFont.truetype(WK, px)
                im1 = Image.new("L", (px * 2, px * 2), 0)
                ImageDraw.Draw(im1).text((2, 2), ch, font=f1, fill=255, anchor="lt")
                im2 = Image.new("L", (px * 2, px * 2), 0)
                ImageDraw.Draw(im2).text((2, 2), ch, font=f2, fill=255, anchor="lt")
                a = int((np.array(im1) > 127).sum())
                b = int((np.array(im2) > 127).sum())
                if a >= 6 and b >= 6:
                    vals.append(a / b)
            return float(np.median(vals)) if vals else None
        a, b = grp(sample), grp(sorted(chosen)[:600])
        if a and b:
            sizes[px] = dict(syn=round(a, 3), real=round(b, 3), bias=round(a / b, 3))
    if sizes:
        print("size sweep (ink/WenKai, bias = syn/real):")
        for px, v in sizes.items():
            print(f"   {px:3d}px  syn {v['syn']:.3f}  real {v['real']:.3f}  bias {v['bias']:.3f}")

    # 3. fallback share and coverage
    fb = sum(1 for c, s in gen.items() if s != "gen")
    cov = sum(1 for c in range(*[BLOCK[0], BLOCK[1] + 1]) if c in cm)
    res = dict(
        font=str(Path(args.font)),
        codepoints_in_block=cov,
        coverage=round(cov / (BLOCK[1] - BLOCK[0] + 1), 4),
        chosen=len(chosen), generated=len(gen), ribbon_fallback=fb,
        fallback_share=round(fb / max(1, len(gen)), 4),
        syn_ink_over_wenkai=None if not rs_syn else round(float(np.median(rs_syn)), 3),
        real_ink_over_wenkai=None if not rs_real else round(float(np.median(rs_real)), 3),
        weight_bias=None if not rs_syn or not rs_real else
        round(float(np.median(rs_syn) / np.median(rs_real)), 3),
        syn_centroid_dx_pct=None if not dxs else round(float(np.median(dxs)) * 100, 2),
        syn_centroid_dy_pct=None if not dys else round(float(np.median(dys)) * 100, 2),
        real_centroid_dx_pct=None if not dxr else round(float(np.median(dxr)) * 100, 2),
        real_centroid_dy_pct=None if not dyr else round(float(np.median(dyr)) * 100, 2),
        bbox_w_ratio=bbox_ratio,
        size_sweep=sizes,
    )
    print("\nfallback share %.1f%%   coverage %d/%d" %
          (100 * res["fallback_share"], cov, BLOCK[1] - BLOCK[0] + 1))
    out = Path(args.out) if args.out else wd / "accept_b.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("->", out)

    # --- hard gates (audit 3-21: this script used to report without judging) ---
    fails = []
    if cov != BLOCK[1] - BLOCK[0] + 1:
        fails.append(f"coverage {cov}")
    wb = res.get("weight_bias")
    if wb is None or not (0.90 <= wb <= 1.15):
        fails.append(f"weight bias {wb} outside 0.90-1.15")
    if res["fallback_share"] is None or res["fallback_share"] > 0.12:
        fails.append(f"fallback share {res['fallback_share']} > 0.12")
    if res.get("bbox_w_ratio") and not (0.95 <= res["bbox_w_ratio"] <= 1.10):
        fails.append(f"bbox ratio {res['bbox_w_ratio']}")
    small = (res.get("size_sweep") or {}).get("12")
    if small and small.get("bias") and small["bias"] > 1.15:
        fails.append(f"12px weight bias {small['bias']} > 1.15")
    if fails:
        raise SystemExit("ACCEPTANCE FAILED: " + "; ".join(fails))
    print("ACCEPTANCE OK")


if __name__ == "__main__":
    main()
