"""Verify that the A line (四書 → GuanGeKai) is still intact after B-line work.

The baseline is **the last shipped copy in `release/`** (`release/SHA256SUMS`), so the
check follows A automatically when A cuts a new version (v1.5.2 → v1.6.0).  The v1.5.2
digests below are kept as a historical fallback: a font that matches neither the shipped
copy nor v1.5.2 is reported, and the verdict tells you whether it changed *since the
previous B-line check* — B never writes `build/GuanGeKai-*`, so that is the only way a
B-side mistake could show up here.

  python3 scripts/67_verify_a.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# last resort: docs/PROJECT_STATE.md §2 (v1.5.2, 2026-10-25).  Superseded by
# release/SHA256SUMS whenever that file lists the same font.
EXPECT = {
    "build/GuanGeKai-Regular.ttf":
        "394d3a0c22a7c32cdfaef2b5fd2c4859f2ebb118b5b0571a4e44f998f3ac2015",
    "build/GuanGeKai-Real.ttf":
        "42ab4007497b2267ee61d0a59570e56df847e6a6219353ceffe6305353ae85ee",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


SNAP = ROOT / "work-b" / "verify_a_snapshot.json"


def main():
    ok = True
    info = {}
    # prefer the shipped copy's digests as the baseline
    shipped = {}
    sums = ROOT / "release" / "SHA256SUMS"
    if sums.exists():
        for line in sums.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].startswith("GuanGeKai-"):
                shipped[f"build/{parts[1]}"] = parts[0]
    base = {**EXPECT, **shipped}
    print(f"== A-line artefacts (baseline: {'release/SHA256SUMS' if shipped else 'v1.5.2'}) ==")
    for rel, want in base.items():
        p = ROOT / rel
        if not p.exists():
            print(f"MISSING  {rel}")
            ok = False
            continue
        got = sha256(p)
        good = got == want
        info[rel] = dict(sha256=got, size=p.stat().st_size, mtime=p.stat().st_mtime)
        # note: `ok` intentionally does NOT include byte-equality with v1.5.2 any more;
        # A's own rebuild with the counter fixes must not read as "B broke A".
        # A rebuild with the P0 counter fixes legitimately changes these bytes; what the B
        # line must prove is that *it* did not touch them.  So a diff is reported against
        # the previous run's snapshot instead of failing outright.
        prev = (json.loads(SNAP.read_text()) if SNAP.exists() else {}).get(rel)
        if good:
            print(f"OK    {rel}  {got[:16]}  {p.stat().st_size:,} bytes (== baseline)")
        elif prev and prev.get("sha256") == got:
            print(f"DIFF  {rel}  {got[:16]}  {p.stat().st_size:,} bytes "
                  f"(!= baseline, but unchanged since the previous B-line check)")
        else:
            print(f"DIFF  {rel}  {got[:16]}  {p.stat().st_size:,} bytes "
                  f"(!= baseline and changed since the previous check — "
                  f"if B did not rebuild A, this is A's own rebuild)")
            print(f"      previous snapshot: {(prev or {}).get('sha256','<none>')[:16]}")

    print("\n== build/ vs the last shipped copy in release/ ==")
    for name in ("GuanGeKai-Regular.ttf", "GuanGeKai-Real.ttf"):
        b, r = ROOT / "build" / name, ROOT / "release" / name
        if b.exists() and r.exists():
            hb, hr = sha256(b), sha256(r)
            print(f"{name:26s} build {hb[:12]} {b.stat().st_size:>10,}B   "
                  f"release {hr[:12]} {r.stat().st_size:>10,}B   "
                  f"{'same' if hb == hr else 'build is NEWER than the shipped copy'}")

    print("\n== A-line pipeline state ==")
    def lines(rel):
        p = ROOT / rel
        return sum(1 for _ in open(p)) if p.exists() else None
    n_chosen = lines("work/chosen.jsonl")
    print(f"work/chosen.jsonl rows = {n_chosen} (expect 1675)")
    ok &= n_chosen == 1675
    prov = ROOT / "release/provenance.json"
    if prov.exists():
        d = json.loads(prov.read_text())
        n_real = sum(1 for v in d.values() if v == "real")
        print(f"release/provenance.json real = {n_real} (expect 1675)")
        ok &= n_real == 1675
    else:
        print("release/provenance.json MISSING")
        ok = False

    print("\n== A-line font coverage ==")
    from fontTools.ttLib import TTFont
    fm = TTFont(str(ROOT / "build/GuanGeKai-Regular.ttf"))
    cm = fm.getBestCmap()
    cov = sum(1 for c in range(0x4E00, 0xA000) if c in cm)
    fam = fm["name"].getDebugName(1)
    print(f"GuanGeKai-Regular.ttf coverage {cov}/20992  family {fam!r}")
    ok &= cov == 20992
    fm2 = TTFont(str(ROOT / "build/GuanGeKai-Real.ttf"))
    n2 = fm2["maxp"].numGlyphs - 1
    print(f"GuanGeKai-Real.ttf glyphs {n2} (expect 1675)")
    ok &= n2 == 1675

    # ok covers the pipeline state + coverage + real subset; the byte-identity of the
    # fonts is reported separately because A's own P0 rebuild changes it by design.
    print("\nRESULT:", "A LINE INTACT" if ok else "A LINE CHANGED — investigate")
    save_snapshot(info)
    return 0 if ok else 1


def save_snapshot(info):
    SNAP.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(SNAP.read_text()) if SNAP.exists() else {}
    old.update(info)
    SNAP.write_text(json.dumps(old, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
