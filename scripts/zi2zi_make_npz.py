"""Build an inference npz for the full CJK basic block with zi2zi-JiT's pipeline."""
import sys, os, json, random, argparse
import numpy as np
from PIL import Image
from tqdm import tqdm

REPO = os.path.join(os.path.dirname(__file__), '..', 'data', 'vendor', 'zi2zi-JiT')
sys.path.insert(0, REPO)
from data_processing.font_utils import GlyphRenderer, load_font, get_cjk_codepoints  # noqa
sys.path.insert(0, os.path.join(REPO, 'scripts'))
from create_gb2312_npz import extract_ref, load_train_info  # noqa

ap = argparse.ArgumentParser()
ap.add_argument("--train_dir", required=True)
ap.add_argument("--source_font", required=True)
ap.add_argument("--output", required=True)
ap.add_argument("--min_cp", type=lambda x: int(x, 16), default=0x4E00)
ap.add_argument("--max_cp", type=lambda x: int(x, 16), default=0x9FFF)
ap.add_argument("--max_chars", type=int, default=None)
ap.add_argument("--ref_size", type=int, default=128)
ap.add_argument("--ref_index", type=int, default=0)
ap.add_argument("--resolution", type=int, default=256)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

fonts = load_train_info(args.train_dir)
assert fonts, "no train fonts"
fi = fonts[0]
trained = set(fi["train_codepoints"])
src_font, src_path = load_font(args.source_font)
src_cps = get_cjk_codepoints(src_font)
cps = [c for c in range(args.min_cp, args.max_cp + 1)
       if c in src_cps and c not in trained]
if args.max_chars:
    cps = cps[:args.max_chars]
print("target chars", len(cps))

renderer = GlyphRenderer(str(src_path), args.resolution)
n = len(cps)
font_labels = np.zeros(n, np.int64)
char_labels = np.arange(n, dtype=np.int64)
unicode_labels = np.array(cps, np.int64)
content = np.empty((n, 3, args.resolution, args.resolution), np.uint8)
style = np.empty((n, 3, args.ref_size, args.ref_size), np.uint8)
train_imgs = fi["train_images"]
keys = list(train_imgs.keys())
rng = random.Random(args.seed)
ref_cache = {}
for k in keys:
    ref_cache[k] = extract_ref(Image.open(train_imgs[k]).convert("RGB"), args.ref_index, args.ref_size)
for i, cp in enumerate(tqdm(cps)):
    img = renderer.render(cp)
    content[i] = np.array(img).transpose(2, 0, 1) if img is not None else 255
    k = rng.choice(keys)
    style[i] = np.array(ref_cache[k]).transpose(2, 0, 1)
os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
np.savez_compressed(args.output, font_labels=font_labels, char_labels=char_labels,
                    unicode_labels=unicode_labels, content_images=content,
                    style_images=style, num_original_samples=np.int64(n))
print("saved", args.output, round(os.path.getsize(args.output)/1e6, 1), "MB")
