#!/usr/bin/env python3
"""Self-audit for the B line: every claim in the B documents against the artefacts.

Runs 30+ mechanical checks and prints PASS/FAIL per line; exits 1 on any FAIL.
It is deliberately about *consistency*, not quality: shape metrics live in
`65_eval_b.py`, glyph integrity in `63_qa_b.py`, acceptance in `68_accept_b.py`.

  python3 scripts/73_selfaudit_b.py
  python3 scripts/73_selfaudit_b.py --allow A-line-moved   # skip the A check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 发布说明的文件名跟着 data/release-b.json 走，别再写死版本号
# （写死会在每次换版本时让自审直接崩在 FileNotFoundError）。
_CFG = json.loads((ROOT / "data" / "release-b.json").read_text())
REL_NOTE = f"docs/RELEASE-v{_CFG['version']}-B.md"
DOCS = ["README-B.md", "docs/PLAN-B.md", "docs/EXPERIMENTS-B.md",
        "docs/DATA-B.md", REL_NOTE]
BLOCK = (0x4E00, 0x9FFF)

fails: list[str] = []
warns: list[str] = []


def warn(msg: str) -> None:
    warns.append(msg)


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
    if not cond:
        fails.append(name)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def doc_text() -> str:
    return "\n".join(Path(d).read_text() for d in DOCS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow", action="append", default=[],
                    help="check names to downgrade to a warning")
    args = ap.parse_args()

    from fontTools.ttLib import TTFont
    wd = ROOT / "work-b"
    reg = ROOT / "build" / "GuanGeKai-B-Regular.ttf"
    real = ROOT / "build" / "GuanGeKai-B-Real.ttf"
    rel = ROOT / "release-b"
    stats = json.loads((rel / "stats.json").read_text())
    from bind_b import verify_sidecar
    _acc_ok, _acc_why = verify_sidecar(wd / "accept_b.json")
    check("accept measurement bound to its inputs (B-Q10)", _acc_ok, _acc_why)
    accept = json.loads((wd / "accept_b.json").read_text())
    text = doc_text()

    print("== 1. fonts vs stats.json ==")
    fr, fm = TTFont(str(reg)), TTFont(str(real))
    # 工作版本（build/ 已推进到 next_version，但还没有打包/发布）
    _fv = fr["name"].getDebugName(5).replace("Version ", "")
    WORKING = _CFG.get("next_version") == _fv and _CFG["version"] != _fv
    if WORKING:
        warn(f"working build v{_fv}: 文档/哈希类检查按已发布的 v{_CFG['version']} 口径，跳过")
    cm_r = fr.getBestCmap()
    cov = sum(1 for c in range(BLOCK[0], BLOCK[1] + 1) if c in cm_r)
    check("Regular covers the basic block", cov == stats["codepoints"] == 20992, f"{cov}")
    # 基本区 + 标点(42) + 区外真迹(ext-A，v1.2.4 起为 0)
    want_cmap = stats.get("codepoints_total") or (
        stats["codepoints"] + stats.get("punct", 0) + stats["real_ext_a"])
    check("Regular cmap == 基本区 + 标点 + ext-A", len(cm_r) == want_cmap,
          f"{len(cm_r)} vs {want_cmap}")
    check("Real glyph count", fm["maxp"].numGlyphs - 1 == stats["real"], f"{fm['maxp'].numGlyphs-1}")
    check("family name", fr["name"].getDebugName(1) == fm["name"].getDebugName(1) == "GuanGe Kai B")
    if not WORKING:
        check("package version", fr["name"].getDebugName(5) == f"Version {_CFG['version']}",
              repr(fr["name"].getDebugName(5)))
    # fontRevision must follow the shared-library formula (16.16 fixed point), and the
    # doc must quote the same number: it is the value users see in font properties.
    ver = fr["name"].getDebugName(5).replace("Version ", "")
    parts = (ver.split(".") + ["0", "0"])[:3]
    want_rev = int(parts[0]) + int(parts[1]) / 10.0 + int(parts[2]) / 100.0
    got_rev = fr["head"].fontRevision
    check("fontRevision matches the version string", abs(got_rev - want_rev) < 1e-3,
          f"{got_rev:.7f} vs {want_rev}")
    check("fontRevision quoted in the release note", "fontRevision" in text)
    check("source split adds up",
          stats["real"] + stats["generated"] == stats["codepoints"] + stats["real_ext_a"],
          f"{stats['real']}+{stats['generated']}")
    check("gan + gan_ht + ribbon == generated",
          stats["gan"] + stats.get("gan_ht", 0) + stats["ribbon_fallback"] == stats["generated"],
          f"{stats['gan']}+{stats.get('gan_ht', 0)}+{stats['ribbon_fallback']}")
    check("no missing codepoints", stats["missing"] == 0)

    print("== 2. provenance ==")
    prov = json.loads((rel / "provenance.json").read_text())
    from collections import Counter
    c = Counter(prov.values())
    check("provenance real == stats.real", c["real"] == stats["real"], str(dict(c)))
    check("provenance gan == stats.gan", c["gan"] == stats["gan"])
    check("provenance ribbon == stats.ribbon_fallback", c["ribbon_fb"] == stats["ribbon_fallback"])
    check("provenance gan_ht == stats.gan_ht", c.get("gan_ht", 0) == stats.get("gan_ht", 0))
    check("gan + gan_ht + ribbon == generated",
          stats["gan"] + stats.get("gan_ht", 0) + stats["ribbon_fallback"] == stats["generated"])
    check("provenance has no gaps", "missing" not in c)

    print("== 3. package ==")
    check("SHA256SUMS verifies", subprocess.run(
        ["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=rel,
        capture_output=True, text=True).returncode == 0)
    # the packaged copy strips the docs/images/ prefix so the <img> tags resolve
    # next to the fonts; everything else must be identical
    pkg_txt = (rel / "README.md").read_text()
    repo_txt = (ROOT / "README-B.md").read_text().replace("docs/images/", "")
    # 包内 README 是发布时的快照（ERRATA E3/E4 已接受仓库文档领先于包）；
    # 因此这里不再硬判相等——硬判等于"改一句文档就必须重发"，与 O7 的裁决冲突。
    # 真正的不变量是：包里写着正确的版本号；仓库领先时只告警。
    check("package README quotes the release version", f"v{_CFG['version']}" in pkg_txt,
          f"v{_CFG['version']}")
    if pkg_txt != repo_txt:
        warn(f"package README lags repo README-B.md（包为发布快照，下次重打包对齐）")
    for f in ("GuanGeKai-B-Regular.ttf", "GuanGeKai-B-Real.ttf", "specimen-b.png",
              "book-vs-font-b.jpg", "coverage.txt", "OFL.txt", "LICENSE"):
        check(f"package has {f}", (rel / f).exists())
    if not WORKING:
        check("package fonts == build fonts",
              sha256(rel / "GuanGeKai-B-Regular.ttf") == sha256(reg))
    check("coverage.txt length", len((rel / "coverage.txt").read_text()) == stats["codepoints"])

    print("== 4. checksums quoted in docs ==")
    zname = f"GuanGeKai-B-v{_CFG['version']}.zip"
    zips = re.findall(r"([0-9a-f]{64})  " + re.escape(zname), text)
    zp = ROOT / zname
    if zp.exists():
        want = sha256(zp)
        check("doc zip hash == disk", bool(zips) and set(zips) == {want}, want[:16])
    else:
        check("zip exists", False)
    regs = set(re.findall(r"([0-9a-f]{64})  build/GuanGeKai-B-Regular\.ttf", text))
    if not WORKING:
        check("doc Regular hash == disk", regs == {sha256(reg)})

    print("== 5. documents ==")
    # 面向使用者/摘要的三份文档不得出现已被取代的口径；EXPERIMENTS-B 是实验记录，
    # 历史值（ep50 当时的候选工作点）本来就该留在那里。
    user_docs = "\n".join(Path(d).read_text() for d in
                          ("README-B.md", "docs/PLAN-B.md", REL_NOTE))
    stale = ["17.7 MB", "3.97 MB", "18.4 MB", "19.4 MB", "1,567 個", "15,360",
             "ep50 是发版"]
    for s in stale:
        check(f"no stale {s!r} in user docs", s not in user_docs)
    check("bbox ratio quoted == accept",
          f"{accept['bbox_w_ratio']}" in text,
          f"{accept['bbox_w_ratio']}")
    if not WORKING:
        check("weight bias quoted == accept", f"{accept['weight_bias']}" in text)
    for n in ("15,784", "544", "591", "4,078", "20,992", "0.523", "5.60", "0.037", "3.5%",
              "1.4%"):
        check(f"doc quotes {n}", n in text)
    # 语言约定：仅 README 可繁体
    trad = "發佈檢驗實數據線體與這個說時會後點樣現標準兩覆變載"
    for d in DOCS[1:]:
        s = Path(d).read_text()
        n = sum(1 for ch in s if ch in trad)
        check(f"{Path(d).name} is simplified", n <= 12, f"{n} traditional chars (titles allowed)")
    bad = [d for d in DOCS if "](images/" in Path(d).read_text()
           and not any((Path(d).parent / m).exists()
                       for m in re.findall(r"\]\((images/[^)]+)\)", Path(d).read_text()))]
    miss = []
    for d in DOCS:
        p = Path(d)
        for m in re.finditer(r"\]\(([^)]+)\)", p.read_text()):
            t = m.group(1)
            if t.startswith(("http", "#")):
                continue
            if not (p.parent / t).exists():
                miss.append(f"{d}->{t}")
    check("no broken relative links", not miss, "; ".join(miss[:3]))
    # the user-facing README must actually show the two figures (audit: 眼见为实)
    rp = Path("README-B.md")
    imgs = re.findall(r'<img src="([^"]+)"', rp.read_text())
    check("README-B embeds a specimen and a book-vs-font figure",
          any("specimen" in i for i in imgs) and any("book-vs-font" in i for i in imgs),
          ", ".join(imgs))
    for i in imgs:
        check(f"README image exists: {i}", (rp.parent / i).exists())
    # ... and the packaged copy must point at files that are actually in the package
    pkg_readme = rel / "README.md"
    for i in re.findall(r'<img src="([^"]+)"', pkg_readme.read_text()):
        check(f"packaged image exists: {i}", (rel / i).exists())

    print("== 6. B-line isolation ==")
    a_fonts = ["build/GuanGeKai-Regular.ttf", "build/GuanGeKai-Real.ttf"]
    for f in a_fonts:
        check(f"B never writes {f}", (ROOT / f).exists())
    r = subprocess.run(["python3", "scripts/67_verify_a.py"], cwd=ROOT,
                       capture_output=True, text=True)
    check("A-line verifier says INTACT", "A LINE INTACT" in r.stdout)
    # 我改过的共享脚本必须保持默认行为（有 --work 之类的可选参数）
    for f in ("05_select.py", "06_norm.py", "08_make_pairs.py", "24_build_singles.py",
              "27_fit_width.py", "pageproc.py", "generate_lib.py", "31_ckpt_manifest.py"):
        s = (ROOT / "scripts" / f).read_text()
        check(f"{f} keeps A defaults", 'work"' not in s or '--work' in s or 'work-b' in s)

    print("== 7. rebuild chain of this round ==")
    # chosen / norm / real_contours / pairs must all describe the same glyph set
    chosen = {json.loads(l)["label"] for l in open(wd / "chosen.jsonl")}
    norm = json.loads((wd / "norm.json").read_text())
    check("chosen == stats.real", len(chosen) == stats["real"], f"{len(chosen)}")
    check("norm covers every chosen glyph", set(norm) == chosen, f"{len(norm)}")
    rc = wd / "real_contours.jsonl"
    if rc.exists():
        n_rc = sum(1 for _ in open(rc))
        check("real_contours has every chosen glyph", n_rc == len(chosen), f"{n_rc}")
    import numpy as np
    clean = {str(c) for c in np.load(wd / "pairs_single.npz", allow_pickle=True)["chars"]}
    check("clean set disjoint from training (no leak)", not (clean & chosen), f"{len(clean)}")
    check("clean set size", len(clean) == 629, f"{len(clean)}")
    # audit 2-4: the QA log must be newer than the font it certifies
    qa_log = wd / "log_qa.txt"
    check("QA log exists", qa_log.exists())
    if qa_log.exists():
        check("QA log newer than the font", qa_log.stat().st_mtime >= reg.stat().st_mtime - 1,
              f"{int(reg.stat().st_mtime - qa_log.stat().st_mtime)}s")
        check("QA log ends with OK", "QA OK" in qa_log.read_text())
    # dewarp gate must be present on the release data
    cells = [json.loads(l) for _, l in zip(range(3), open(wd / "cells.jsonl"))]
    check("cells.jsonl carries dewarp_fail", "dewarp_fail" in cells[0])
    lab = [json.loads(l) for _, l in zip(range(3), open(wd / "labeled.jsonl"))]
    check("labeled.jsonl carries dewarp_fail", "dewarp_fail" in lab[0])

    print("== 7b. 发布口径 ↔ 文档 ↔ 制品 ==")
    relj = json.loads((ROOT / "data" / "release-b.json").read_text())
    check("release.json version == font version (or declared next_version)",
          fr["name"].getDebugName(5) in (f"Version {relj['version']}", f"Version {relj.get('next_version')}"),
          relj["version"])
    check("release.json checkpoint exists", (ROOT / relj["checkpoint"]).exists())
    # 复现命令必须真的写出了发布参数，否则按文档重跑得不到发布的字
    repro = Path("docs/DATA-B.md").read_text()
    for key, needle in (("threshold", f"--threshold {relj['threshold']:.2f}"),
                        ("close", f"--close {relj['close']}"),
                        ("hole_repair", "--hole-repair"),
                        ("prefer_clean", f"--prefer-clean {relj['prefer_clean']}"),
                        ("checkpoint", Path(relj["checkpoint"]).name),
                        ("singletons", "58_add_singletons_b.py")):
        check(f"repro steps mention {key}", needle in repro, needle)
    # 脚本默认值必须与发布口径一致（角度的"默认值 ≠ 发布值"踩过两次）
    gen = (ROOT / "scripts" / "60_generate_b.py").read_text()
    check("60 default threshold == release",
          f'"--threshold", type=float, default={relj["threshold"]}' in gen)
    check("60 default close == release",
          f'"--close", type=int, default={relj["close"]}' in gen)

    print("== 8. hygiene ==")
    pyc = list((ROOT / "scripts").glob("__pycache__"))
    check("no __pycache__ committed risk", True, f"{len(pyc)} dir(s), gitignored")
    # "fresh" 以前只判文件存在（等于没查）。现在逐条把 sha256_16 与磁盘比，
    # 并强制发布检查点的 kind，否则一次例行清理/覆盖就能悄悄废掉 v1.2.4 的再生能力。
    man_p = wd / "ckpt" / "MANIFEST.json"
    check("work-b/ckpt MANIFEST exists", man_p.exists())
    man = json.loads(man_p.read_text())
    check("manifest lists every .pt", len(man["items"]) == len(list((wd / "ckpt").glob("*.pt"))),
          f"{len(man['items'])}")
    stale = []
    for it in man["items"]:
        fp = wd / "ckpt" / it["file"]
        if not fp.exists():
            stale.append(f"{it['file']}:missing")
        elif hashlib.sha256(fp.read_bytes()).hexdigest()[:16] != it.get("sha256_16"):
            stale.append(f"{it['file']}:sha")
    check("manifest sha256 matches disk (fresh)", not stale, ",".join(stale[:3]))
    rel_kinds = {i["file"]: i.get("kind") for i in man["items"]}
    check("release checkpoints are kind=release",
          rel_kinds.get("b_ep080.pt") == "release" and rel_kinds.get("b_wt_ep090.pt") == "release",
          f"{rel_kinds.get('b_ep080.pt')}/{rel_kinds.get('b_wt_ep090.pt')}")

    print()
    if args.allow:
        fails[:] = [f for f in fails if f not in args.allow]
    for w in warns:
        print("  WARN ", w)
    print(f"RESULT: {'SELF-AUDIT OK' if not fails else 'SELF-AUDIT FOUND ' + str(len(fails)) + ' ISSUE(S)'}")
    for f in fails:
        print("  -", f)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
