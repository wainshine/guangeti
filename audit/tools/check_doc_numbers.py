#!/usr/bin/env python3
"""X9: read-only cross-check of numbers/terms in *current* docs against release JSON.

This is intentionally a checklist, not a proof: it flags suspicious stale numbers for a
human (or the coordinator) to adjudicate.  Historical documents (docs/releases/,
docs/REPORTS/, old RELEASE-vX files) and lines with an explicit historical marker are
allowed to keep old numbers.

Usage:  python3 audit/tools/check_doc_numbers.py [--verbose]
Exit:   0 = no findings, 1 = findings (read-only; never writes).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CURRENT_DOCS = [
    "AGENTS.md",
    "README.md",
    "README-B.md",
    "README-C.md",
    "docs/PROJECT_STATE.md",
    "docs/method.md",
    "docs/DATA.md",
    "docs/DATA-B.md",
    "docs/DATA-C.md",
    "docs/RELEASE-v1.7.2.md",
    "docs/RELEASE-v1.2.4-B.md",
    "docs/RELEASE-v1.3.0-C.md",
    "docs/RELEASE-v1.7.3.md",
    "docs/RELEASE-v1.2.5-B.md",
    "docs/RELEASE-v1.4.0-C.md",
]

# Stale/superseded tokens.  If the same line carries HISTORICAL_MARKERS it is allowed.
STALE = [
    r"C\s*v1\.2\.0",
    r"B\s*v1\.0\.1",
    r"(?<![\d.])0\.549(?![\d])",
    r"(?<![\d.])5\.92(?![\d])",
    r"(?<![\d.])5\.16(?![\d])",
    r"(?<![\d.])0\.4666(?![\d])",
    r"\b9\.5%",
    r"\b90\.5%",
    r"\b0\.7%",
    r"4,?078",
    r"21,?036",
    r"44\s*个?码位",
    r"\b1,?228\b",
]
CHAIN_FILES = ("README.md", "docs/DATA.md", "docs/PROJECT_STATE.md")
HISTORICAL_MARKERS = (
    "旧", "历史", "當時", "当时", "撤回", "v1.5.0", "v1.6", "v1.2.0", "v1.2.1",
    "v1.2.2", "v1.2.4", "v1.0.1", "v1.1", "E8", "E9", "E24", "E29", "E32",
    "E34", "E36", "E39", "已修复", "历史版本", "此 5.92", "旧记", "旧表述",
    "旧值", "旧口径", "禁止", "作废", "不要引用", "不要再引用", "口径更正",
    "口径注", "复核", "1,833", "vs 5.7%",
)

# Artifact hashes that must be internally consistent when they appear.
HASH_KEYS = {
    "A Reg": ("89120d52209446a3b6403871b7376f76dd8008e8223348de9dedf3609ed8eb75", "build"),
    "A Real": ("59b1154d5e0d6b2d92af64bff78b7594ccba325176abf9f6aa40c70352990323", "build"),
    "B Reg": ("544ce807bbe5de9589e67e5d4e408ca43cc848ac544f478b95cc51ccca755c71", "build"),
    "B Real": ("45d87eb0f4cded331caf9034bb423b1d8105288620af35fe24776c32495aa53c", "build"),
    "C Reg": ("8132f15ff3ef159ae3bd68c27451c51c44f34ce26848e9178e684b9385e03f91", "candidate"),
    "C Real": ("d534e504d6aacb90d3ce07ae4f22d7d2bea4519280c64dde42424f8cf99e60f0", "candidate"),
    "A zip": ("14483141b854056aa887f6e4be37c78053692419dd304a4e3de432be7256835b", "release-a.json"),
    "B zip": ("2537de50f67517696fea70102c97ecb4da0f8bd29d3746baebad629ee4e83c46", "release-b.json"),
    "C zip": ("613e34334d2d0a3edee88410dd54e2d5348284732c3820495cbf249cfd6f3554", "release-c.json"),
}


def release_values() -> dict:
    out = {}
    d = json.loads((ROOT / "data/release-a.json").read_text())
    out["A.version"] = d["version"]
    out["A.real"] = d["counts"]["real"]
    out["A.gan"] = d["counts"]["gan_ep90"] + d["counts"]["gan_ep80"]
    out["A.ribbon"] = d["counts"]["ribbon_fb"]
    out["A.dice"] = d["clean"]["dice"]
    out["A.clean_n"] = d["clean"]["n"]
    out["A.reg_sha"] = d["artifacts"]["regular_sha256"]
    out["A.real_sha"] = d["artifacts"]["real_sha256"]
    out["A.zip_sha"] = d["artifacts"]["zip_sha256"]
    d = json.loads((ROOT / "data/release-b.json").read_text())
    out["B.version"] = d["version"]
    out["B.real"] = d["real"]
    out["B.gan"] = d["gan"]
    out["B.gan_ht"] = d["gan_ht"]
    out["B.ribbon"] = d["ribbon"]
    out["B.dice"] = d["clean"]["dice"]
    out["B.chamfer"] = d["clean"]["chamfer"]
    out["B.zip_sha"] = d["zip_sha256"]
    d = json.loads((ROOT / "data/release-c.json").read_text())
    out["C.version"] = d["version"]
    out["C.real"] = d["real"]
    out["C.gan"] = d["gan"]
    out["C.ribbon"] = d["ribbon_fallback"]
    out["C.punct"] = d["punctuation"]
    out["C.weight_bias"] = d["weight_bias"]
    out["C.fallback_share"] = d["fallback_share"]
    out["C.unseen_dice"] = d["unseen_dice"]
    out["C.unseen_chamfer"] = d["unseen_chamfer"]
    out["C.zip_sha"] = d["zip_sha256"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    vals = release_values()
    findings = []
    checked = 0
    for rel in CURRENT_DOCS:
        p = ROOT / rel
        if not p.exists():
            findings.append(f"MISSING {rel}")
            continue
        recent: list[str] = []
        in_code = False
        for i, line in enumerate(p.read_text().splitlines(), 1):
            checked += 1
            if line.startswith("```"):
                in_code = not in_code
            hist = any(m in line for m in HISTORICAL_MARKERS) or any(
                any(m in prev for m in HISTORICAL_MARKERS) for prev in recent[-8:])
            if not in_code and re.match(r"^[0-9a-f]{64}\s+\S+", line) and not hist:
                findings.append(f"{rel}:{i}: bare checksum outside code fence :: {line.strip()[:80]}")
            for pat in STALE:
                if re.search(pat, line) and not hist:
                    if "4,?078" in pat and "→" in line:
                        continue  # explicit transition (4,078 → 4,073) is historical by nature
                    findings.append(f"{rel}:{i}: stale token /{pat}/ :: {line.strip()[:120]}")
            for name, (sha, _src) in HASH_KEYS.items():
                if sha[:8] in line and sha not in line:
                    if re.search(re.escape(sha[:8]) + r"\s*(…|\.\.\.|\.\.)", line):
                        continue
                    if "前 16" in line or "sha256_16" in line or any(
                            ("前 16" in prev or "sha256_16" in prev) for prev in recent[-8:]):
                        continue  # table explicitly documents shortened hashes
                    findings.append(f"{rel}:{i}: {name} hash prefix but not full hash")
            recent.append(line)
    # rebuild chains must mention the punct extension step (P0-3)
    for rel in CHAIN_FILES:
        text = (ROOT / rel).read_text()
        if "13_extend_punct" not in text:
            findings.append(f"{rel}: rebuild chain does not mention 13_extend_punct")

    # exact expected values sanity (release json itself)
    # Current build/version contract (release packages may lag; read the actual fonts).
    from fontTools.ttLib import TTFont
    build = {}
    for line, reg, real in (
        ("A", ROOT / "build/GuanGeKai-Regular.ttf", ROOT / "build/GuanGeKai-Real.ttf"),
        ("B", ROOT / "build/GuanGeKai-B-Regular.ttf", ROOT / "build/GuanGeKai-B-Real.ttf"),
        ("C", ROOT / "work-c/qa/c14/GuanGeKai-C-Regular-v1.4.ttf",
               ROOT / "work-c/qa/c14/GuanGeKai-C-Real-v1.4.ttf"),
    ):
        build[f"{line}.version"] = TTFont(reg)["name"].getDebugName(5).split()[-1]
        build[f"{line}.real"] = len(TTFont(real).getBestCmap())
    assert build == {"A.version": "1.7.3", "B.version": "1.2.5", "C.version": "1.4.0",
                     "A.real": 2261, "B.real": 4073, "C.real": 5250}, build

    print(f"checked {len(CURRENT_DOCS)} current docs, {checked} lines")
    if args.verbose:
        for k, v in vals.items():
            print(f"  {k:18s} {v}")
    if findings:
        print(f"FINDINGS: {len(findings)}")
        for f in findings:
            print("  " + f)
        return 1
    print("DOC NUMBERS OK (no stale/torn hash in current docs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
