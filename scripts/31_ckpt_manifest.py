"""Regenerate work/ckpt/MANIFEST.json from what is actually on disk.

Run after every training run: checkpoints get overwritten in place, so a manifest
written before a run goes stale and its sha256 entries stop matching.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CKPT_DIR = ROOT / "work" / "ckpt"
CK = ROOT / "work" / "ckpt"
# 该文件已于 2026-10-24 22:05 删除（见 DATA §6.5.1），条目保留用于说明历史
CORE_EPOCHS = {50, 100, 150, 200, 300, 400, 500}


def kind_of(name: str) -> str:
    """Classify a checkpoint for the retention rule (owner, 2026-10-25)."""
    import re as _re
    if name.endswith("_best.pt"):
        return "best"
    m = _re.search(r"_ep(\d+)\.pt$", name)
    if m:
        return "core" if int(m.group(1)) in CORE_EPOCHS else "snapshot"
    return "final"


INVALID = {"zi2zi_gan_multi_g_best.pt": "训练于 2026-10-24 05:27，用的是坏数据集"
                                       "（多实例配对 71% 目标空白），模型不可用，仅作记录"}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt-dir", default=str(CKPT_DIR),
                    help="checkpoint directory (the B line uses work-b/ckpt)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    ck = Path(args.ckpt_dir)
    out_path = Path(args.out) if args.out else ck / "MANIFEST.json"
    items = []
    for p in sorted(ck.glob("*.pt")):
        items.append({
            "file": p.name,
            "kind": kind_of(p.name),
            "size_mb": round(p.stat().st_size / 1e6, 1),
            "sha256_16": hashlib.sha256(p.read_bytes()).hexdigest()[:16],
            "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime)),
            "status": "invalid" if p.name in INVALID else "ok",
        })
    man = {
        "note": "每次训练或覆盖检查点后必须重跑本脚本；sha256 与磁盘失配说明文件已被覆盖",
        "retention": ("保留：最终一轮 + 验证最佳轮 + 核心轮次 50/100/150/200/300/400/500…；"
                      "其余中间轮次可删。删除前先看这里，并在 docs/DATA.md §6.5.1"
                      "（B 线：docs/DATA-B.md §6.5）登记；删完立刻重跑本脚本"),
        "invalid_reason": INVALID,
        "items": items,
    }
    out_path.write_text(json.dumps(man, ensure_ascii=False, indent=1))
    print(f"{len(items)} checkpoints -> {out_path}")


if __name__ == "__main__":
    main()
