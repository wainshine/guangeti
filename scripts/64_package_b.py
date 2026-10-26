"""B-line: assemble release-b/, provenance, coverage, stats and checksums.

Forked from `14_package.py`; the A-line release/ directory is never touched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
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
    ap.add_argument("--work", default=str(ROOT / "work-b"))
    ap.add_argument("--out", default=str(ROOT / "release-b"))
    ap.add_argument("--readme", default=str(ROOT / "README-B.md"))
    args = ap.parse_args()
    wd = Path(args.work)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    full = ROOT / "build" / "GuanGeKai-B-Regular.ttf"
    real = ROOT / "build" / "GuanGeKai-B-Real.ttf"
    # --- freshness gate (audit P1-4): packaging a stale font against newer inputs is
    # exactly how the v1.5.1 "0 synthetic glyphs" incident slipped through.
    srcs = [wd / "chosen.jsonl", wd / "generated.jsonl", full, real]
    missing_src = [str(p) for p in srcs if not p.exists()]
    if missing_src:
        raise SystemExit("ABORT: packaging inputs missing: " + ", ".join(missing_src))
    # Each font depends on a different input set: the full font needs both files, the
    # real subset only chosen.jsonl.  Comparing both against both was a false positive.
    deps = {full: (wd / "chosen.jsonl", wd / "generated.jsonl"),
            real: (wd / "chosen.jsonl",)}
    for f, ins in deps.items():
        newest = max((p.stat().st_mtime, p.name) for p in ins)
        if f.stat().st_mtime < newest[0] - 1:
            raise SystemExit(
                f"ABORT: {f.name} is older than {newest[1]} "
                f"({time.strftime('%H:%M', time.localtime(f.stat().st_mtime))} < "
                f"{time.strftime('%H:%M', time.localtime(newest[0]))}) — "
                f"rebuild the font before packaging")
    for f in (full, real):
        shutil.copy2(f, out / f.name)
    shutil.copy2(ROOT / "OFL.txt", out / "OFL.txt")
    if (ROOT / "LICENSE").exists():
        shutil.copy2(ROOT / "LICENSE", out / "LICENSE")
    readme = Path(args.readme)
    if readme.exists():
        shutil.copy2(readme, out / "README.md")
        # the packaged README sits next to the images, so strip the docs/images/ prefix
        # (same rule as 14_package.py); otherwise every <img> in the package is broken
        rp = out / "README.md"
        txt = rp.read_text(encoding="utf-8")
        rp.write_text(txt.replace("docs/images/", ""), encoding="utf-8")
    for name in ("specimen-b.png", "book-vs-font-b.jpg"):
        img = ROOT / "docs" / "images" / name
        if not img.exists():
            raise SystemExit(f"ABORT: release figure missing: {img}")
        shutil.copy2(img, out / name)

    real_chars = {json.loads(l)["label"] for l in open(wd / "chosen.jsonl")}
    gen_kind = {}
    KNOWN_SRC = {"gen", "gen_ht", "base"}   # primary gan / hard-tail gan / ribbon fallback
    bad_src = set()
    for l in open(wd / "generated.jsonl"):
        r = json.loads(l)
        src = r.get("src")
        if src not in KNOWN_SRC:
            bad_src.add(src)
        gen_kind[r["char"]] = {"gen": "gan", "gen_ht": "gan_ht"}.get(src, "ribbon_fb")
    if bad_src:
        raise SystemExit(f"ABORT: unknown provenance tags {sorted(bad_src)} "
                         f"(whitelist {sorted(KNOWN_SRC)})")
    provenance = {}
    for c in range(BLOCK[0], BLOCK[1] + 1):
        ch = chr(c)
        provenance[ch] = ("real" if ch in real_chars else gen_kind.get(ch, "missing"))
    # the five genuine glyphs outside the basic block are in the font too; the audit
    # (3-20) pointed out they were absent from provenance/stats
    ext = sorted(ch for ch in real_chars if not (BLOCK[0] <= ord(ch) <= BLOCK[1]))
    for ch in ext:
        provenance[ch] = "real"
    (out / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False))

    f = TTFont(full)
    cmap = f.getBestCmap()
    covered = [chr(c) for c in range(BLOCK[0], BLOCK[1] + 1) if c in cmap]
    (out / "coverage.txt").write_text("".join(covered))
    stats = dict(
        codepoints=len(covered),
        real=sum(1 for v in provenance.values() if v == "real"),
        real_basic=sum(1 for k, v in provenance.items() if v == "real"
                        and BLOCK[0] <= ord(k) <= BLOCK[1]),
        real_ext_a=len(ext),
        generated=sum(1 for v in provenance.values() if v in ("gan", "ribbon_fb")),
        gan=sum(1 for v in provenance.values() if v == "gan"),
        gan_ht=sum(1 for v in provenance.values() if v == "gan_ht"),
        ribbon_fallback=sum(1 for v in provenance.values() if v == "ribbon_fb"),
        missing=sum(1 for v in provenance.values() if v == "missing"),
        upm=f["head"].unitsPerEm,
        glyphs=f["maxp"].numGlyphs,
        file_bytes=full.stat().st_size,
        real_file_bytes=real.stat().st_size,
        family=f["name"].getDebugName(1),
    )
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    if stats["missing"]:
        raise SystemExit(f"ABORT: {stats['missing']} block codepoints have no provenance")
    if stats["codepoints"] != BLOCK[1] - BLOCK[0] + 1:
        raise SystemExit(f"ABORT: coverage {stats['codepoints']} != {BLOCK[1]-BLOCK[0]+1}")
    for k in ("real", "gan", "ribbon_fallback"):
        if stats[k] == 0:
            raise SystemExit(f"ABORT: {k} count is 0 — provenance is broken")
    lines = [f"{sha256(p)}  {p.name}" for p in sorted(out.glob("*"))
             if p.is_file() and p.name != "SHA256SUMS"]
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
