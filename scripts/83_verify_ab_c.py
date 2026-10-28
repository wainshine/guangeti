"""C-line gate: prove that building C did not touch the shipped A and B lines.

The C line writes only work-c/, build/GuanGeKai-C-*, release-c/ and the *-C.md
documents.  This script verifies that claim from the artefacts themselves rather than
from good intentions:

  * byte identity of the four shipped TTFs against release/SHA256SUMS (A v1.6.5)
    and release-b/SHA256SUMS (B v1.2.1);
  * pipeline invariants that would break if a shared script changed behaviour with
    default arguments (A chosen 1,675 / B chosen 4,078, both fonts at 20,992);
  * the release archives named in DATA.md, when present.

It also snapshots the four TTF hashes into work-c/ab_baseline.json; a later run
reports "changed since the baseline" separately from "changed since the release",
which is the difference between "C broke it" and "the owner rebuilt A/B on purpose".

  python3 scripts/83_verify_ab_c.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work-c"

A_FONTS = ["GuanGeKai-Regular.ttf", "GuanGeKai-Real.ttf"]
B_FONTS = ["GuanGeKai-B-Regular.ttf", "GuanGeKai-B-Real.ttf"]
# zip hashes are release-time snapshots: they change when a package is rebuilt,
# which is expected.  Update them in the same commit as the release.
ZIPS = {"GuanGeKai-v1.7.0.zip": "f7b3d25f2120003045e3b930c1b17df4b5331f42c07b1858c9e8f0b1b92f2b36",
        "GuanGeKai-B-v1.2.2.zip": "d9da537640fbac12003ea2d1a13323cdda9187ff9f5bce49fb5e10095ff4b491"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sums(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[1]] = parts[0]
    return out


def main():
    ok = True
    issues = []
    info = {"fonts": {}, "checks": {}}

    sa = sums(ROOT / "release" / "SHA256SUMS")
    sb = sums(ROOT / "release-b" / "SHA256SUMS")
    for name, want in [(n, sa.get(n)) for n in A_FONTS] + [(n, sb.get(n)) for n in B_FONTS]:
        p = ROOT / "build" / name
        if not p.exists():
            issues.append(f"MISSING {name}")
            ok = False
            continue
        got = sha256(p)
        status = "OK" if got == want else ("NO-BASELINE" if not want else "DIFF")
        if status == "DIFF":
            issues.append(f"{name} differs from its release checksum")
            ok = False
        info["fonts"][name] = dict(sha256=got, want=want, status=status,
                                   bytes=p.stat().st_size)
        print(f"{status:11s} {name:28s} {got[:16]}  {p.stat().st_size:,} B")

    from fontTools.ttLib import TTFont
    def coverage(path):
        f = TTFont(str(path))
        cm = f.getBestCmap()
        return sum(1 for c in range(0x4E00, 0xA000) if c in cm), f["name"].getDebugName(1)

    def n_real(path):
        return TTFont(str(path))["maxp"].numGlyphs - 1

    def lines(path):
        return sum(1 for _ in open(path)) if path.exists() else -1

    checks = {
        "A coverage": (coverage(ROOT / "build/GuanGeKai-Regular.ttf")[0], 20992),
        "A real glyphs": (n_real(ROOT / "build/GuanGeKai-Real.ttf"), 1675),
        "A chosen": (lines(ROOT / "work/chosen.jsonl"), 1675),
        "A provenance real": (sum(1 for v in json.loads(
            (ROOT / "release/provenance.json").read_text()).values() if v == "real"), 1675),
        "B coverage": (coverage(ROOT / "build/GuanGeKai-B-Regular.ttf")[0], 20992),
        "B real glyphs": (n_real(ROOT / "build/GuanGeKai-B-Real.ttf"), 4078),
        "B chosen": (lines(ROOT / "work-b/chosen.jsonl"), 4078),
        "B provenance real": (sum(1 for v in json.loads(
            (ROOT / "release-b/provenance.json").read_text()).values() if v == "real"), 4078),
    }
    for k, (got, want) in checks.items():
        good = got == want
        ok &= good
        if not good:
            issues.append(f"{k}: {got} != {want}")
        print(f"{'OK' if good else 'FAIL':11s} {k:22s} {got} (expect {want})")
    info["checks"] = {k: dict(got=v[0], want=v[1], ok=v[0] == v[1])
                      for k, v in checks.items()}

    fam_a = coverage(ROOT / "build/GuanGeKai-Regular.ttf")[1]
    fam_b = coverage(ROOT / "build/GuanGeKai-B-Regular.ttf")[1]
    info["families"] = {"A": fam_a, "B": fam_b}
    print(f"{'OK' if fam_a == 'GuanGe Kai' else 'FAIL':11s} A family {fam_a!r}")
    print(f"{'OK' if fam_b == 'GuanGe Kai B' else 'FAIL':11s} B family {fam_b!r}")
    ok &= fam_a == "GuanGe Kai" and fam_b == "GuanGe Kai B"

    for z, want in ZIPS.items():
        p = ROOT / z
        if not p.exists():
            print(f"{'WARN':11s} {z} not present")
            continue
        got = sha256(p)
        if want:
            good = got == want
            ok &= good
            print(f"{'OK' if good else 'FAIL':11s} {z} {got[:16]}")
            if not good:
                issues.append(f"{z} hash {got[:16]} != {want[:16]}")
        else:
            print(f"{'INFO':11s} {z} {got[:16]} (no recorded baseline)")

    base_p = WORK / "ab_baseline.json"
    base = json.loads(base_p.read_text()) if base_p.exists() else {}
    changed_since_base = [n for n in info["fonts"]
                          if base.get(n) and base[n] != info["fonts"][n]["sha256"]]
    info["changed_since_baseline"] = changed_since_base
    if changed_since_base:
        print("CHANGED since the previous C-line check:", changed_since_base)
    info["ok"] = bool(ok)
    info["issues"] = issues
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "verify_ab.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    snap = {n: v["sha256"] for n, v in info["fonts"].items()}
    base.update(snap)
    base_p.write_text(json.dumps(base, ensure_ascii=False, indent=1))
    print("\nRESULT:", "A/B INTACT" if ok else "A/B CHANGED — investigate before release")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
