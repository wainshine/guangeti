"""Re-render ribbon-fallback glyphs with the corrected 256px ink normalisation."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import ImageFont
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import brush_lib as B
from generate_lib import render_base, ribbon_scale, raster_to_em
from glyphvec import trace, normalize_to_base

S = 512
font = ImageFont.truetype(str(ROOT / "data/base/LXGWWenKai-Regular.ttf"), S)
rel = np.load(ROOT / "work/stroke_rel_width.npy")
rows = [json.loads(l) for l in open(ROOT / "work/generated.jsonl")]
out = []
n = 0
for r in rows:
    if r.get("src") == "gen":
        out.append(r); continue
    ch = r["char"]
    wm = render_base(font, ch, S) > 127
    fr = B.glyph_frames(wm, S)
    rng = np.random.RandomState(ord(ch) % (2 ** 31))
    raw = rng.choice(rel, size=len(fr), replace=True); raw /= max(1e-6, raw.mean())
    w = np.power(raw, 1.4); w /= max(1e-6, w.mean())
    comp256 = float(wm.sum()) * (256.0 / S) ** 2
    m = B.render_ribbon(fr, scale=ribbon_scale(comp256), dips=w, end_skew=0.9, taper=0.2, size=S, ss=2)
    cs = trace(m.astype(bool), turdsize=2, alphamax=0.4, opttol=0.5)
    if not cs:
        out.append(r); continue
    em = normalize_to_base(raster_to_em(cs, S), ch, blend=1.0, min_scale=0.8, max_scale=1.25)
    out.append({"char": ch, "contours": em, "src": "base"}); n += 1
    if n % 200 == 0: print(n, flush=True)
(ROOT / "work/generated.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n")
print("re-rendered", n, "of", len(rows))
