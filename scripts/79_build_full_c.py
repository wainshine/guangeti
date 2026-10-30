"""C-line: build the complete font build/GuanGeKai-C-Regular.ttf.

Forked from `62_build_full_b.py`; family name `GuanGe Kai C`, work-c paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fontbuild import build_font  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "work-c"
BLOCK = (0x4E00, 0x9FFF)
FAMILY = "GuanGe Kai C"
def _version():
    try:
        return json.loads((ROOT / "data" / "release-c.json").read_text())["version"]
    except Exception:
        return "1.1.0"


VERSION = _version()
COPYRIGHT = ("GuanGe Kai C (館閣楷 C). Real glyphs traced from the Ming manuscript "
             "永樂大典 (嘉靖隆慶間内府重寫本), Library of Congress 藏本 / digitised by "
             "the Library of Congress, distributed by 書格 shuge.org. "
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(WB))
    ap.add_argument("--out", default=str(ROOT / "build" / "GuanGeKai-C-Regular.ttf"))
    ap.add_argument("--min-real", type=int, default=1000)
    ap.add_argument("--no-punct", action="store_true",
                    help="do not append the 42 punctuation/digit/space glyphs")
    ap.add_argument("--allow-missing", action="store_true",
                    help="dry-run only: build even when coverage is incomplete")
    args = ap.parse_args()
    wd = Path(args.work)
    real = load(wd / "real_contours.jsonl")
    gen = load(wd / "generated.jsonl")
    glyphs = {}
    # Every genuine glyph we have goes in, even the handful outside the basic block
    # (5 extension-A forms); the block itself is still checked to be complete below.
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
    build_font(glyphs, out, family=FAMILY, style="Regular", version=VERSION,
               copyright_text=COPYRIGHT)
    punct = 0
    if not args.no_punct and out.resolve() != (ROOT / "build" / "GuanGeKai-C-Regular.ttf").resolve():
        raise SystemExit("ABORT: non-canonical --out would silently skip the 42 punctuation glyphs; "
                         "build to build/GuanGeKai-C-Regular.ttf or pass --no-punct")
    if not args.no_punct:
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "scripts" / "13_extend_punct.py"),
                        "--line", "C", "--inplace"], check=True)
        from fontTools.ttLib import TTFont
        cm = TTFont(out).getBestCmap()
        punct = sum(1 for c in cm if not (BLOCK[0] <= c <= BLOCK[1]))
    # Build manifest: pins the exact inputs this font was built from.  `81_package_c.py`
    # compares these hashes instead of mtimes, so a later regeneration of generated.jsonl
    # cannot silently be paired with an older font (the v1.0.1 packaging incident).
    man = dict(
        font=str(out), font_sha256=sha256(out), punctuation=punct,
        chosen_sha256=sha256(wd / "chosen.jsonl"),
        generated_sha256=sha256(wd / "generated.jsonl"),
        real_sha256=(sha256(wd / "real_contours.jsonl")
                     if (wd / "real_contours.jsonl").exists() else ""),
        real_count=len(real), gen_count=len(gen), total=len(glyphs),
        version=VERSION,
    )
    (wd / "build_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1))
    print("wrote", args.out)
    print(f"manifest -> {wd / 'build_manifest.json'}")


if __name__ == "__main__":
    main()
