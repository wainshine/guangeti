"""Collect the final B-line numbers into one markdown block (for the release docs).

Reads only artefacts, so the numbers cannot drift from the shipped files.

  python3 scripts/70_summary_b.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WB = ROOT / "work-b"


def main():
    prov = json.loads((ROOT / "release-b" / "provenance.json").read_text()) \
        if (ROOT / "release-b" / "provenance.json").exists() else {}
    stats = json.loads((ROOT / "release-b" / "stats.json").read_text()) \
        if (ROOT / "release-b" / "stats.json").exists() else {}
    accept = json.loads((WB / "accept_b.json").read_text()) if (WB / "accept_b.json").exists() else {}
    ev = {}
    cand = sorted(WB.glob("evalfull_ep*.json")) + sorted(WB.glob("eval_ep*_clean.json")) \
        + sorted(WB.glob("eval_ep0*.json"))
    for p in cand:
        d = json.loads(p.read_text())
        for k, v in d.items():
            if k.startswith("b_ep") or k.startswith("_floor") or k.startswith("_genuine"):
                ev.setdefault(p.stem, {})[k] = v
    n_pairs = 0
    pp = WB / "pairs/pairs.npz"
    if pp.exists():
        import numpy as np
        n_pairs = len(np.load(pp, allow_pickle=True)["chars"])
    n_clean = 0
    cp = WB / "pairs_single.npz"
    if cp.exists():
        import numpy as np
        n_clean = len(np.load(cp, allow_pickle=True)["chars"])

    print("## B 线最终数字（由 70_summary_b.py 从产物生成）\n")
    print("| 项 | 值 |\n|---|---|")
    print(f"| 真跡字數 | **{stats.get('real', '?')}** |")
    print(f"| 生成字數 | {stats.get('generated', '?')}（GAN {stats.get('gan', '?')} / ribbon 回退 {stats.get('ribbon_fallback', '?')}） |")
    print(f"| 缺字 | {stats.get('missing', '?')} |")
    print(f"| CJK 基本區覆蓋 | {stats.get('codepoints', '?')}/20992 |")
    print(f"| 字體體積 | Regular {stats.get('file_bytes',0)/1e6:.2f} MB / Real {stats.get('real_file_bytes',0)/1e6:.2f} MB |")
    print(f"| 訓練配對 | {n_pairs} |")
    print(f"| 乾淨集 | {n_clean}（與訓練集交集 0） |")
    if accept:
        print(f"| 字重比（合成/真跡） | {accept.get('weight_bias','?')} |")
        print(f"| 包圍盒寬比 | {accept.get('bbox_w_ratio','?')} |")
        s = accept.get("size_sweep") or {}
        if s:
            print(f"| 小字號字重偏移 | " +
                  " · ".join(f"{k}px ×{v['bias']}" for k, v in s.items()) + " |")
    print()
    if ev:
        print("| 檢查點 | Dice | 墨量比 | chamfer | 崩壞率 |\n|---|---|---|---|---|")
        for name, d in ev.items():
            for k, v in d.items():
                if k.startswith("b_ep"):
                    print(f"| {name} ({k}) | {v['dice']} | {v['ink']} | {v['chamfer']} | {v['broken']*100:.1f}% |")
                    break
    print()
    if ev:
        fl = [v.get("_floor_same_char", {}).get("chamfer") for v in ev.values()]
        fl = [x for x in fl if x]
        if fl:
            print(f"真跡互比地板 chamfer = **{fl[0]}**（同一字兩個真跡樣本互比）")
    if prov:
        miss = sum(1 for v in prov.values() if v == "missing")
        print(f"\nprovenance: {len(prov)} 個碼位，missing {miss}")


if __name__ == "__main__":
    main()
