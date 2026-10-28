"""Check terminology & naming rules across docs, code and packaged files.

Single source of truth: `docs/GLOSSARY.md`.  Migration plan: `docs/CONVENTIONS.md`.
What will deliberately NOT be fixed: `docs/ERRATA.md`.

Checks
------
1. 《四书白文》 is a manuscript (写本), not a block print.  Flags 「刻本」 and the
   carving vocabulary (刻刀 / 刀刻 / 雕版 / 版刻 / 摹刻 / 翻刻), plus the English
   `woodblock|block-print|blockprint`.
2. Technical routes are `ribbon` / `zi2zi-GAN` / `zi2zi-JiT`.  Flags `路线 A/B/C`
   and `方案 A/B/C` (A/B/C belong to the glyph lines).
3. `R0/R0b/R1–R7` are gate-rule ids (`scripts/30_gate_rules.py`).  Any other use of
   `R<digit>` in docs/scripts is reported: the routes must not reuse them.

Explicit opt-out (no keyword guessing)
--------------------------------------
A line that legitimately uses a banned word (e.g. 「通行本是刻本系统」) carries:

    ... 通行本是刻本系统。 <!-- term-ok -->

The marker silences that line only.  A keyword heuristic was tried first and it hid
real errors (see docs/CONVENTIONS.md §9).

Known legacy (reported, never fails the run)
--------------------------------------------
* `build/GuanGeKai*.ttf` name tables still say `woodblock print` — the binaries are
  frozen at v1.6.5; rebuilding would change hashes (docs/ERRATA.md E2).
* `release*/README.md`, `release*/specimen.png` are packaged snapshots (ERRATA.md E3/E4).

Exit code 1 when a non-whitelisted, non-legacy hit exists, so it can gate a release.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Whole-file exemptions: these files must be able to quote the banned forms.
FULL_WHITELIST = {
    "scripts/97_check_terms.py",     # patterns and docstring quote the terms
    "docs/GLOSSARY.md",              # the normative table shows 禁止 forms
    "docs/CONVENTIONS.md",           # migration plan quotes old → new
    "docs/ERRATA.md",                # errata records the wrong wording
    "scripts/30_gate_rules.py",      # gate-rule ids live here by design
}
# History: published release notes and audit reports are not rewritten.
PREFIX_WHITELIST = ("docs/RELEASE-", "docs/releases/", "docs/AUDIT-")
# Legacy binaries / packaged snapshots: reported separately, never fatal.
LEGACY_PREFIX = ("build/", "release/", "release-b/", "release-c/")

OPT_OUT = "<!-- term-ok -->"

TERMS = [
    ("刻本", re.compile(r"刻本")),
    ("刻刀/刀刻", re.compile(r"刻刀|刀刻|雕版|版刻|摹刻|翻刻")),
    ("woodblock", re.compile(r"woodblock|block-print|blockprint", re.I)),
    ("路线 A/B/C", re.compile(r"路线\s*[ABC](?![0-9A-Za-z])")),
    ("方案 A/B/C", re.compile(r"方案\s*[ABC](?![0-9A-Za-z])")),
]
GATE_ID = re.compile(r"(?<![A-Za-z0-9_])R(?:0b?|[1-9])(?![0-9A-Za-z_])")


class Report:
    def __init__(self) -> None:
        self.hard: list[tuple[str, str, int, str]] = []
        self.legacy: list[tuple[str, str, int, str]] = []
        self.skipped: set[str] = set()
        self.opted_out = 0

    def add(self, rel: str, kind: str, ln: int, text: str) -> None:
        bucket = self.legacy if rel.startswith(LEGACY_PREFIX) else self.hard
        bucket.append((rel, kind, ln, text))


def _skip_file(rel: str) -> bool:
    return rel in FULL_WHITELIST or rel.startswith(PREFIX_WHITELIST)


def scan_text(path: Path, rel: str, rep: Report) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return
    for i, line in enumerate(lines, 1):
        if OPT_OUT in line:
            if any(rx.search(line) for _n, rx in TERMS):
                rep.opted_out += 1
            continue
        for name, rx in TERMS:
            if rx.search(line):
                rep.add(rel, name, i, line.strip()[:120])
        # gate-id reuse: the gate table's own rows ("| R1 ... |") are legitimate
        if GATE_ID.search(line) and not line.lstrip().startswith("| R"):
            rep.add(rel, "R 编号与闸门判据冲突", i, line.strip()[:120])


def scan_fonts(rep: Report) -> None:
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        print("  ! fontTools 不可用，跳过字体元数据检查", file=sys.stderr)
        return
    for ttf in sorted((ROOT / "build").glob("GuanGeKai*.ttf")):
        rel = str(ttf.relative_to(ROOT))
        try:
            font = TTFont(str(ttf), lazy=True)
        except Exception:
            continue
        seen: set[tuple[int, str]] = set()
        for rec in font["name"].names:
            if rec.nameID not in (0, 1, 4, 5, 10):
                continue
            try:
                txt = str(rec)
            except Exception:
                continue
            if (rec.nameID, txt) in seen:      # Mac/Win platform duplicates
                continue
            seen.add((rec.nameID, txt))
            for name, rx in TERMS:
                if name in ("刻本", "刻刀/刀刻", "woodblock") and rx.search(txt):
                    rep.add(rel, f"font {name}", rec.nameID, txt[:120])
                    break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    rep = Report()
    targets: list[Path] = []
    targets += sorted(ROOT.glob("*.md"))
    targets += sorted((ROOT / "docs").glob("*.md"))
    targets += sorted((ROOT / "scripts").glob("*.py"))
    for d in ("release", "release-b", "release-c"):
        targets += sorted((ROOT / d).glob("README.md"))

    for p in dict.fromkeys(targets):
        rel = str(p.relative_to(ROOT))
        if _skip_file(rel):
            rep.skipped.add(rel)
            continue
        scan_text(p, rel, rep)
    scan_fonts(rep)

    def dump(title: str, rows: list[tuple[str, str, int, str]]) -> None:
        by_file: dict[str, list] = {}
        for rel, kind, ln, text in rows:
            by_file.setdefault(rel, []).append((kind, ln, text))
        print(f"{title} — {len(rows)} 处，见 {len(by_file)} 个文件")
        for rel in sorted(by_file):
            print(f"  {rel}  ({len(by_file[rel])})")
            if not args.quiet:
                for kind, ln, text in by_file[rel][:8]:
                    print(f"      [{kind}] line {ln}: {text}")

    if rep.legacy:
        print()
        dump("已知遗留（不影响退出码；见 docs/ERRATA.md E2/E3/E4）", rep.legacy)

    if rep.hard:
        print()
        dump("TERMS FAILED", rep.hard)
        print("\n修法：docs/GLOSSARY.md §4；合法例外在该行尾加 <!-- term-ok -->。")
        print("历史文件加白名单，不改历史。")
        sys.exit(1)

    note = ""
    if rep.skipped:
        note += f"；白名单 {len(rep.skipped)} 个文件未扫"
    if rep.opted_out:
        note += f"；{rep.opted_out} 行显式豁免"
    print(f"\nTERMS OK （除白名单与已知遗留外一致{note}）")


if __name__ == "__main__":
    main()
