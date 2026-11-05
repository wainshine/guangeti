"""C-line 大字实验: build build/GuanGeKai-C-Big-Regular.ttf (family `GuanGe Kai C Big`).

Forked from `79_build_full_c.py`.  Differences:

  * family/version are fixed here — the experiment must not read or write
    data/release-c.json, and 79's ABORT on non-canonical --out does not apply
    because the 42 punctuation glyphs are appended in-process instead of
    shelling out to `13_extend_punct.py --line C --inplace` (that script only
    knows the three canonical A/B/C paths);
  * --min-real defaults to 500: the 大字 chosen set has ~651 genuine glyphs,
    an order of magnitude fewer than the C line's 5,299.

EXPERIMENT artifact: nothing in the release flow consumes this font.  If the
experiment fails, delete build/GuanGeKai-C-Big-Regular.ttf and keep work-c-big/.

    python3 scripts/103_build_full_c_big.py
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fontbuild import build_font  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BLOCK = (0x4E00, 0x9FFF)
FAMILY = "GuanGe Kai C Big"
VERSION = "0.1.0-exp"
COPYRIGHT = ("GuanGe Kai C Big (館閣楷 C 大字实验). Real glyphs traced from the Ming manuscript "
             "永樂大典 (嘉靖隆慶間内府重寫本), Library of Congress 藏本 / digitised by "
             "the Library of Congress, distributed by 書格 shuge.org; 大字字頭 cells only. "
             "Generated glyphs derived from LXGW WenKai (OFL 1.1). "
             "Copyright 2026 The GuanGe Kai Project Authors. SIL OFL 1.1.")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    out = {}
    p = Path(path)
    if not p.exists():
        return out
    for line in open(p):
        r = json.loads(line)
        out[r["char"]] = r["contours"]
    return out


def extend_punct(font_path: Path) -> None:
    """Reuse 13_extend_punct.extend() verbatim: copy the 42 LXGW punct glyphs in place."""
    spec = importlib.util.spec_from_file_location(
        "extend_punct", ROOT / "scripts" / "13_extend_punct.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.extend(font_path, font_path, False, False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(ROOT / "work-c-big"))
    ap.add_argument("--out", default=str(ROOT / "build" / "GuanGeKai-C-Big-Regular.ttf"))
    ap.add_argument("--min-real", type=int, default=500)
    ap.add_argument("--no-punct", action="store_true")
    ap.add_argument("--allow-missing", action="store_true",
                    help="build even when coverage is incomplete (debug only)")
    args = ap.parse_args()
    wd = Path(args.work)
    real = load(wd / "real_contours.jsonl")
    gen = load(wd / "generated.jsonl")
    glyphs = {}
    for ch in sorted(set(real) | set(gen)):
        glyphs[ch] = real[ch] if ch in real else gen[ch]
    in_block = sum(1 for c in range(BLOCK[0], BLOCK[1] + 1) if chr(c) in glyphs)
    missing = (BLOCK[1] - BLOCK[0] + 1) - in_block
    print(f"real {len(real)} gen {len(gen)} total {len(glyphs)} "
          f"(basic block {in_block}/{BLOCK[1]-BLOCK[0]+1}) missing {missing}")
    if (len(real) < args.min_real or missing > 0) and not args.allow_missing:
        raise SystemExit(f"ABORT: real={len(real)} missing={missing} — refusing to write a "
                         f"font whose real glyphs are absent or whose coverage is incomplete")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    build_font(glyphs, out, family=FAMILY, style="Regular", version=VERSION,
               copyright_text=COPYRIGHT)
    punct = 0
    if not args.no_punct:
        extend_punct(out)
        from fontTools.ttLib import TTFont
        cm = TTFont(out).getBestCmap()
        punct = sum(1 for c in cm if not (BLOCK[0] <= c <= BLOCK[1]))
    man = dict(
        font=str(out), font_sha256=sha256(out), punctuation=punct,
        chosen_sha256=sha256(wd / "chosen.jsonl"),
        generated_sha256=(sha256(wd / "generated.jsonl")
                          if (wd / "generated.jsonl").exists() else ""),
        real_sha256=sha256(wd / "real_contours.jsonl"),
        real_count=len(real), gen_count=len(gen), total=len(glyphs),
        version=VERSION, family=FAMILY,
    )
    (wd / "build_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1))
    print("wrote", args.out)
    print(f"manifest -> {wd / 'build_manifest.json'}")


if __name__ == "__main__":
    main()
