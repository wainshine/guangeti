"""Assemble the release folder, checksums, coverage and provenance."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
BLOCK = (0x4E00, 0x9FFF)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "release"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    full = ROOT / "build" / "GuanGeKai-Regular.ttf"
    real = ROOT / "build" / "GuanGeKai-Real.ttf"
    for f in (full, real):
        shutil.copy2(f, out / f.name)
    shutil.copy2(ROOT / "OFL.txt", out / "OFL.txt")
    if (ROOT / "LICENSE").exists():
        shutil.copy2(ROOT / "LICENSE", out / "LICENSE")
    shutil.copy2(ROOT / "README.md", out / "README.md")
    # only the two user-facing figures; analysis panels stay in the repo
    for name in ("specimen.png", "book-vs-font.png"):
        img = ROOT / "docs" / "images" / name
        if img.exists():
            shutil.copy2(img, out / name)
    # the packaged README sits next to the images, so strip the docs/images/ prefix
    rp = out / "README.md"
    if rp.exists():
        rp.write_text(rp.read_text(encoding="utf-8").replace("docs/images/", ""), encoding="utf-8")

    real_chars = {json.loads(l)["label"] for l in open(ROOT / "work" / "chosen.jsonl")}
    # three-way provenance: GAN output vs ribbon fallback (guard triggered) vs real
    gen_kind = {}
    for l in open(ROOT / "work" / "generated.jsonl"):
        r = json.loads(l)
        gen_kind[r["char"]] = "gan" if r.get("src") == "gen" else "ribbon_fb"
    provenance = {}
    for c in range(BLOCK[0], BLOCK[1] + 1):
        ch = chr(c)
        provenance[ch] = ("real" if ch in real_chars
                          else gen_kind.get(ch, "missing"))
    (out / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False))

    f = TTFont(full)
    cmap = f.getBestCmap()
    covered = [chr(c) for c in range(BLOCK[0], BLOCK[1] + 1) if c in cmap]
    (out / "coverage.txt").write_text("".join(covered))
    stats = dict(
        codepoints=len(covered),
        real=sum(1 for v in provenance.values() if v == "real"),
        generated=sum(1 for v in provenance.values() if v in ("gan", "ribbon_fb")),
        gan=sum(1 for v in provenance.values() if v == "gan"),
        ribbon_fallback=sum(1 for v in provenance.values() if v == "ribbon_fb"),
        missing=sum(1 for v in provenance.values() if v == "missing"),
        upm=f["head"].unitsPerEm,
        glyphs=f["maxp"].numGlyphs,
        file_bytes=full.stat().st_size,
        real_file_bytes=real.stat().st_size,
    )
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    lines = [f"{sha256(p)}  {p.name}" for p in sorted(out.glob("*")) if p.is_file() and p.name != "SHA256SUMS"]
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
